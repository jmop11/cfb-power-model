-- ============================================================================
-- CFB Power Rating + Upset Model — Database Schema (SQLite)
-- ============================================================================
--
-- SCOPE: FBS only. FCS opponents get a flat baseline rating (see `config`),
-- not full feature treatment.
--
-- CRITICAL DESIGN RULE — "as-of" / no leakage:
-- Every rolling stat (ratings, style tags, defensive splits, turnover luck,
-- roster age, usage) is computed using data THROUGH THE END of the previous
-- week only. A `team_week_state` row for (team, season, week=9) must never
-- include anything from week 9's own games — it represents what was
-- knowable entering week 9, and is what you'd use to predict week 9 games.
-- Same rule applies to betting lines / injury reports: both are pulled at
-- T-minus-60-minutes before each game's kickoff, so they represent the same
-- moment in time as each other.
--
-- TWO MANUAL TABLES in this schema (everything else is API-sourced or
-- derived): `rivalries` and `coaching_staff` (+ its derived `coach_moves`
-- diff table). Everything else — lookahead/letdown/revenge/stakes, SOS,
-- turnover luck, style tags, opponent splits — is computed from your own
-- ratings and CFBD data, no manual curation required.
-- ============================================================================


-- ============================================================================
-- 0. CONFIG — tunable constants, so tuning doesn't require code changes
-- ============================================================================
CREATE TABLE config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    description TEXT
);
-- Seed examples (insert at setup time):
--   ('elo_k_factor', '20', 'How much a single result moves a team''s rating')
--   ('mov_cap', '28', 'Margin of victory cap before it stops adding Elo weight')
--   ('fcs_baseline_rating', '1200', 'Flat Elo assigned to any FCS opponent')
--   ('preseason_blend_weight', '0.5', 'Weight on talent composite vs prior-year Elo in preseason prior')
--   ('betting_snapshot_minutes_before_kickoff', '60', 'T-minus snapshot for lines + injuries')


-- ============================================================================
-- 1. REFERENCE / SLOW-CHANGING TABLES
-- ============================================================================

CREATE TABLE venues (
    venue_id      INTEGER PRIMARY KEY,
    cfbd_id       INTEGER,
    name          TEXT NOT NULL,
    city          TEXT,
    state         TEXT,
    latitude      REAL,
    longitude     REAL,
    elevation_ft  REAL,
    timezone      TEXT,
    capacity      INTEGER
);

CREATE TABLE teams (
    team_id       INTEGER PRIMARY KEY,
    cfbd_id       INTEGER,
    school        TEXT NOT NULL,
    mascot        TEXT,
    home_venue_id INTEGER REFERENCES venues(venue_id),
    is_fbs        BOOLEAN NOT NULL DEFAULT 1
);

-- Year-specific — required because of realignment. Used for bowl-eligibility
-- / championship-stakes context, NOT for SOS (SOS comes from Elo directly).
CREATE TABLE conference_membership (
    team_id     INTEGER NOT NULL REFERENCES teams(team_id),
    season      INTEGER NOT NULL,
    conference  TEXT NOT NULL,
    PRIMARY KEY (team_id, season)
);

-- MANUAL TABLE #1 — user-curated, FBS-only rivalry pairs.
CREATE TABLE rivalries (
    rivalry_id    INTEGER PRIMARY KEY,
    team_id_a     INTEGER NOT NULL REFERENCES teams(team_id),
    team_id_b     INTEGER NOT NULL REFERENCES teams(team_id),
    rivalry_name  TEXT,
    notes         TEXT
);

-- MANUAL/SEMI-AUTOMATED TABLE #2a — scraped annually from Wikipedia
-- team-season infobox pages (CFBD's /coaches endpoint is HC-only).
CREATE TABLE coaching_staff (
    team_id     INTEGER NOT NULL REFERENCES teams(team_id),
    season      INTEGER NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('HC','OC','DC','SC')),
    coach_name  TEXT NOT NULL,
    PRIMARY KEY (team_id, season, role)
);

-- 2b — derived year-over-year diff of `coaching_staff`, auto-flagged,
-- then manually QA'd (verified flag) before being trusted downstream.
CREATE TABLE coach_moves (
    move_id       INTEGER PRIMARY KEY,
    coach_name    TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('HC','OC','DC','SC')),
    side_of_ball  TEXT CHECK (side_of_ball IN ('offense','defense','special_teams')),
    from_team_id  INTEGER REFERENCES teams(team_id),
    from_season   INTEGER,
    to_team_id    INTEGER REFERENCES teams(team_id),
    to_season     INTEGER,
    verified      BOOLEAN NOT NULL DEFAULT 0  -- set true after manual QA pass
);


