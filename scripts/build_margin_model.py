import sqlite3
import math

db_path = "data/cfb_model.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()


def implied_elo_gap(probability):
    probability = min(max(probability, 0.02), 0.98)
    return -400 * math.log10((1 / probability) - 1)


# Every FBS-vs-FBS completed game we've already generated a prediction for.
# Reusing predicted_home_win_prob (rather than re-deriving ratings from
# scratch) means this automatically reflects the corrected, bug-fixed
# Elo history -- no separate re-pull needed.
cur.execute("""
    SELECT p.predicted_home_win_prob, g.home_score, g.away_score
    FROM predictions p
    JOIN games g ON g.game_id = p.game_id
    JOIN teams ht ON ht.team_id = g.home_team_id
    JOIN teams at ON at.team_id = g.away_team_id
    WHERE p.model_version = 'elo_v2_walkforward_hfa'
      AND ht.is_fbs = 1 AND at.is_fbs = 1
      AND g.completed = 1
""")
rows = cur.fetchall()

xs, ys = [], []
for predicted_prob, home_score, away_score in rows:
    xs.append(implied_elo_gap(predicted_prob))
    ys.append(home_score - away_score)

n = len(xs)
x_mean = sum(xs) / n
y_mean = sum(ys) / n

numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
denominator = sum((x - x_mean) ** 2 for x in xs)
slope = numerator / denominator
intercept = y_mean - slope * x_mean

residuals = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
residual_variance = sum(r ** 2 for r in residuals) / (n - 2)  # -2 for the two fitted params
residual_std = residual_variance ** 0.5

print(f"Trained on {n} FBS-vs-FBS games")
print(f"Margin = {slope:.4f} * elo_diff + {intercept:.3f}")
print(f"Residual standard deviation: {residual_std:.2f} points")

cur.execute("""
    DELETE FROM config WHERE key IN
    ('margin_regression_slope', 'margin_regression_intercept', 'margin_residual_stdev')
""")
cur.execute("INSERT INTO config (key, value, description) VALUES (?, ?, ?)",
    ('margin_regression_slope', str(slope), 'Elo-diff-to-margin conversion, OLS on historical FBS games'))
cur.execute("INSERT INTO config (key, value, description) VALUES (?, ?, ?)",
    ('margin_regression_intercept', str(intercept), 'Intercept for margin regression, should sit near 0'))
cur.execute("INSERT INTO config (key, value, description) VALUES (?, ?, ?)",
    ('margin_residual_stdev', str(residual_std), 'Std dev of actual margin vs predicted, drives future cover-probability calc'))
conn.commit()
conn.close()