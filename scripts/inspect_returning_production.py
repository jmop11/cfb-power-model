import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CFBD_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

response = requests.get(
    "https://api.collegefootballdata.com/player/returning",
    headers=headers,
    params={"year": 2025}
)
data = response.json()

print(f"Got {len(data)} teams back for 2025")
if data:
    print(json.dumps(data[0], indent=2))