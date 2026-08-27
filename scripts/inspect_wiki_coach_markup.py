import requests

response = requests.get(
    "https://en.wikipedia.org/w/api.php",
    params={
        "action": "parse",
        "page": "2025 Georgia Bulldogs football team",
        "prop": "wikitext",
        "format": "json"
    },
    headers={"User-Agent": "cfb-power-model-research/1.0"}
)
data = response.json()
wikitext = data["parse"]["wikitext"]["*"]

# Print the full infobox, start to finish
start = wikitext.find("{{Infobox")
end = wikitext.find("\n}}", start) + 3
print(wikitext[start:end])

print("\n\n=== Any special-teams-related field, anywhere in the page ===")
for line in wikitext.split("\n"):
    if "special" in line.lower() or "st_coach" in line.lower():
        print(line)