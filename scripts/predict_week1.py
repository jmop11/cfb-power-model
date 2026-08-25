import sqlite3
from elo_engine import calculate_expected_score

db_path = "data/cfb_model.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

SEASON = 2026
MODEL_VERSION = "week1_2026_live"
START_DATE = "2026-08-29"
END_DATE = "2026-08-30"  # inclusive -- this weekend specifically, not next weekend's slate


def get_config(key, cast=float):
    cur.execute("SELECT value FROM config WHERE key = ?", (key,))
    return cast(cur.fetchone()[0])


LEAGUE_BASELINE_HFA = get_config("flat_hfa_placeholder")
FCS_BASELINE = get_config("fcs_baseline_rating")

cur.execute("""
    SELECT team_id, elo_start_of_season, hfa_residual
    FROM team_season WHERE season = ?
""", (SEASON,))
team_state = {row[0]: (row[1], row[2] or 0) for row in cur.fetchall()}

cur.execute("SELECT team_id, school, is_fbs FROM teams")
team_info = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

cur.execute("""
    SELECT game_id, home_team_id, away_team_id, neutral_site, start_date_utc
    FROM games
    WHERE season = ? AND season_type = 'regular'
      AND DATE(start_date_utc) BETWEEN ? AND ?
    ORDER BY start_date_utc
""", (SEASON, START_DATE, END_DATE))
games = cur.fetchall()

cur.execute("DELETE FROM predictions WHERE model_version = ?", (MODEL_VERSION,))

print(f"=== {START_DATE} to {END_DATE} Predictions ({len(games)} games) ===\n")

for game_id, home_id, away_id, neutral_site, start_date in games:
    home_name, home_is_fbs = team_info[home_id]
    away_name, away_is_fbs = team_info[away_id]

    if home_is_fbs and home_id in team_state:
        rating_home, home_residual = team_state[home_id]
    else:
        rating_home, home_residual = FCS_BASELINE, 0

    if away_is_fbs and away_id in team_state:
        rating_away, _ = team_state[away_id]
    else:
        rating_away = FCS_BASELINE

    hfa = 0 if neutral_site else LEAGUE_BASELINE_HFA + home_residual
    predicted_home_prob = calculate_expected_score(rating_home, rating_away, hfa)

    cur.execute("""
        INSERT INTO predictions (game_id, model_version, predicted_home_win_prob, generated_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (game_id, MODEL_VERSION, predicted_home_prob))

    favorite = home_name if predicted_home_prob >= 0.5 else away_name
    favorite_prob = max(predicted_home_prob, 1 - predicted_home_prob)

    print(f"{away_name:20s} @ {home_name:20s}  ->  {favorite} {favorite_prob:.1%}")

conn.commit()
conn.close()
print(f"\n{len(games)} games predicted and logged.")