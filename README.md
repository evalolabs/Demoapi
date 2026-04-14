# Demoapi

Demo-Tenant-API fuer MonshyBot Function Calling.

## API 1: Produktkatalog + Verfuegbarkeit + Standort

Dieses Projekt simuliert eine externe Tenant-API fuer einen fiktiven Baumarkt-Partner:

- Handelsmarke/Filialkette: `BauRaum`
- Produktlinie (fiktive Bosch-Analogie): `Voltara`

Die API liefert:

- Produktsuche
- Barcode-Lookup
- Produktdetails
- Verfuegbarkeit pro Store
- Standortdaten pro Store (Aisle/Shelf + Koordinaten)

## Schnellstart

```bash
cd Demoapi
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8100
```

Health:

```bash
curl http://localhost:8100/health
```

## Auth

API-Key wird ueber einen dieser Header akzeptiert:

- `Authorization: Bearer <key>`
- `X-API-Key: <key>`

Standard-Key (nur lokal): `demo-tenant-key`

Uebersteuerbar via Env:

- `DEMO_API_KEY`
- `DEMO_DB_PATH`
- `ATLAS_URI`
- `ATLAS_DB_NAME`

## Beispielaufrufe

Produktsuche:

```bash
curl "http://localhost:8100/v1/products/search?q=voltara bohrmaschine&limit=5" -H "X-API-Key: demo-tenant-key"
```

Barcode:

```bash
curl "http://localhost:8100/v1/products/barcode/4006381000016" -H "X-API-Key: demo-tenant-key"
```

Verfuegbarkeit:

```bash
curl "http://localhost:8100/v1/products/voltara_akku_bohrschrauber_001/availability?store_id=bauraum_berlin_01" -H "X-API-Key: demo-tenant-key"
```

Standort:

```bash
curl "http://localhost:8100/v1/products/voltara_akku_bohrschrauber_001/location?store_id=bauraum_berlin_01" -H "X-API-Key: demo-tenant-key"
```

## MongoDB Atlas seeding

Wenn du die Daten auf Atlas generieren willst:

1) Env setzen:

```bash
set ATLAS_URI=mongodb+srv://USER:PASS@CLUSTER/demoapi?retryWrites=true&w=majority
set ATLAS_DB_NAME=demoapi
```

2) Seed starten:

```bash
python seed_atlas.py
```

Optional alles neu aufbauen (Collections vorher loeschen):

```bash
python seed_atlas.py --drop-first
```

PowerShell Shortcut (ein Kommando):

```powershell
.\seed_atlas.ps1 -AtlasUri "mongodb+srv://USER:PASS@CLUSTER/demoapi?retryWrites=true&w=majority" -DbName "demoapi"
```

Mit Neuaufbau:

```powershell
.\seed_atlas.ps1 -AtlasUri "mongodb+srv://USER:PASS@CLUSTER/demoapi?retryWrites=true&w=majority" -DbName "demoapi" -DropFirst
```

PowerShell mit `.env` (kein URI im Kommando noetig):

1) `.env` anlegen (oder `.env.example` kopieren):

```env
ATLAS_URI=mongodb+srv://USER:PASS@CLUSTER/demoapi?retryWrites=true&w=majority
ATLAS_DB_NAME=demoapi
```

2) Seed starten:

```powershell
.\seed_atlas.ps1
```

Optional anderes Env-File:

```powershell
.\seed_atlas.ps1 -EnvFile ".env.prod" -DropFirst
```

Der Seeder:

- erzeugt den kompletten Datensatz deterministisch
- schreibt in `products` und `inventory`
- erstellt wichtige Indexe (inkl. unique)
- seeded nur, wenn beide Collections leer sind (ohne `--drop-first`)

## Deploy (Docker)

1) `.env` erstellen:

```env
DEMO_API_KEY=demo-tenant-key
ATLAS_URI=mongodb+srv://USER:PASS@CLUSTER/demoapi?retryWrites=true&w=majority
ATLAS_DB_NAME=demoapi
```

2) Build + Start:

```bash
docker compose up -d --build
```

3) Health pruefen:

```bash
curl http://localhost:8100/health
```

4) Atlas seeding ausfuehren:

- lokal vor dem Deploy mit `python seed_atlas.py`, oder
- im laufenden Container:

```bash
docker exec -it demoapi python seed_atlas.py
```

## GitHub Actions

Enthaltene Workflows:

- `.github/workflows/demoapi-ci.yml`: lint/smoke + Docker Build bei Push/PR
- `.github/workflows/demoapi-docker-publish.yml`: pusht Docker Image nach GHCR

GHCR Image-Name:

- `ghcr.io/<github-owner>/demoapi`

## One-command deploy scripts

### Windows (PowerShell)

```powershell
.\deploy.ps1
```

Mit Optionen:

```powershell
.\deploy.ps1 -Branch main -HealthUrl "http://127.0.0.1:8100/health"
```

### Linux/macOS

```bash
chmod +x deploy.sh
./deploy.sh
```

Mit Optionen:

```bash
HEALTH_URL=http://127.0.0.1:8100/health HEALTH_RETRIES=30 ./deploy.sh main
```

Die Deploy-Skripte machen:

- `git fetch/checkout/pull`
- `docker compose up -d --build`
- Health-Check mit Retry-Logik
