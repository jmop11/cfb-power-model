import requests

TEST_TEAMS = [
    ("Ohio State", "Buckeyes"),
    ("BYU", "Cougars"),
    ("Miami (OH)", "RedHawks"),
    ("Army", "Black Knights"),
    ("UCF", "Knights"),
]

for school, mascot in TEST_TEAMS:
    title = f"2025 {school} {mascot} football team"
    response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "parse", "page": title, "prop": "wikitext", "format": "json"},
        headers={"User-Agent": "cfb-power-model-research/1.0"}
    )
    data = response.json()
    if "error" in data:
        print(f"FAILED: '{title}' -> {data['error']['info']}")
    else:
        print(f"OK: '{title}'")