import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CFBD_API_KEY")

if not api_key:
    raise ValueError("CFBD_API_KEY not found — check your .env file")

url = "https://api.collegefootballdata.com/teams"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}
params = {"conference": "SEC"}

response = requests.get(url, headers=headers, params=params)

print(f"Status code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Success! Got {len(data)} teams back.")
    print(f"First team: {data[0]['school']}")
else:
    print(f"Error: {response.text}")