import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("CFBD_API_KEY")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

for year in [2015, 2016, 2017, 2018]:
    r = requests.get("https://api.collegefootballdata.com/roster",
        headers=headers, params={"year": year})
    print(f"{year}: {len(r.json())} players")