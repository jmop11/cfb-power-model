import os
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CFBD_API_KEY")
db_path = "data/cfb_model.db"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Lookup of teams we already know (all currently FBS, is_fbs=1)
cur.execute("SELECT team_id, cfbd_id FROM teams")
team_lookup = {row[1]: row[0] for row in cur.fetchall()}
fbs_cfbd_ids = set(team_lookup.keys())

def get_or_create_team(cfbd_id, school_name):
    """Return our internal team_id for a CFBD team id, creating a
    non-FBS placeholder row (is_fbs=0) if we haven't seen it before."""
    if cfbd_id in team_lookup:
        return team_lookup[cfbd_id]
    cur.execute(
        "INSERT INTO teams (cfbd_id, school, is_fbs) VALUES (?, ?, 0)",
        (cfbd_id, school_name)
    )
    new_id = cur.lastrowid
    team_lookup[cfbd_id] = new_id
    return new_id

START_YEAR = 2015
END_YEAR = datetime.now().year  # includes the in-progress 2026 season

games_inserted = 0
games_skipped = 0

for year in range(START_YEAR, END_YEAR + 1):
    for season_type in ["regular", "postseason"]:
        params = {"year": year, "seasonType": season_type}
        response = requests.get(
            "https://api.collegefootballdata.com/games",
            headers=headers, params=params
        )
        games = response.json()

        for g in games:
            home_cfbd_id = g.get("homeId")
            away_cfbd_id = g.get("awayId")

            # Skip games where NEITHER team is FBS (e.g. D2 vs D2)
            if home_cfbd_id not in fbs_cfbd_ids and away_cfbd_id not in fbs_cfbd_ids:
                games_skipped += 1
                continue

            cur.execute("SELECT game_id FROM games WHERE cfbd_id = ?", (g.get("id"),))
            if cur.fetchone():
                continue  # already loaded — safe to re-run this script

            home_team_id = get_or_create_team(home_cfbd_id, g.get("homeTeam"))
            away_team_id = get_or_create_team(away_cfbd_id, g.get("awayTeam"))

            cur.execute("""
                INSERT INTO games (cfbd_id, season, week, season_type, start_date_utc,
                                    home_team_id, away_team_id, neutral_site,
                                    home_score, away_score, completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                g.get("id"),
                g.get("season"),
                g.get("week"),
                g.get("seasonType"),
                g.get("startDate"),
                home_team_id,
                away_team_id,
                1 if g.get("neutralSite") else 0,
                g.get("homePoints"),
                g.get("awayPoints"),
                1 if g.get("completed") else 0
            ))
            games_inserted += 1

    conn.commit()
    print(f"{year}: done")

conn.close()
print(f"Total games inserted: {games_inserted}")
print(f"Total games skipped (no FBS team involved): {games_skipped}")