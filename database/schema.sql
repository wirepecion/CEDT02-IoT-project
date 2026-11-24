-- ===== TimescaleDB (run in psql, database "pilot") =====
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE TABLE IF NOT EXISTS sensor_readings (
  time        timestamptz NOT NULL,
  device_id   text        NOT NULL,
  temperature double precision,
  humidity    double precision
);
SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_sr_device_time ON sensor_readings (device_id, time DESC);
-- Optional: drop data older than 90 days
-- SELECT add_retention_policy('sensor_readings', INTERVAL '90 days');

-- ===== QuestDB (run in web console http://localhost:9000) =====
-- CREATE TABLE sensor_readings (
--   ts TIMESTAMP, device_id SYMBOL, temperature DOUBLE, humidity DOUBLE,
--   gas LONG, light LONG, distance DOUBLE      -- gas/light/distance: from the ESP32 via the Pi
-- ) TIMESTAMP(ts) PARTITION BY DAY TTL 90d;   -- TTL needs a recent version; remove if rejected

-- ===== GreptimeDB (psql -h 127.0.0.1 -p 4003 -d public) =====
-- CREATE TABLE sensor_readings (
--   ts TIMESTAMP TIME INDEX, device_id STRING PRIMARY KEY,
--   temperature DOUBLE, humidity DOUBLE
-- );
