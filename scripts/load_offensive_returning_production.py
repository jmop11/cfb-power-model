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

cur.execute("SELECT team_id, school FROM teams")
team_by_name = {row[1]: row[0] for row in cur.fetchall()}

START_YEAR = 2015
END_YEAR = datetime.now().year

inserted = 0
updated = 0
unmatched_names = set()

for year in range(START_YEAR, END_YEAR + 1):
    response = requests.get(
        "https://api.collegefootballdata.com/player/returning",
        headers=headers,
        params={"year": year}
    )
    data = response.json()

    if not data:
        print(f"{year}: no returning production data published yet, skipping")
        continue

    for entry in data:
        school = entry.get("team")
        returning_pct = entry.get("percentPPA")

        team_id = team_by_name.get(school)
        if team_id is None:
            unmatched_names.add(school)
            continue

        cur.execute(
            "SELECT 1 FROM team_season WHERE team_id = ? AND season = ?",
            (team_id, year)
        )
        if cur.fetchone():
            cur.execute(
                "UPDATE team_season SET returning_production_pct_offense = ? WHERE team_id = ? AND season = ?",
                (returning_pct, team_id, year)
            )
            updated += 1
        else:
            cur.execute(
                "INSERT INTO team_season (team_id, season, returning_production_pct_offense) VALUES (?, ?, ?)",
                (team_id, year, returning_pct)
            )
            inserted += 1

    conn.commit()
    print(f"{year}: done ({len(data)} teams)")

conn.close()

print(f"\nInserted {inserted} new rows, updated {updated} existing rows")
if unmatched_names:
    print(f"\n{len(unmatched_names)} names didn't match anything in teams:")
    for name in sorted(unmatched_names):
        print(f"  - {name}")