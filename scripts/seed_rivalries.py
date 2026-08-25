import sqlite3

db_path = "data/cfb_model.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT team_id, school FROM teams")
team_by_name = {row[1]: row[0] for row in cur.fetchall()}

# (team_a, team_b, rivalry_name, notes)
RIVALRIES = [
    # --- Sourced from EA Sports College Football 26's official trophy list ---
    ("Washington State", "Washington", "Apple Cup", None),
    ("Arkansas", "Missouri", "Battle Line Trophy", None),
    ("Bowling Green", "Toledo", "Battle of I-75", None),
    ("Houston", "Rice", "Bayou Bucket", None),
    ("Syracuse", "West Virginia", "Ben Schwartzwalder Trophy", None),
    ("West Virginia", "Virginia Tech", "Black Diamond Trophy", None),
    ("Utah State", "Wyoming", "Bridger Rifle", None),
    ("Colorado State", "Wyoming", "Bronze Boot", None),
    ("Northern Illinois", "Ball State", "Bronze Stalk Trophy", None),
    ("Colorado", "Colorado State", "Centennial Cup", None),
    ("UConn", "UCF", "Civil ConFLiCT", "Discontinued after realignment"),
    ("Army", "Navy", "Commander-in-Chief's Trophy", "Three-way with Air Force"),
    ("Army", "Air Force", "Commander-in-Chief's Trophy", "Three-way with Navy"),
    ("Navy", "Air Force", "Commander-in-Chief's Trophy", "Three-way with Army"),
    ("Virginia", "Virginia Tech", "Commonwealth Cup", None),
    ("Iowa State", "Iowa", "Cy-Hawk Trophy", None),
    ("Iowa", "Minnesota", "Floyd of Rosedale", None),
    ("Wisconsin", "Nebraska", "Freedom Trophy", None),
    ("Nevada", "UNLV", "Fremont Cannon", None),
    ("Navy", "SMU", "Gansz Trophy", None),
    ("Northwestern", "Michigan", "George Jewett Trophy", None),
    ("Georgia", "Georgia Tech", "Georgia's Governor's Cup", "Clean, Old-Fashioned Hate"),
    ("Arkansas", "LSU", "Golden Boot", None),
    ("Ole Miss", "Mississippi State", "Golden Egg Trophy", "Egg Bowl"),
    ("Texas", "Oklahoma", "Golden Hat", "Red River Rivalry, neutral site Dallas"),
    ("Kentucky", "Louisville", "Governor's Cup", None),
    ("Minnesota", "Penn State", "Governor's Victory Bell", None),
    ("Iowa", "Wisconsin", "Heartland Trophy", None),
    ("Iowa", "Nebraska", "Heroes Trophy", None),
    ("Illinois", "Ohio State", "Illibuck Trophy", None),
    ("Boston College", "Notre Dame", "Ireland Trophy", None),
    ("TCU", "SMU", "Iron Skillet", None),
    ("Hawai'i", "Nevada", "Island Showdown Trophy", None),
    ("Notre Dame", "USC", "Jeweled Shillelagh", None),
    ("Kansas State", "Kansas", "Kansas Governor's Cup", "Sunflower Showdown"),
    ("Air Force", "Hawai'i", "Kuter Trophy", None),
    ("Penn State", "Michigan State", "Land Grant Trophy", None),
    ("Illinois", "Northwestern", "Land of Lincoln Trophy", None),
    ("Stanford", "Notre Dame", "Legends Trophy", None),
    ("Notre Dame", "Michigan State", "Megaphone Trophy", None),
    ("Boise State", "Fresno State", "Milk Can", None),
    ("Boston College", "Clemson", "O'Rourke-McFadden Trophy", None),
    ("San Diego State", "Fresno State", "Oil Can", None),
    ("Michigan State", "Indiana", "Old Brass Spittoon", None),
    ("Indiana", "Purdue", "Old Oaken Bucket", None),
    ("Hawai'i", "Wyoming", "Paniolo Trophy", None),
    ("Michigan", "Michigan State", "Paul Bunyan Trophy", None),
    ("Minnesota", "Wisconsin", "Paul Bunyan's Axe", "Longest-running rivalry in FBS, since 1890"),
    ("Purdue", "Illinois", "Purdue Cannon", None),
    ("Colorado State", "Air Force", "Ram-Falcon Trophy", None),
    ("Ball State", "Miami (OH)", "Red Bird Trophy", None),
    ("TCU", "Texas Tech", "Saddle Trophy", None),
    ("UTEP", "New Mexico State", "Silver Spade", "Battle of I-10"),
    ("Notre Dame", "Purdue", "Shillelagh Trophy", None),
    ("Arkansas", "Texas A&M", "Southwest Classic Trophy", None),
    ("Missouri", "Iowa State", "Telephone Trophy", None),
    ("Arizona", "Arizona State", "Territorial Cup", "Oldest rivalry trophy in FBS, 1899"),
    ("Stanford", "California", "The Axe", "The Big Game"),
    ("Southern Miss", "Tulane", "The Bell (Gulf Coast)", None),
    ("Marshall", "Ohio", "The Bell (Ol' School)", None),
    ("South Alabama", "Troy", "The Belt", None),
    ("Memphis", "UAB", "The Bones Trophy", "Battle for the Bones"),
    ("Cincinnati", "Louisville", "The Keg of Nails", None),
    ("Middle Tennessee", "Troy", "The Palladium Trophy", None),
    ("LSU", "Tulane", "The Rag", None),
    ("San José State", "Fresno State", "Valley Cup", None),
    ("UCLA", "USC", "Victory Bell", "Battle for Los Angeles"),
    ("Missouri", "Nebraska", "Victory Bell (Midwest)", None),
    ("Duke", "North Carolina", "Victory Bell (NC)", None),
    ("Cincinnati", "Miami (OH)", "Victory Bell (Ohio)", "Oldest non-conference rivalry, since 1888"),
    ("Akron", "Kent State", "Wagon Wheel Trophy", None),
    ("UCF", "South Florida", "War on I-4 Trophy", None),
    ("Utah", "BYU", "Beehive Boot", "Three-way with Utah State"),
    ("Utah", "Utah State", "Beehive Boot", "Three-way with BYU"),
    ("BYU", "Utah State", "Beehive Boot", "Three-way with Utah"),
    ("Hawai'i", "San José State", "Dick Tomey Legacy Trophy", None),
    ("Michigan", "Minnesota", "Little Brown Jug", None),
    ("Central Michigan", "Eastern Michigan", "Michigan MAC Trophy", "Three-way with Western Michigan"),
    ("Central Michigan", "Western Michigan", "Michigan MAC Trophy", "Three-way with Eastern Michigan"),
    ("Eastern Michigan", "Western Michigan", "Michigan MAC Trophy", "Three-way with Central Michigan"),

    # --- Major rivalries with no physical trophy ---
    ("Alabama", "Auburn", "Iron Bowl", "No trophy awarded"),
    ("Oklahoma", "Oklahoma State", "Bedlam Series", "No trophy awarded"),
    ("BYU", "Utah", "Holy War", "No trophy awarded"),
    ("Tennessee", "Alabama", "Third Saturday in October", "No trophy awarded"),
    ("LSU", "Alabama", None, "No trophy awarded"),
    ("Auburn", "Georgia", "Deep South's Oldest Rivalry", "No trophy awarded"),
    ("Florida", "Florida State", "Sunshine Showdown", "No trophy awarded"),
    ("Florida", "Georgia", "World's Largest Outdoor Cocktail Party", "Neutral site, Jacksonville"),
    ("Miami", "Florida State", None, "No trophy awarded"),
    ("Miami", "Florida", None, "No trophy awarded"),
    ("Penn State", "Ohio State", None, "No trophy, high-stakes modern Big Ten rivalry"),
    ("Penn State", "Michigan", None, "No trophy awarded"),
    ("Oregon", "Washington", None, "No trophy awarded"),
    ("Oregon", "USC", None, "No trophy, formed post-realignment"),
    ("Michigan", "Ohio State", None, "The Game -- no trophy, one of the sport's defining rivalries"),

    # --- Confirmed via Big Ten conference-specific verification ---
    ("Minnesota", "Nebraska", "$5 Bits of Broken Chair Trophy", None),
    ("Colorado", "Nebraska", "Bison Head Trophy", "Trophy itself has been lost"),
]

inserted = 0
unmatched = set()

for team_a, team_b, name, notes in RIVALRIES:
    id_a = team_by_name.get(team_a)
    id_b = team_by_name.get(team_b)

    if id_a is None:
        unmatched.add(team_a)
    if id_b is None:
        unmatched.add(team_b)
    if id_a is None or id_b is None:
        continue

    cur.execute("""
        SELECT 1 FROM rivalries
        WHERE (team_id_a = ? AND team_id_b = ?) OR (team_id_a = ? AND team_id_b = ?)
    """, (id_a, id_b, id_b, id_a))
    if cur.fetchone():
        continue

    cur.execute("""
        INSERT INTO rivalries (team_id_a, team_id_b, rivalry_name, notes)
        VALUES (?, ?, ?, ?)
    """, (id_a, id_b, name, notes))
    inserted += 1

conn.commit()
conn.close()

print(f"Inserted {inserted} rivalries")
if unmatched:
    print(f"\n{len(unmatched)} team names didn't match — check spelling against your teams table:")
    for name in sorted(unmatched):
        print(f"  - {name}")