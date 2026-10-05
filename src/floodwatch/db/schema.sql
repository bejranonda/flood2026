-- BKK FloodWatch schema (plain PostgreSQL 16; TimescaleDB/PostGIS deferred, see DECISIONS D-013).
-- All times are timestamptz stored in UTC. Levels are m MSL (Ko Lak).

CREATE TABLE IF NOT EXISTS station (
    code          text PRIMARY KEY,           -- HII tele_station_oldcode, e.g. BKK008, C.2
    hii_id        bigint,                     -- numeric id used by waterlevel_graph
    name_th       text,
    name_en       text,
    lat           double precision,
    lon           double precision,
    bank_msl      double precision,           -- HII min_bank (D-009)
    ground_msl    double precision,
    critical_msl  double precision,
    agency        text,
    province      text,
    amphoe        text,
    river         text,
    basin         text,
    in_focus      boolean NOT NULL DEFAULT false,
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- Effective-dated history of metadata changes (never overwrite silently).
CREATE TABLE IF NOT EXISTS station_version (
    code        text NOT NULL,
    valid_from  timestamptz NOT NULL DEFAULT now(),
    bank_msl    double precision,
    ground_msl  double precision,
    lat         double precision,
    lon         double precision,
    source      text NOT NULL,
    PRIMARY KEY (code, valid_from)
);

CREATE TABLE IF NOT EXISTS observation (
    code            text NOT NULL,
    obs_time        timestamptz NOT NULL,
    level_msl       double precision,
    discharge       double precision,
    situation_level smallint,
    source          text NOT NULL,            -- hii_load | hii_graph | hii_chart
    quality_flag    text NOT NULL DEFAULT 'ok',
    raw_ref         text,                     -- sha256 of the archived payload
    PRIMARY KEY (code, obs_time)
);
CREATE INDEX IF NOT EXISTS observation_time_idx ON observation (obs_time DESC);

CREATE TABLE IF NOT EXISTS rain_obs (
    code      text NOT NULL,
    obs_time  timestamptz NOT NULL,
    rain_1h   double precision,
    rain_24h  double precision,
    lat       double precision,
    lon       double precision,
    name_th   text,
    province  text,
    PRIMARY KEY (code, obs_time)
);

CREATE TABLE IF NOT EXISTS weather_forecast (
    point       text NOT NULL,
    issue_time  timestamptz NOT NULL,         -- fetch time rounded to the hour (Open-Meteo run time not exposed)
    valid_time  timestamptz NOT NULL,
    model       text NOT NULL,
    precip_mm   double precision,
    PRIMARY KEY (point, issue_time, valid_time, model)
);

CREATE TABLE IF NOT EXISTS crowd_report (           -- privacy: no text, no photos (KI-107)
    ticket_id    text PRIMARY KEY,
    report_time  timestamptz NOT NULL,
    lat          double precision,
    lon          double precision,
    state        text,
    is_flood     boolean NOT NULL
);
CREATE INDEX IF NOT EXISTS crowd_report_time_idx ON crowd_report (report_time DESC);

CREATE TABLE IF NOT EXISTS forecast_run (
    id          bigserial PRIMARY KEY,
    code        text NOT NULL,
    issue_time  timestamptz NOT NULL,
    version     text NOT NULL,
    payload     jsonb NOT NULL,                -- horizons, quantiles, method per horizon, skill, recovery
    UNIQUE (code, issue_time)
);

-- The backtest (evaluate) per gauge, reused by the 30-min forecast for about a day (D-064).
CREATE TABLE IF NOT EXISTS forecast_model (
    code        text PRIMARY KEY,
    trained_at  timestamptz NOT NULL,
    n_rows      integer NOT NULL,              -- readings in the training window when trained (retrain on +20 %)
    payload     jsonb NOT NULL                 -- evaluate() result: method, skill, quantiles per horizon
);

CREATE TABLE IF NOT EXISTS source_health (
    source               text PRIMARY KEY,
    last_success         timestamptz,
    last_error           timestamptz,
    last_error_msg       text,
    consecutive_failures integer NOT NULL DEFAULT 0,
    last_data_time       timestamptz
);

-- Forecasts issued by others, archived as issued so their skill can be measured (HII FEWS files are overwritten
-- daily, D-050). Never mixed with our forecast_run; value in the source's unit (m MSL or m3/s).
CREATE TABLE IF NOT EXISTS external_forecast (
    source      text NOT NULL,
    code        text NOT NULL,                 -- our station code (C.13, CPY014)
    issue_time  timestamptz NOT NULL,          -- the file's Last-Modified
    valid_time  timestamptz NOT NULL,
    value       double precision NOT NULL,
    unit        text NOT NULL,
    PRIMARY KEY (source, code, issue_time, valid_time)
);

-- Rain as it was forecast ~1 and ~2 days before each hour (Open-Meteo previous runs), per rain point: the honest
-- training data for the rain-aware level model (D-052). Live forecasts stay in weather_forecast.
CREATE TABLE IF NOT EXISTS rain_hindcast (
    point       text NOT NULL,
    valid_time  timestamptz NOT NULL,
    day1        double precision NOT NULL,     -- mm/h, forecast issued ~1 day before valid_time
    day2        double precision NOT NULL,     -- mm/h, forecast issued ~2 days before valid_time
    PRIMARY KEY (point, valid_time)
);

-- Flooded H3 cells seen by satellite radar in the last 7 days (GISTDA, D-071; Q45). Replaced as a whole once a day;
-- only the centre, area and place are kept (no polygons, no raw payload: ~300 MB and it echoes our key, KI-262).
CREATE TABLE IF NOT EXISTS sat_flood (
    h3          text PRIMARY KEY,
    lat         double precision NOT NULL,
    lon         double precision NOT NULL,
    area_m2     double precision,
    province    text,
    amphoe      text,
    tambon      text,
    img_from    date,
    img_to      date,
    fetched_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sat_flood_latlon_idx ON sat_flood (lat, lon);

-- DWR early-warning level posts (กรมทรัพยากรน้ำ, Thai egress only): kept apart from `station` because the level is
-- depth on a local staff post (not m MSL) and alarm levels are mostly a 4.00 m default (2026-10-03). Trend-only layer.
CREATE TABLE IF NOT EXISTS dwr_station (
    code        text PRIMARY KEY,
    name_th     text,
    lat         double precision,
    lon         double precision,
    province    text,
    amphoe      text,
    tambon      text,
    main_basin  text,
    sub_basin   text,
    dept        text,
    alert_max   double precision,
    status      text,
    first_seen  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
-- Large dams, daily (HII analyst/dam; RID and EGAT records), for the impact page (D-099)
-- The dams behind HII's daily records (D-100): one row per record id (RID and EGAT keep their own ids)
CREATE TABLE IF NOT EXISTS dam (
    dam_id        integer PRIMARY KEY,
    agency        text,
    name_th       text,
    lat           double precision,
    lon           double precision,
    normal_mcm    double precision,
    max_mcm       double precision,
    sub_basin_id  integer,
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dam_daily (
    dam_id        integer NOT NULL,
    agency        text,
    name_th       text,
    dam_date      date NOT NULL,
    storage_mcm   double precision,
    storage_pct   double precision,
    inflow_mcm    double precision,
    released_mcm  double precision,
    spilled_mcm   double precision,
    level_m       double precision,
    fetched_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (dam_id, dam_date)
);

CREATE TABLE IF NOT EXISTS dwr_obs (
    code      text NOT NULL,
    obs_time  timestamptz NOT NULL,
    level     double precision NOT NULL,
    PRIMARY KEY (code, obs_time)
);

-- Google Flood Hub (D-087): virtual gauges with Google's thresholds, every flood status issued, daily forecasts.
CREATE TABLE IF NOT EXISTS gfh_gauge (
    gauge_id         text PRIMARY KEY,
    lat              double precision,
    lon              double precision,
    source           text,
    quality_verified boolean,
    has_model        boolean,
    warning          double precision,
    danger           double precision,
    extreme          double precision,
    unit             text,
    updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS gfh_status (
    gauge_id     text NOT NULL,
    issued_time  timestamptz NOT NULL,
    severity     text,
    trend        text,
    range_start  timestamptz,
    range_end    timestamptz,
    inundation   text,
    PRIMARY KEY (gauge_id, issued_time)
);
CREATE TABLE IF NOT EXISTS gfh_forecast (
    gauge_id     text NOT NULL,
    issued_time  timestamptz NOT NULL,
    start_time   timestamptz NOT NULL,
    end_time     timestamptz,
    value        double precision NOT NULL,
    PRIMARY KEY (gauge_id, issued_time, start_time)
);

-- Small key/value store for collector bookkeeping (e.g. which stations were backfilled).
CREATE TABLE IF NOT EXISTS collector_state (
    key         text PRIMARY KEY,
    value       jsonb NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Citizen feedback on what we show (privacy: no names/contacts; IP never stored, only a daily-salted hash
-- for rate limiting; notes are never published). Feeds verification and data-quality review (APPROACH §3.5).
CREATE TABLE IF NOT EXISTS user_feedback (
    id           bigserial PRIMARY KEY,
    created_at   timestamptz NOT NULL DEFAULT now(),
    code         text,                          -- station the feedback is about (NULL = location-only report)
    verdict      text,                          -- matches | higher | lower | unsure (reality vs what we show)
    depth        text,                          -- none | ankle | knee | waist | above (water where the user is)
    note         text,                          -- <= 280 chars, never published
    lat          double precision,              -- rounded to 3 decimals (~100 m), only if the user opted in
    lon          double precision,
    snapshot     jsonb NOT NULL,                -- what the site showed at that moment (taken server-side)
    client_hash  text NOT NULL
);
CREATE INDEX IF NOT EXISTS user_feedback_time_idx ON user_feedback (created_at DESC);
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS loc_source text;   -- gps | pin (a pin can be anywhere)
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS rule_label jsonb;  -- instant keyword triage (always)
ALTER TABLE user_feedback ADD COLUMN IF NOT EXISTS ai_label jsonb;    -- optional Workers AI triage (D-022)
ALTER TABLE station ADD COLUMN IF NOT EXISTS coord_source text;          -- NULL = HII feed; osm_approx = curated
ALTER TABLE station ADD COLUMN IF NOT EXISTS coord_precision_km real;    -- rough radius for approximate positions
ALTER TABLE station ADD COLUMN IF NOT EXISTS sub_basin integer;           -- HII sub_basin_id: a river and its tributaries
ALTER TABLE station ADD COLUMN IF NOT EXISTS warning_msl double precision;
ALTER TABLE station ADD COLUMN IF NOT EXISTS basin22 text;          -- HII basin.json (22 basins), every gauge (v0.17)
ALTER TABLE station ADD COLUMN IF NOT EXISTS river_main text;       -- HII river_main.json name within 2 km, else NULL
ALTER TABLE station ADD COLUMN IF NOT EXISTS river_system integer;  -- rivers whose lines touch share a system -- agency warning level (BMA: drainage threshold, D-038)
