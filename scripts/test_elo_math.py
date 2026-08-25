from elo_engine import update_ratings

print("=== Case 1: Evenly matched teams, close home win ===")
new_home, new_away = update_ratings(1500, 1500, 24, 21, hfa=55, k_factor=20, mov_cap=28)
print(f"Home: 1500 -> {new_home:.1f} (expected: small increase)")
print(f"Away: 1500 -> {new_away:.1f} (expected: small decrease)")

print("\n=== Case 2: Big underdog pulls the upset ===")
new_home, new_away = update_ratings(1400, 1700, 27, 24, hfa=55, k_factor=20, mov_cap=28)
print(f"Home (underdog): 1400 -> {new_home:.1f} (expected: BIG increase)")
print(f"Away (favorite): 1700 -> {new_away:.1f} (expected: BIG decrease)")

print("\n=== Case 3: Big favorite wins big (already expected) ===")
new_home, new_away = update_ratings(1700, 1400, 45, 10, hfa=55, k_factor=20, mov_cap=28)
print(f"Home (favorite): 1700 -> {new_home:.1f} (expected: only a small increase, despite 35pt margin)")
print(f"Away (underdog): 1400 -> {new_away:.1f} (expected: only a small decrease)")

print("\n=== Case 4: Same big favorite, but LOSES ===")
new_home, new_away = update_ratings(1700, 1400, 17, 24, hfa=55, k_factor=20, mov_cap=28)
print(f"Home (favorite, upset): 1700 -> {new_home:.1f} (expected: LARGE decrease)")
print(f"Away (underdog, upset win): 1400 -> {new_away:.1f} (expected: LARGE increase)")