import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CFBD_API_KEY")
db_path = "data/cfb_model.db"

url = "https://api.collegefootballdata.com/teams"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

response = requests.get(url, headers=headers)
all_teams = response.json()

fbs_teams = [t for t in all_teams if t.get("classification") == "fbs"]
print(f"Found {len(fbs_teams)} FBS teams out of {len(all_teams)} total teams")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

venues_added = 0
teams_added = 0
teams_skipped = 0

for team in fbs_teams:
    location = team.get("location")
    home_venue_id = None

    if location:
        cfbd_venue_id = location.get("id")

        cur.execute("SELECT venue_id FROM venues WHERE cfbd_id = ?", (cfbd_venue_id,))
        existing_venue = cur.fetchone()

        if existing_venue:
            home_venue_id = existing_venue[0]
        else:
            cur.execute("""
                INSERT INTO venues (cfbd_id, name, city, state, latitude, longitude,
                                     elevation_ft, timezone, capacity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cfbd_venue_id,
                location.get("name"),
                location.get("city"),
                location.get("state"),
                location.get("latitude"),
                location.get("longitude"),
                float(location["elevation"]) if location.get("elevation") is not None else None,
                location.get("timezone"),
                location.get("capacity")
            ))
            home_venue_id = cur.lastrowid
            venues_added += 1

    cfbd_team_id = team.get("id")

    cur.execute("SELECT team_id FROM teams WHERE cfbd_id = ?", (cfbd_team_id,))
    if cur.fetchone():
        teams_skipped += 1
        continue

    cur.execute("""
        INSERT INTO teams (cfbd_id, school, mascot, home_venue_id, is_fbs)
        VALUES (?, ?, ?, ?, ?)
    """, (
        cfbd_team_id,
        team.get("school"),
        team.get("mascot"),
        home_venue_id,
        1
    ))
    teams_added += 1

conn.commit()
conn.close()

print(f"Added {venues_added} new venues")
print(f"Added {teams_added} new teams, skipped {teams_skipped} already in database")