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

CREATE TABLE IF NOT EXISTS source_health (
    source               text PRIMARY KEY,
    last_success         timestamptz,
    last_error           timestamptz,
    last_error_msg       text,
    consecutive_failures integer NOT NULL DEFAULT 0,
    last_data_time       timestamptz
);
