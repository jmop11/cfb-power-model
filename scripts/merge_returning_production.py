import sqlite3

db_path = "data/cfb_model.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    SELECT team_id, season, returning_production_pct_offense, returning_production_pct_defense
    FROM team_season
    WHERE returning_production_pct_offense IS NOT NULL
       OR returning_production_pct_defense IS NOT NULL
""")
rows = cur.fetchall()

both_sides = 0
one_side_only = 0

for team_id, season, off_pct, def_pct in rows:
    if off_pct is not None and def_pct is not None:
        combined = (off_pct + def_pct) / 2
        both_sides += 1
    else:
        # Only one side of the ball has real data -- don't fabricate a
        # "total" number from half the picture, leave it honestly NULL.
        combined = None
        one_side_only += 1

    cur.execute(
        "UPDATE team_season SET returning_production_pct = ? WHERE team_id = ? AND season = ?",
        (combined, team_id, season)
    )

conn.commit()
conn.close()

print(f"Combined both sides for {both_sides} team-seasons")
print(f"Left NULL (only one side available) for {one_side_only} team-seasons")