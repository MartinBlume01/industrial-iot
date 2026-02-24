# Linux Troubleshooting Guide (Dieter)

Diese Kurzanleitung hilft bei den häufigsten Problemen beim Betrieb des Stacks auf Linux.

## 1) Build-Kontext in Portainer fehlt

Fehlermeldung (typisch):
- `path .../services/iot-ingestor not found`

Ursache:
- Falscher Compose-Pfad im Git-Deployment oder Nutzung des Web Editors ohne passenden Kontext.

Fix:
- Repository: `https://github.com/MartinBlume01/industrial-iot`
- Compose Path mit Unterordner setzen:
  - Mit Build: `Dieter/docker-compose.yml`
  - Ohne Build: `Dieter/docker-compose.portainer.yml`

## 2) Image kann nicht gezogen werden

Fehlermeldung (typisch):
- `pull access denied ... industrial-iot-ingestor`

Ursache:
- `IOT_INGESTOR_IMAGE` zeigt auf ein nicht existentes oder nicht zugreifbares Image.

Fix:
- `IOT_INGESTOR_IMAGE=ghcr.io/martinblume01/industrial-iot-ingestor:1.0.0`

Wenn GHCR privat ist:
- `echo <PAT> | docker login ghcr.io -u MartinBlume01 --password-stdin`
- PAT benötigt mindestens `read:packages`

## 3) Git Push Auth schlägt fehl

Fehlermeldung (typisch):
- `Invalid username or token`
- `Password authentication is not supported for Git operations`

Ursache:
- GitHub-Passwort statt Personal Access Token (PAT) verwendet.

Fix:
- PAT classic mit Scope `repo` erstellen
- Bei `git push`:
  - Username: `MartinBlume01`
  - Password: PAT (nicht GitHub-Passwort)

## 4) iot-ingestor läuft, aber schreibt keine Daten

Checks:
- `docker compose logs -f iot-ingestor`
- `docker compose logs -f mosquitto`

Env prüfen:
- `MQTT_BROKER=mosquitto`
- `MQTT_TOPIC=application/+/device/+/event/up`
- `PG_HOST=postgres`
- `PG_DB=iot`
- `PG_USER=iot_app`
- `PG_PASSWORD=iot_app`

## 5) Services laufen, UI nicht erreichbar

Checks:
- `docker compose ps`
- Firewall/Ports prüfen:
  - `8080/tcp` (ChirpStack)
  - `3000/tcp` (Grafana)
  - `1700/udp` (Gateway Bridge)

## 6) Basis-Reset bei undefiniertem Zustand

Im Projektordner (`industrial-iot/Dieter`):

```bash
docker compose down
docker compose up -d --build
docker compose logs -f
```

## 7) Schneller Gesundheitscheck

```bash
docker compose ps
docker compose logs -f iot-ingestor
docker compose logs -f chirpstack-gateway-bridge
```
