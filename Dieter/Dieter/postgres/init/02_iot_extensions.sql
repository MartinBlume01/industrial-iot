\connect iot
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS temperature_measurements (
  id BIGSERIAL PRIMARY KEY,
  device_eui TEXT NOT NULL,
  temperature_c DOUBLE PRECISION,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  raw JSONB NOT NULL
);

SELECT create_hypertable('temperature_measurements', 'received_at', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_temperature_measurements_device_time
  ON temperature_measurements (device_eui, received_at DESC);
