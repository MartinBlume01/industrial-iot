# Debian 13 Deployment Guide

Diese Anleitung beschreibt den Betrieb des Projekts auf Debian 13 (Trixie) mit Docker und optional Portainer.

Zusätzliche schnelle Fehlerbehebung: [docs/linux-troubleshooting.md](linux-troubleshooting.md)

## 1) Voraussetzungen

- Debian 13 Server mit Internetzugang
- Öffentliche oder interne statische IP
- Ports im Firewall-Konzept freigegeben:
  - `1700/udp` (LoRa Gateway -> Gateway Bridge)
  - `8080/tcp` (ChirpStack UI/API)
  - `3000/tcp` (Grafana)
  - `1883/tcp` (MQTT, nur falls extern benötigt)

## 2) Docker + Portainer installieren

```bash
sudo bash scripts/debian13/install-docker-portainer.sh
```

Danach Portainer öffnen:
- `https://<server-ip>:9443`

## 3) Projekt bereitstellen

### Option A: Direkt mit Docker Compose (CLI)

```bash
cp .env.portainer.example .env
nano .env

docker compose up -d --build
```

### Option B1: Über Portainer Stack (Repository + Build)

- In Portainer: **Stacks -> Add stack -> Repository**
- Repository mit diesem Projekt angeben
- Compose Path: `Dieter/docker-compose.yml`
- Environment Variablen aus `.env.portainer.example` setzen
- Deploy klicken

### Option B2: Über Portainer Web editor / ohne Build-Kontext

Wenn ihr den Stack im Portainer Web editor einfügt, ist `./services/iot-ingestor` als Build-Kontext nicht verfügbar.

- Compose-Datei: `docker-compose.portainer.yml`
- Compose-Datei: `Dieter/docker-compose.portainer.yml`
- Environment Variablen aus `.env.portainer.prebuilt.example` setzen
- `IOT_INGESTOR_IMAGE` muss auf ein vorhandenes Registry-Image zeigen
- Deploy klicken

Schnellstart-Env (Copy/Paste für Portainer):

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change_me_strong
POSTGRES_PORT=5432

MQTT_PORT=1883
MQTT_INTERNAL_PORT=1883

CHIRPSTACK_PORT=8080
CHIRPSTACK_API_SECRET=change_me_chirpstack_api_secret
CHIRPSTACK_LOG_LEVEL=info
CHIRPSTACK_NETWORK_ENABLED_REGIONS=eu868

LORA_UDP_PORT=1700

PG_HOST=postgres
PG_PORT=5432
PG_DB=iot
PG_USER=iot_app
PG_PASSWORD=iot_app

GRAFANA_PORT=3000
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=change_me_grafana_admin

IOT_INGESTOR_IMAGE=ghcr.io/martinblume01/industrial-iot-ingestor:latest
MQTT_BROKER=mosquitto
MQTT_TOPIC=application/+/device/+/event/up
```

GitHub Owner `MartinBlume01` wird in Image-Namen kleingeschrieben zu `martinblume01`.

Beispiel zum Vorab-Build + Push:

```bash
docker build -t industrial-iot-ingestor:1.0.0 ./services/iot-ingestor
```

Anschließend GHCR-Tag setzen und pushen:

```bash
docker tag industrial-iot-ingestor:1.0.0 ghcr.io/martinblume01/industrial-iot-ingestor:1.0.0
docker login ghcr.io
docker push ghcr.io/martinblume01/industrial-iot-ingestor:1.0.0
```

Wichtig:
- Für GHCR immer den Owner in Kleinbuchstaben verwenden (`martinblume01`).

## 4) Automatischer Build nach GHCR (GitHub Actions)

Im Repository ist ein Workflow hinterlegt:
- `.github/workflows/iot-ingestor-ghcr.yml`

Der Workflow baut und pusht bei Änderungen in `services/iot-ingestor/**` automatisch nach GHCR.

Ergebnis-Image (Schema):
- `ghcr.io/<github-owner-lowercase>/industrial-iot-ingestor:latest` (nur Default-Branch)
- `ghcr.io/<github-owner-lowercase>/industrial-iot-ingestor:sha-<commit>`

Voraussetzungen:
- Repository liegt auf GitHub
- Actions sind aktiviert
- Standard-`GITHUB_TOKEN` hat Paketrechte (im Workflow gesetzt: `packages: write`)

Danach in Portainer setzen:
- `IOT_INGESTOR_IMAGE=ghcr.io/<github-owner-lowercase>/industrial-iot-ingestor:latest`

Hinweis für private Images:
- In Portainer unter **Registries** `ghcr.io` mit GitHub-User + PAT (`read:packages`) hinterlegen.

## 5) Debian-spezifischer Hinweis (Webhook)

Die Compose-Datei enthält für Grafana bereits:
- `extra_hosts: host.docker.internal:host-gateway`

Damit funktioniert das Standard-Webhook-Ziel `http://host.docker.internal:5001/alerts` auch auf Linux. Wenn euer Empfänger extern läuft, URL in `grafana/provisioning/alerting/contact-points.yml` anpassen.

## 6) Betrieb prüfen

```bash
docker compose ps
docker compose logs -f iot-ingestor
docker compose logs -f chirpstack-gateway-bridge
```

## 7) Sicherheit vor Go-Live

- Standard-Passwörter/Secrets in `.env` ersetzen
- MQTT-Anonymous in `mosquitto/mosquitto.conf` deaktivieren
- Reverse-Proxy + TLS vor Grafana/ChirpStack setzen
- DB-Backups testen (Restore-Test)
