DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'chirpstack') THEN
    CREATE ROLE chirpstack WITH LOGIN PASSWORD 'chirpstack';
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'iot_app') THEN
    CREATE ROLE iot_app WITH LOGIN PASSWORD 'iot_app';
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'chirpstack') THEN
    CREATE DATABASE chirpstack OWNER chirpstack;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'iot') THEN
    CREATE DATABASE iot OWNER iot_app;
  END IF;
END $$;
