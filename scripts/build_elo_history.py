import sqlite3
from elo_engine import update_ratings, calculate_preseason_prior, calculate_expected_score

db_path = "data/cfb_model.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

MODEL_VERSION = "elo_v1_flat_hfa"  # labels this run so a later HFA-corrected rerun is never confused with it

# Safe to rerun: wipe this model version's predictions before rebuilding,
# rather than letting duplicate rows pile up on every rerun.
cur.execute("DELETE FROM predictions WHERE model_version = ?", (MODEL_VERSION,))
conn.commit()


def get_config(key, cast=float):
    cur.execute("SELECT value FROM config WHERE key = ?", (key,))
    return cast(cur.fetchone()[0])


K_FACTOR = get_config("elo_k_factor")
MOV_CAP = get_config("mov_cap")
BLEND_WEIGHT = get_config("preseason_blend_weight")
ZSCORE_MULTIPLIER = get_config("talent_zscore_to_elo_multiplier")
REGRESSION_FACTOR = get_config("yearly_regression_factor")
FCS_BASELINE = get_config("fcs_baseline_rating")
FLAT_HFA = get_config("flat_hfa_placeholder")
DEFAULT_ELO = 1500.0

cur.execute("SELECT DISTINCT season FROM games ORDER BY season")
seasons = [row[0] for row in cur.fetchall()]

current_rating = {}

for season in seasons:
    print(f"=== Processing {season} ===")

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

        cur.execute("SELECT 1 FROM team_season WHERE team_id = ? AND season = ?", (team_id, season))
        if cur.fetchone():
            cur.execute(
                "UPDATE team_season SET elo_start_of_season = ? WHERE team_id = ? AND season = ?",
                (prior, team_id, season)
            )
        else:
            cur.execute(
                "INSERT INTO team_season (team_id, season, elo_start_of_season) VALUES (?, ?, ?)",
                (team_id, season, prior)
            )

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

        hfa = 0 if neutral_site else FLAT_HFA

        # NEW: capture the PRE-game predicted probability before ratings change.
        # This is the piece the original run never saved -- without it, there's
        # nothing to compare real outcomes against later for HFA calibration
        # (or eventual Brier scoring).
        predicted_home_prob = calculate_expected_score(rating_home, rating_away, hfa)

        cur.execute("""
            INSERT INTO predictions (game_id, model_version, predicted_home_win_prob, generated_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (game_id, MODEL_VERSION, predicted_home_prob))

        new_home, new_away = update_ratings(
            rating_home, rating_away, home_score, away_score,
            hfa=hfa, k_factor=K_FACTOR, mov_cap=MOV_CAP
        )

        if home_is_fbs:
            current_rating[home_id] = new_home
            cur.execute("""
                INSERT OR REPLACE INTO team_week_state
                (team_id, season, season_type, week, elo_rating)
                VALUES (?, ?, ?, ?, ?)
            """, (home_id, season, season_type, week, new_home))

        if away_is_fbs:
            current_rating[away_id] = new_away
            cur.execute("""
                INSERT OR REPLACE INTO team_week_state
                (team_id, season, season_type, week, elo_rating)
                VALUES (?, ?, ?, ?, ?)
            """, (away_id, season, season_type, week, new_away))

    conn.commit()
    print(f"{season}: {len(season_games)} games processed")

conn.close()
print("\nDone.")