-- ============================================================================
-- 2. PLAYER-LEVEL TABLES
-- ============================================================================

CREATE TABLE players (
    player_id       INTEGER PRIMARY KEY,
    cfbd_id         INTEGER,
    espn_id         INTEGER,
    name            TEXT NOT NULL,
    birthdate       DATE,              -- pulled from ESPN roster API
    position        TEXT,
    current_team_id INTEGER REFERENCES teams(team_id)
);

-- Usage-based "who's actually playing" — recomputed periodically,
-- season-to-date THROUGH `through_week`, excluding that week's own game.
-- This is what replaces a hardcoded position-count template for the
-- starting-22 / roster-age calculation, and lets composition emerge
-- naturally per team (Army vs. Oregon) instead of being pre-assumed.
CREATE TABLE player_usage (
    player_id      INTEGER NOT NULL REFERENCES players(player_id),
    team_id        INTEGER NOT NULL REFERENCES teams(team_id),
    season         INTEGER NOT NULL,
    through_week   INTEGER NOT NULL,
    position_group TEXT NOT NULL,
    usage_rate     REAL,               -- season-to-date share, excl. current wk
    PRIMARY KEY (player_id, season, through_week)
);


-- ============================================================================
-- 3. GAME-LEVEL TABLES (schedule, results, weather, lines, injuries)
-- ============================================================================

CREATE TABLE games (
    game_id         INTEGER PRIMARY KEY,
    cfbd_id         INTEGER,
    season          INTEGER NOT NULL,
    week            INTEGER NOT NULL,
    season_type     TEXT NOT NULL CHECK (season_type IN ('regular','postseason')),
    start_date_utc  DATETIME NOT NULL,
    home_team_id    INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id    INTEGER NOT NULL REFERENCES teams(team_id),
    neutral_site    BOOLEAN NOT NULL DEFAULT 0,
    venue_id        INTEGER REFERENCES venues(venue_id),
    home_score      INTEGER,
    away_score      INTEGER,
    completed       BOOLEAN NOT NULL DEFAULT 0
);
CREATE INDEX idx_games_season_week ON games(season, week);

CREATE TABLE game_weather (
    game_id       INTEGER PRIMARY KEY REFERENCES games(game_id),
    temp_f        REAL,
    wind_mph      REAL,
    precip_type   TEXT,
    precip_intensity REAL,
    pulled_at     DATETIME
);

-- Pulled at the standardized T-minus-60-minutes snapshot (config: 
-- betting_snapshot_minutes_before_kickoff), same moment as injury_reports.
CREATE TABLE betting_lines (
    line_id            INTEGER PRIMARY KEY,
    game_id            INTEGER NOT NULL REFERENCES games(game_id),
    provider           TEXT,
    spread_home        REAL,
    over_under         REAL,
    moneyline_home     INTEGER,
    moneyline_away     INTEGER,
    implied_prob_home  REAL,          -- derived from moneyline/spread
    pulled_at          DATETIME NOT NULL
);

