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

WEIGHTS = {
    "INT": 4,
    "TD": 5,      # applies whether it came from the defensive or interceptions category
    "SACKS": 3,
    "TFL": 2,
    "PD": 2,
    "QB HUR": 1,
    "TOT": 1,
}

cur.execute("SELECT team_id, school FROM teams WHERE is_fbs = 1")
team_by_name = {row[1]: row[0] for row in cur.fetchall()}


def get_defensive_value_by_player(year):
    """Pulls defensive + interceptions stats for the whole league in two
    calls, returns {player_id: {"value": float, "team": str}}."""
    player_value = {}

    for category in ["defensive", "interceptions"]:
        response = requests.get(
            "https://api.collegefootballdata.com/stats/player/season",
            headers=headers,
            params={"year": year, "category": category}
        )
        rows = response.json()

        teams_seen = set(row["team"] for row in rows)
        print(f"  {category}: {len(rows)} rows across {len(teams_seen)} teams")

        for row in rows:
            stat_type = row["statType"]
            if stat_type not in WEIGHTS:
                continue
            player_id = row["playerId"]
            weighted = WEIGHTS[stat_type] * float(row["stat"])

            if player_id not in player_value:
                player_value[player_id] = {"value": 0.0, "team": row["team"]}
            player_value[player_id]["value"] += weighted

    return player_value


START_YEAR = 2016  # defensive stats category has no data for 2015, confirmed via inspection
END_YEAR = datetime.now().year - 1  # can't compute "returning" for a season with no next-year roster to compare against

for prior_year in range(START_YEAR, END_YEAR + 1):
    current_year = prior_year + 1
    print(f"\n=== Computing defensive returning production: {prior_year} -> {current_year} ===")

    last_year_value = get_defensive_value_by_player(prior_year)

    if not last_year_value:
        print(f"  No data for {prior_year}, skipping")
        continue

    team_totals = {}
    team_returning = {}
    for player_id, info in last_year_value.items():
        team = info["team"]
        team_totals[team] = team_totals.get(team, 0.0) + info["value"]

    roster_response = requests.get(
        "https://api.collegefootballdata.com/roster",
        headers=headers,
        params={"year": current_year}
    )
    roster_data = roster_response.json()
    current_player_ids = set(str(p["id"]) for p in roster_data)

    for player_id, info in last_year_value.items():
        if player_id in current_player_ids:
            team = info["team"]
            team_returning[team] = team_returning.get(team, 0.0) + info["value"]

    updated = 0
    for team_name, total_value in team_totals.items():
        team_id = team_by_name.get(team_name)
        if team_id is None or total_value == 0:
            continue
        pct_returning = team_returning.get(team_name, 0.0) / total_value

        cur.execute("SELECT 1 FROM team_season WHERE team_id = ? AND season = ?", (team_id, current_year))
        if cur.fetchone():
            cur.execute(
                "UPDATE team_season SET returning_production_pct_defense = ? WHERE team_id = ? AND season = ?",
                (pct_returning, team_id, current_year)
            )
        else:
            cur.execute(
                "INSERT INTO team_season (team_id, season, returning_production_pct_defense) VALUES (?, ?, ?)",
                (team_id, current_year, pct_returning)
            )
        updated += 1

    conn.commit()
    print(f"  Updated {updated} teams for {current_year}")

conn.close()
print("\nDone.")