from elo_engine import calculate_preseason_prior

print("=== Case 1: Elite talent, no prior season (2015 bootstrap year) ===")
result = calculate_preseason_prior(
    talent_composite=950, talent_mean=650, talent_stdev=150,
    prior_year_elo=None, blend_weight=0.5,
    regression_factor=0.33, zscore_multiplier=200
)
print(f"Result: {result:.1f} (expected: well above 1500, talent-only)")

print("\n=== Case 2: Weak talent this year, but strong prior-year Elo ===")
result = calculate_preseason_prior(
    talent_composite=500, talent_mean=650, talent_stdev=150,
    prior_year_elo=1750, blend_weight=0.5,
    regression_factor=0.33, zscore_multiplier=200
)
print(f"Result: {result:.1f} (expected: pulled down from 1750, but not all the way to talent's number)")

print("\n=== Case 3: No talent data yet (2026), decent prior-year Elo ===")
result = calculate_preseason_prior(
    talent_composite=None, talent_mean=650, talent_stdev=150,
    prior_year_elo=1600, blend_weight=0.5,
    regression_factor=0.33, zscore_multiplier=200
)
print(f"Result: {result:.1f} (expected: regressed prior-year Elo only, no talent influence)")

print("\n=== Case 4: Nothing available at all ===")
result = calculate_preseason_prior(
    talent_composite=None, talent_mean=650, talent_stdev=150,
    prior_year_elo=None, blend_weight=0.5,
    regression_factor=0.33, zscore_multiplier=200
)
print(f"Result: {result:.1f} (expected: exactly 1500, the flat default)")