-- Pulled at the same T-minus-60 snapshot as betting_lines. Reliable mainly
-- for conference games (non-conference reports aren't mandated).
CREATE TABLE injury_reports (
    report_id   INTEGER PRIMARY KEY,
    game_id     INTEGER NOT NULL REFERENCES games(game_id),
    team_id     INTEGER NOT NULL REFERENCES teams(team_id),
    player_id   INTEGER REFERENCES players(player_id),
    position    TEXT,
    status      TEXT CHECK (status IN ('available','probable','questionable','doubtful','out')),
    source      TEXT CHECK (source IN ('conference_report','fallback_scrape')),
    pulled_at   DATETIME NOT NULL
);

-- Per-team-per-game situational context. Two rows per game (one per team),
-- since context is often asymmetric (only one side has the bye, etc).
CREATE TABLE game_context (
    game_id            INTEGER NOT NULL REFERENCES games(game_id),
    team_id            INTEGER NOT NULL REFERENCES teams(team_id),
    is_rivalry         BOOLEAN DEFAULT 0,   -- joined from `rivalries`
    is_revenge_game    BOOLEAN DEFAULT 0,   -- lost to this opp last meeting
    had_bye_last_week  BOOLEAN DEFAULT 0,
    days_rest          INTEGER,
    lookahead_score    REAL,   -- next wk opponent Elo minus this wk opponent Elo
    letdown_score      REAL,   -- this wk opponent Elo minus last wk opponent Elo
    bowl_stakes_score  REAL,   -- proxy for eligibility/playoff stakes
    is_fcs_opponent    BOOLEAN DEFAULT 0,
    PRIMARY KEY (game_id, team_id)
);

-- Travel/environmental shock, from the traveling team's perspective
-- (near-zero for the home team in a standard non-neutral-site game).
CREATE TABLE game_travel (
    game_id                 INTEGER NOT NULL REFERENCES games(game_id),
    team_id                 INTEGER NOT NULL REFERENCES teams(team_id),
    distance_miles          REAL,
    timezones_crossed       INTEGER,
    elevation_differential_ft REAL,   -- venue elevation minus team's home elevation
    climate_shock_f         REAL,     -- game-day temp minus team's seasonal norm
    PRIMARY KEY (game_id, team_id)
);


-- ============================================================================
-- 4. TEAM-SEASON TABLE (mostly preseason-fixed values)
-- ============================================================================

CREATE TABLE team_season (
    team_id                   INTEGER NOT NULL REFERENCES teams(team_id),
    season                    INTEGER NOT NULL,
    talent_composite          REAL,     -- CFBD /talent (247 composite)
    returning_production_pct  REAL,     -- CFBD returning production
    coach_continuity_score    REAL,     -- transfer-following-coach metric, side-of-ball weighted
    elo_start_of_season       REAL,     -- blended prior: talent + prior-yr Elo regressed to mean
    PRIMARY KEY (team_id, season)
);


-- ============================================================================
-- 5. TEAM-WEEK ROLLING STATE — the Elo/SRS engine's memory
-- ============================================================================
-- One row per team per week, representing state ENTERING that week
-- (i.e. computed from weeks 1..week-1 only). This is what the weekly
-- update script appends to after each week's results come in.
-- ============================================================================

CREATE TABLE team_week_state (
    team_id                     INTEGER NOT NULL REFERENCES teams(team_id),
    season                      INTEGER NOT NULL,
    week                        INTEGER NOT NULL,
    elo_rating                  REAL,
    srs_rating                  REAL,
    sos                         REAL,    -- avg opponent Elo (or exp. win-prob sum)
    hfa_residual                REAL,    -- empirical, rolling multi-yr avg
    avg_roster_age              REAL,    -- usage-weighted starting-22, excl. current wk
    style_run_rate              REAL,    -- standard-downs rush %, season-to-date, excl. current wk
    def_run_success_allowed     REAL,    -- standard-downs, season-to-date, excl. current wk
    def_pass_success_allowed    REAL,
    turnover_luck_gap           REAL,    -- actual TO margin minus expected (from havoc rate)
    qb_starter_player_id        INTEGER REFERENCES players(player_id),
    qb_changed_flag             BOOLEAN DEFAULT 0,
    ol_continuity_pct           REAL,    -- % of O-line snaps same as prior week
    PRIMARY KEY (team_id, season, week)
);
CREATE INDEX idx_tws_season_week ON team_week_state(season, week);


-- ============================================================================
-- 6. MODEL OUTPUTS / EVALUATION
-- ============================================================================

CREATE TABLE predictions (
    prediction_id            INTEGER PRIMARY KEY,
    game_id                  INTEGER NOT NULL REFERENCES games(game_id),
    model_version             TEXT NOT NULL,
    predicted_home_win_prob   REAL,
    predicted_margin          REAL,
    upset_probability         REAL,
    market_implied_prob_home  REAL,
    model_market_edge         REAL,      -- model prob minus market implied prob
    generated_at              DATETIME NOT NULL
);

CREATE TABLE backtest_results (
    backtest_id             INTEGER PRIMARY KEY,
    model_version            TEXT NOT NULL,
    evaluated_through_season INTEGER,
    evaluated_through_week   INTEGER,
    brier_score              REAL,
    precision                REAL,
    recall                   REAL,
    sample_size               INTEGER,
    notes                    TEXT,
    run_at                   DATETIME NOT NULL
);

-- The parallel prior-vs-learned comparison for rivalry/lookahead/letdown
-- weighting: same feature, two weight sources, tracked over time.
CREATE TABLE context_weight_comparison (
    id                      INTEGER PRIMARY KEY,
    feature_name            TEXT NOT NULL,   -- e.g. 'rivalry', 'lookahead_score'
    weight_source            TEXT NOT NULL CHECK (weight_source IN ('research_prior','learned')),
    weight_value             REAL,
    season                   INTEGER,         -- null = cumulative/all-time
    brier_score_at_eval      REAL,
    notes                    TEXT
);