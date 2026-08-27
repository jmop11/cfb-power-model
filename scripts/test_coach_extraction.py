import re
import requests


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

    for i in [1, 2]:
        for prefix, role in [("codef_coach", "DC"), ("cooff_coach", "OC")]:
            pattern = rf"\|\s*{prefix}{i}\s*=\s*\[\[([^\]|]+)"
            match = re.search(pattern, wikitext)
            if match:
                coaches[f"Co-{role}-{i}"] = match.group(1).strip()

    # SC has no clean infobox field -- search line by line, try a few
    # known formats, take the first real match.
    for line in wikitext.split("\n"):
        if "special teams coordinator" in line.lower():
            name_match = (
                re.search(r"\[\[([^\]|]+)\]\]\s*\|\|", line)
                or re.match(r"\*\s*([A-Za-z.\s]+?)\s*[–-]", line)
                or re.match(r"\|\s*([A-Za-z.\s]+?)\s*\|\|", line)
            )
            if name_match:
                coaches["SC"] = name_match.group(1).strip()
                break

    return coaches


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
wikitext = response.json()["parse"]["wikitext"]["*"]

result = extract_coaches_from_wikitext(wikitext)
print("Extracted coaches:")
for role, name in result.items():
    print(f"  {role}: {name}")