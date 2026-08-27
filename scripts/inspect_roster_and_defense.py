import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CFBD_API_KEY")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

response = requests.get(
    "https://api.collegefootballdata.com/stats/player/season",
    headers=headers,
    params={"year": 2025, "team": "Georgia"}
)
data = response.json()

categories = sorted(set(row["category"] for row in data))
print(f"All distinct categories found ({len(categories)} total):")
for category in categories:
    print(f"  {category}")

int_rows = [row for row in data if "INT" in row["statType"].upper() or "int" in row["category"].lower()]
print(f"\nRows matching 'INT' anywhere: {len(int_rows)}")
for row in int_rows[:5]:
    print(f"  category={row['category']}, statType={row['statType']}, player={row['player']}")