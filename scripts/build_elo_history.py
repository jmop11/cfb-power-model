import sqlite3
from elo_engine import update_ratings, calculate_preseason_prior, calculate_expected_score

db_path = "data/cfb_model.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

MODEL_VERSION = "elo_v2_walkforward_hfa"

cur.execute("DELETE FROM predictions WHERE model_version = ?", (MODEL_VERSION,))
conn.commit()

# Teams whose pre-promotion "history" is actually FCS conference play
# mislabeled as FBS competition, because is_fbs is a static current-day
# flag rather than year-specific. Defined ONCE here, not inside the loop.
NEWLY_PROMOTED_FBS = {
    2017: ["Coastal Carolina"],
    2018: ["Liberty"],
    2022: ["James Madison"],
    2023: ["Jacksonville State", "Sam Houston"],
    2024: ["Kennesaw State"],
    2026: ["North Dakota State", "Sacramento State", "Delaware", "Missouri State"],
}


def get_config(key, cast=float):
    cur.execute("SELECT value FROM config WHERE key = ?", (key,))
    return cast(cur.fetchone()[0])


K_FACTOR = get_config("elo_k_factor")
MOV_CAP = get_config("mov_cap")
BLEND_WEIGHT = get_config("preseason_blend_weight")
ZSCORE_MULTIPLIER = get_config("talent_zscore_to_elo_multiplier")
REGRESSION_FACTOR = get_config("yearly_regression_factor")
FCS_BASELINE = get_config("fcs_baseline_rating")
LEAGUE_BASELINE_HFA = get_config("flat_hfa_placeholder")
MIN_HOME_GAMES = int(get_config("min_home_games_for_hfa"))
RESIDUAL_CAP = get_config("hfa_residual_cap")
DEFAULT_ELO = 1500.0

cur.execute("SELECT DISTINCT season FROM games ORDER BY season")
seasons = [row[0] for row in cur.fetchall()]

cur.execute("SELECT team_id, school FROM teams")
school_by_id = {row[0]: row[1] for row in cur.fetchall()}

current_rating = {}
home_game_history = {}
current_hfa_residual = {}


def implied_elo_gap(probability):
    import math
    probability = min(max(probability, 0.02), 0.98)
    return -400 * math.log10((1 / probability) - 1)


