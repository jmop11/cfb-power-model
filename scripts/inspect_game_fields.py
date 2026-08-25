import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CFBD_API_KEY")

url = "https://api.collegefootballdata.com/games"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}
params = {"year": 2024, "seasonType": "regular"}

response = requests.get(url, headers=headers, params=params)
data = response.json()

print(f"Got {len(data)} games back")
print(json.dumps(data[0], indent=2))