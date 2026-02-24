# Industrial IoT Server Stack (LoRaWAN + Open Source)

Dieses Setup stellt einen eigenen Server bereit, der:
- LoRaWAN-Daten vom Gateway annimmt,
- Temperaturdaten in TimescaleDB speichert,
- Auswertung und Alarmierung über Grafana ermöglicht.

## Enthaltene Komponenten

- `chirpstack/chirpstack` (LoRaWAN Network Server + UI)
- `chirpstack/chirpstack-gateway-bridge` (UDP 1700 vom Gateway zu MQTT)
- `eclipse-mosquitto` (MQTT Broker)
- `timescale/timescaledb` (PostgreSQL + Timescale)
- `grafana/grafana-oss` (Dashboards / Auswertung)
- `iot-ingestor` (MQTT `up` Events -> Tabelle `temperature_measurements`)

## Start

1. Im Projektordner starten:

```bash
docker compose up -d --build
```

## Debian 13 (Trixie)

- Für Debian 13 gibt es eine fertige Anleitung: [docs/debian13-deployment.md](docs/debian13-deployment.md)
- Docker + Portainer Installation per Script:

```bash
sudo bash scripts/debian13/install-docker-portainer.sh
```

## Deployment mit Portainer (Stacks)

Empfohlen: Stack aus einem Git-Repository deployen, damit alle relativen Pfade (`./grafana`, `./chirpstack`, `./postgres/init`) korrekt verfügbar sind.

Wichtig:
- Der Portainer **Web editor** hat keinen Zugriff auf euren lokalen Projektordner als Build-Kontext.
- `docker-compose.yml` mit `build: ./services/iot-ingestor` funktioniert dort daher nicht zuverlässig.
- Für Web-editor/ohne Build immer `docker-compose.portainer.yml` + fertiges Registry-Image verwenden.

1. Datei `.env.portainer.example` nach `.env` kopieren und Passwörter/Secrets anpassen.
2. In Portainer: **Stacks -> Add stack -> Repository**.
3. Repository mit diesem Projekt angeben und als Compose-Pfad `docker-compose.yml` setzen.
4. Bei Bedarf Environment-Variablen in Portainer überschreiben.
5. Stack deployen.

Hinweis zum `iot-ingestor` Service:
- Der Stack enthält `build` + `image`.
- Wenn euer Portainer-Setup kein Image-Build zulässt, baut das Image vorher in einer CI/CD Pipeline und setzt `IOT_INGESTOR_IMAGE` auf euer Registry-Image.

### Portainer ohne Build (nur fertige Images)

Für restriktive Portainer-Umgebungen nutzt ihr direkt:
- Compose: `docker-compose.portainer.yml`
- Env-Beispiel: `.env.portainer.prebuilt.example`

Vorgehen:
1. Env-Werte setzen (insbesondere `IOT_INGESTOR_IMAGE` auf euer Registry-Image)
2. In Portainer als Compose-Datei `docker-compose.portainer.yml` verwenden
3. Stack deployen (ohne Build-Schritt)

Image vorab bauen und pushen (Beispiel):

```bash
docker build -t industrial-iot-ingestor:1.0.0 ./services/iot-ingestor
```

Dann lokal gebautes Image für GHCR taggen und pushen:

```bash
docker tag industrial-iot-ingestor:1.0.0 ghcr.io/martinblume01/industrial-iot-ingestor:1.0.0
docker login ghcr.io
docker push ghcr.io/martinblume01/industrial-iot-ingestor:1.0.0
```

Hinweis:
- GitHub-Owner `MartinBlume01` wird in GHCR-Image-Namen kleingeschrieben zu `martinblume01`.

2. Zugriff:
- ChirpStack UI: `http://localhost:8080`
- Grafana: `http://localhost:3000` (User: `admin`, Passwort: `admin_change_me`)

Nach dem Start ist ein Dashboard automatisch vorhanden:
- `Industrial IoT / Factory Temperature Overview`
- Panels: Temperaturverlauf, letzte Messwerte, Anzahl Abweichungen, aktive Abweichungen

Zusätzlich ist ein Alerting-Setup automatisch provisioniert:
- Alert-Regel: `Temperature Out Of Range`
- Trigger: Wenn mindestens 1 Messstelle außerhalb `5°C .. 80°C` liegt (für 2 Minuten)
- Contact Point: `iot-webhook` (Standardziel: `http://host.docker.internal:5001/alerts`)

3. Stack prüfen:

```bash
docker compose ps
docker compose logs -f iot-ingestor
```

## MikroTik wAP LR8G Gateway (Grundprinzip)

- Packet Forwarder auf euren Server zeigen lassen:
  - Server-IP: IP eures Docker-Hosts
  - UDP Port: `1700`
- Region / Frequenzplan: `EU868`
- Gateway EUI notieren und in ChirpStack als Gateway registrieren.

## Datenmodell

Tabelle: `temperature_measurements`
- `device_eui` (Text)
- `temperature_c` (Double)
- `received_at` (Timestamp with timezone)
- `raw` (JSONB)

Die Tabelle ist als Hypertable in TimescaleDB angelegt.

## Auswertungsbeispiele (SQL)

Alle letzten Temperaturen je Messstelle:

```sql
SELECT
  device_eui,
  max(received_at) AS last_seen,
  (array_agg(temperature_c ORDER BY received_at DESC))[1] AS latest_temp_c
FROM temperature_measurements
GROUP BY device_eui
ORDER BY last_seen DESC;
```

Aktive Abweichungen (unter 5°C oder über 80°C):

```sql
WITH latest AS (
  SELECT DISTINCT ON (device_eui)
    device_eui,
    received_at,
    temperature_c
  FROM temperature_measurements
  ORDER BY device_eui, received_at DESC
)
SELECT device_eui, temperature_c, received_at
FROM latest
WHERE temperature_c IS NOT NULL
  AND (temperature_c < 5 OR temperature_c > 80)
ORDER BY received_at DESC;
```

## Wichtige nächste Schritte (Produktion)

- Alle Standard-Passwörter ersetzen (`docker-compose.yml`).
- TLS/Reverse Proxy für externe Zugriffe aktivieren.
- MQTT Auth aktivieren (statt `allow_anonymous true`).
- Regelmäßige DB-Backups + Restore-Test einrichten.
- In ChirpStack Payload-Codec für Sensoren konfigurieren, damit `temperature` sauber in `object` steht.

## Alerting anpassen

- Webhook-Ziel ändern: `grafana/provisioning/alerting/contact-points.yml`
- Grenzwerte ändern: `grafana/provisioning/alerting/rules.yml` (`temperature_c < 5 OR temperature_c > 80`)
- Nach Änderungen Grafana neu starten:

```bash
docker compose restart grafana
```