for season in seasons:
    print(f"=== Processing {season} ===")

    # --- Discard pre-promotion FCS "history" for newly-FBS teams ---
    for team_name in NEWLY_PROMOTED_FBS.get(season, []):
        cur.execute("SELECT team_id FROM teams WHERE school = ?", (team_name,))
        row = cur.fetchone()
        if row:
            team_id = row[0]
            current_rating[team_id] = None
            home_game_history.pop(team_id, None)
            current_hfa_residual.pop(team_id, None)
            print(f"  Reset {team_name}: pre-promotion FCS history discarded")

    # --- Recompute each team's HFA residual from history BEFORE this season ---
    for team_id, games in home_game_history.items():
        if len(games) < MIN_HOME_GAMES:
            continue
        avg_predicted = sum(p for p, _ in games) / len(games)
        actual_rate = sum(w for _, w in games) / len(games)
        residual = implied_elo_gap(actual_rate) - implied_elo_gap(avg_predicted)
        residual = max(min(residual, RESIDUAL_CAP), -RESIDUAL_CAP)
        current_hfa_residual[team_id] = residual

    # --- Talent z-scores for this season's preseason prior ---
    cur.execute("""
        SELECT team_id, talent_composite FROM team_season
        WHERE season = ? AND talent_composite IS NOT NULL
    """, (season,))
    talent_rows = cur.fetchall()
    talent_by_team = {row[0]: row[1] for row in talent_rows}

    if talent_rows:
        values = [row[1] for row in talent_rows]
        talent_mean = sum(values) / len(values)
        talent_stdev = (sum((v - talent_mean) ** 2 for v in values) / len(values)) ** 0.5
    else:
        talent_mean, talent_stdev = None, None

    cur.execute("SELECT team_id FROM teams WHERE is_fbs = 1")
    fbs_team_ids = [row[0] for row in cur.fetchall()]

    for team_id in fbs_team_ids:
        prior = calculate_preseason_prior(
            talent_composite=talent_by_team.get(team_id),
            talent_mean=talent_mean,
            talent_stdev=talent_stdev,
            prior_year_elo=current_rating.get(team_id),
            blend_weight=BLEND_WEIGHT,
            regression_factor=REGRESSION_FACTOR,
            zscore_multiplier=ZSCORE_MULTIPLIER,
            default_elo=DEFAULT_ELO
        )
        current_rating[team_id] = prior

        residual = current_hfa_residual.get(team_id, 0)

        cur.execute("SELECT 1 FROM team_season WHERE team_id = ? AND season = ?", (team_id, season))
        if cur.fetchone():
            cur.execute(
                "UPDATE team_season SET elo_start_of_season = ?, hfa_residual = ? WHERE team_id = ? AND season = ?",
                (prior, residual, team_id, season)
            )
        else:
            cur.execute(
                "INSERT INTO team_season (team_id, season, elo_start_of_season, hfa_residual) VALUES (?, ?, ?, ?)",
                (team_id, season, prior, residual)
            )

    # --- Process this season's games, in TRUE chronological order ---
    cur.execute("""
        SELECT game_id, season_type, week, home_team_id, away_team_id,
               home_score, away_score, neutral_site
        FROM games
        WHERE season = ? AND completed = 1
        ORDER BY start_date_utc
    """, (season,))
    season_games = cur.fetchall()

    for (game_id, season_type, week, home_id, away_id,
         home_score, away_score, neutral_site) in season_games:

        cur.execute("SELECT is_fbs FROM teams WHERE team_id = ?", (home_id,))
        home_is_fbs = cur.fetchone()[0]
        cur.execute("SELECT is_fbs FROM teams WHERE team_id = ?", (away_id,))
        away_is_fbs = cur.fetchone()[0]

        rating_home = current_rating.get(home_id) if home_is_fbs else FCS_BASELINE
        rating_away = current_rating.get(away_id) if away_is_fbs else FCS_BASELINE

        if neutral_site or season == 2020:
            hfa = 0
        else:
            hfa = LEAGUE_BASELINE_HFA + current_hfa_residual.get(home_id, 0)

        predicted_home_prob = calculate_expected_score(rating_home, rating_away, hfa)

        cur.execute("""
            INSERT INTO predictions (game_id, model_version, predicted_home_win_prob, generated_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (game_id, MODEL_VERSION, predicted_home_prob))

        if (not neutral_site and season != 2020 and home_is_fbs and away_is_fbs):
            actual_win = 1 if home_score > away_score else 0
            home_game_history.setdefault(home_id, []).append((predicted_home_prob, actual_win))

        new_home, new_away = update_ratings(
            rating_home, rating_away, home_score, away_score,
            hfa=hfa, k_factor=K_FACTOR, mov_cap=MOV_CAP
        )

        if home_is_fbs:
            current_rating[home_id] = new_home
            cur.execute("""
                INSERT OR REPLACE INTO team_week_state
                (team_id, season, season_type, week, elo_rating, hfa_residual)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (home_id, season, season_type, week, new_home, current_hfa_residual.get(home_id, 0)))

        if away_is_fbs:
            current_rating[away_id] = new_away
            cur.execute("""
                INSERT OR REPLACE INTO team_week_state
                (team_id, season, season_type, week, elo_rating)
                VALUES (?, ?, ?, ?, ?)
            """, (away_id, season, season_type, week, new_away))

    conn.commit()
    print(f"{season}: {len(season_games)} games processed "
          f"({len(current_hfa_residual)} teams now have empirical HFA residuals)")

conn.close()
print("\nDone.")