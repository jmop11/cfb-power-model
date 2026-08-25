import math


def calculate_expected_score(rating_home, rating_away, hfa):
    """
    Standard Elo logistic formula. Returns the home team's expected
    probability of winning, as a number between 0 and 1.

    HFA is added to the home team's rating BEFORE comparing the two —
    a positive HFA effectively makes the home team look stronger than
    its raw rating alone would suggest, which is exactly what "home
    field advantage" means in practical terms.

    The /400 divisor is Elo's standard scaling constant: a 400-point
    rating gap corresponds to a 10x difference in expected win odds.
    We're not deriving that from anything project-specific — it's the
    same constant chess Elo (and most sports Elo variants) use.
    """
    rating_diff = rating_away - (rating_home + hfa)
    expected_home = 1 / (1 + 10 ** (rating_diff / 400))
    return expected_home


def calculate_mov_multiplier(margin, elo_diff_of_winner, mov_cap):
    """
    Margin-of-victory multiplier, adapted from the same approach 538
    uses for NFL Elo. The idea: a blowout win means more when the
    winner was an underdog than when the winner was already a heavy
    favorite (a big favorite winning big was already expected).

    - margin gets capped at mov_cap before the log, so a 60-point
      demolition doesn't move ratings dramatically more than a
      35-point one — the marginal information in "how much bigger
      was this blowout" trails off.
    - The log compresses margin's effect so it grows, but slows down,
      as margin increases (log(2) is a much bigger jump than the gap
      between log(30) and log(31)).
    - The second term is the actual dampening: elo_diff_of_winner is
      how big a favorite the winner already was pre-game. As that
      number grows, the whole multiplier shrinks toward a floor —
      exactly the "this was already expected" discount.
    """
    capped_margin = min(abs(margin), mov_cap)
    multiplier = math.log(capped_margin + 1) * (2.2 / (0.001 * abs(elo_diff_of_winner) + 2.2))
    return multiplier


def update_ratings(rating_home, rating_away, home_score, away_score,
                    hfa, k_factor, mov_cap):
    """
    Runs one game through the full Elo update and returns the new
    (rating_home, rating_away) tuple. Every other piece of the engine
    we build after this — the season loop, the database writes — only
    exists to call this function correctly, for the right teams, in
    the right order. This is the actual heart of the system.
    """
    expected_home = calculate_expected_score(rating_home, rating_away, hfa)
    expected_away = 1 - expected_home

    if home_score > away_score:
        actual_home, actual_away = 1, 0
    elif home_score < away_score:
        actual_home, actual_away = 0, 1
    else:
        actual_home, actual_away = 0.5, 0.5  # essentially never happens in modern CFB, handled anyway

    margin = abs(home_score - away_score)

    # How big a favorite was the actual winner, pre-game? Needed for the MOV dampening.
    if actual_home == 1:
        elo_diff_of_winner = (rating_home + hfa) - rating_away
    elif actual_away == 1:
        elo_diff_of_winner = rating_away - (rating_home + hfa)
    else:
        elo_diff_of_winner = 0

    mov_multiplier = calculate_mov_multiplier(margin, elo_diff_of_winner, mov_cap) if margin > 0 else 1.0

    new_rating_home = rating_home + k_factor * mov_multiplier * (actual_home - expected_home)
    new_rating_away = rating_away + k_factor * mov_multiplier * (actual_away - expected_away)

    return new_rating_home, new_rating_away

def calculate_preseason_prior(talent_composite, talent_mean, talent_stdev,
                                prior_year_elo, blend_weight,
                                regression_factor, zscore_multiplier,
                                default_elo=1500):
    """
    Builds a team's starting Elo for a new season, blending two signals:
    how good the roster looks on paper (talent), and how good the team
    actually proved to be last year (prior Elo, regressed toward the mean).
    Handles missing data gracefully in both directions — a team with no
    talent number yet (like 2026 right now) falls back to prior-year Elo
    alone; a team with no prior season (like 2015, or new to FBS) falls
    back to talent alone; a team with neither gets the flat default.
    """
    if talent_composite is not None and talent_stdev:
        talent_zscore = (talent_composite - talent_mean) / talent_stdev
        talent_component = default_elo + (talent_zscore * zscore_multiplier)
    else:
        talent_component = None

    if prior_year_elo is not None:
        regressed_prior = default_elo + (prior_year_elo - default_elo) * (1 - regression_factor)
    else:
        regressed_prior = None

    if talent_component is not None and regressed_prior is not None:
        return blend_weight * talent_component + (1 - blend_weight) * regressed_prior
    elif talent_component is not None:
        return talent_component
    elif regressed_prior is not None:
        return regressed_prior
    else:
        return default_elo