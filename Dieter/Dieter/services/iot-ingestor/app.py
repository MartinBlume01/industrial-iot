import json
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psycopg

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "application/+/device/+/event/up")

PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "iot")
PG_USER = os.getenv("PG_USER", "iot_app")
PG_PASSWORD = os.getenv("PG_PASSWORD", "iot_app")


def pg_conn_string() -> str:
    return (
        f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} "
        f"user={PG_USER} password={PG_PASSWORD}"
    )


def init_db() -> None:
    with psycopg.connect(pg_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS temperature_measurements (
                  id BIGSERIAL PRIMARY KEY,
                  device_eui TEXT NOT NULL,
                  temperature_c DOUBLE PRECISION,
                  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  raw JSONB NOT NULL
                );
                """
            )
            cur.execute(
                """
                SELECT create_hypertable(
                    'temperature_measurements',
                    'received_at',
                    if_not_exists => TRUE
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_temperature_measurements_device_time
                ON temperature_measurements (device_eui, received_at DESC);
                """
            )
        conn.commit()


def extract_temperature(payload: dict) -> float | None:
    obj = payload.get("object")
    if isinstance(obj, dict):
        for key in ("temperature", "temp", "temperature_c", "temperatureC"):
            value = obj.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    return None


def extract_device_eui(payload: dict) -> str:
    device_info = payload.get("deviceInfo")
    if isinstance(device_info, dict):
        dev_eui = device_info.get("devEui")
        if isinstance(dev_eui, str) and dev_eui:
            return dev_eui

    dev_eui = payload.get("devEui")
    if isinstance(dev_eui, str) and dev_eui:
        return dev_eui

    return "unknown"


def extract_timestamp(payload: dict) -> datetime:
    ts = payload.get("time")
    if isinstance(ts, str):
        try:
            if ts.endswith("Z"):
                ts = ts.replace("Z", "+00:00")
            return datetime.fromisoformat(ts)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def store_measurement(payload: dict) -> None:
    device_eui = extract_device_eui(payload)
    temperature_c = extract_temperature(payload)
    received_at = extract_timestamp(payload)

    with psycopg.connect(pg_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO temperature_measurements (device_eui, temperature_c, received_at, raw)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                (device_eui, temperature_c, received_at, json.dumps(payload)),
            )
        conn.commit()


def on_connect(client, _userdata, _flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        print(f"Connected to MQTT and subscribed: {MQTT_TOPIC}")
    else:
        print(f"MQTT connect failed with code: {rc}")


def on_message(_client, _userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        store_measurement(payload)
        print(f"Stored measurement from topic: {msg.topic}")
    except Exception as exc:
        print(f"Error processing MQTT message ({msg.topic}): {exc}")


def wait_for_db(max_retries: int = 60, delay_seconds: int = 2) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            with psycopg.connect(pg_conn_string()) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                conn.commit()
            return
        except Exception:
            print(f"Database not ready (attempt {attempt}/{max_retries})")
            time.sleep(delay_seconds)
    raise RuntimeError("Database did not become ready in time")


def main() -> None:
    wait_for_db()
    init_db()

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
