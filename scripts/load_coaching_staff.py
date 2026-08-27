import re
import sqlite3
import time
import requests

db_path = "data/cfb_model.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

HEADERS = {"User-Agent": "cfb-power-model-research/1.0"}

WIKI_TITLE_OVERRIDES = {
    "Miami (OH)": "Miami",
}


def extract_coaches_from_wikitext(wikitext):
    coaches = {}
    infobox_patterns = {
        "HC": r"\|\s*head_coach\s*=\s*\[\[([^\]|]+)",
        "OC": r"\|\s*off_coach\s*=\s*\[\[([^\]|]+)",
        "DC": r"\|\s*def_coach\s*=\s*\[\[([^\]|]+)",
    }
    for role, pattern in infobox_patterns.items():
        match = re.search(pattern, wikitext)
        if match:
            coaches[role] = match.group(1).strip()
    return coaches


def fetch_wikitext(title, retries=1):
    """Returns (wikitext_or_None, error_reason). Retries once on any
    network/parsing failure before giving up."""
    for attempt in range(retries + 1):
        try:
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "parse", "page": title, "prop": "wikitext", "format": "json"},
                headers=HEADERS,
                timeout=10
            )
            data = response.json()
            if "error" in data:
                return None, "page does not exist"
            return data["parse"]["wikitext"]["*"], None
        except (requests.exceptions.RequestException, ValueError) as e:
            if attempt < retries:
                time.sleep(2)
                continue
            return None, f"network/parse error: {e}"


cur.execute("SELECT team_id, school, mascot FROM teams WHERE is_fbs = 1")
teams = cur.fetchall()

START_YEAR = 2015
END_YEAR = 2026

inserted = 0
failed = []

for team_id, school, mascot in teams:
    wiki_school = WIKI_TITLE_OVERRIDES.get(school, school)

    for year in range(START_YEAR, END_YEAR + 1):
        title = f"{year} {wiki_school} {mascot} football team"

        wikitext, error = fetch_wikitext(title)

        if wikitext is None:
            failed.append((school, year, title, error))
            time.sleep(0.3)
            continue

        coaches = extract_coaches_from_wikitext(wikitext)

        for role, coach_name in coaches.items():
            cur.execute("""
                INSERT OR REPLACE INTO coaching_staff (team_id, season, role, coach_name)
                VALUES (?, ?, ?, ?)
            """, (team_id, year, role, coach_name))
            inserted += 1

        time.sleep(0.3)

    conn.commit()
    print(f"{school}: done through {END_YEAR}")

conn.close()

print(f"\nInserted/updated {inserted} coach records")
print(f"\n{len(failed)} team-years failed to resolve:")
for school, year, title, error in failed[:30]:
    print(f"  {year} {school}: {error}")
if len(failed) > 30:
    print(f"  ... and {len(failed) - 30} more")