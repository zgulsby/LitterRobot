# Litter Robot → Skylight Chore Notifier

## What this project does

A Python script that polls Whisker (Litter Robot) API for waste drawer status and creates a chore on Skylight Calendar when the drawer is full or near-full. Runs on Google Cloud Run Jobs every 3 hours via Cloud Scheduler.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│ Whisker API  │────▶│  notifier.py │────▶│  Skylight API    │
│ (pylitterbot)│     │ (Cloud Run)  │     │  (chore create)  │
└─────────────┘     └──────────────┘     └──────────────────┘
                           │
                    ┌──────┴──────┐
                    │ GCS bucket  │
                    │ (state.json)│
                    └─────────────┘
```

**Core flow:**
1. Authenticate to Whisker using pylitterbot
2. Check each robot's waste drawer level and DFI (Drawer Full Indicator) status
3. If drawer is full (or above configurable threshold), check if we already created a chore recently (dedup via state file in GCS)
4. If no recent chore exists, create a Skylight chore titled "🐱 Empty Litter Robot" in the Family category
5. After user empties and resets the drawer, the next poll sees it's clear and resets the dedup state

## Project structure

```
litter-robot-notifier/
├── CLAUDE.md              # This file
├── pyproject.toml         # Project config and dependencies
├── Dockerfile             # Container image for Cloud Run
├── run.sh                 # Local run script (optional)
├── .env.example           # Template for secrets
├── .env                   # Actual secrets (gitignored)
├── .gitignore
├── state.json             # Dedup state tracking (gitignored, auto-generated locally)
├── src/
│   ├── __init__.py
│   ├── main.py            # Entry point — run this
│   ├── whisker_client.py  # Whisker/Litter Robot API wrapper
│   ├── skylight_client.py # Skylight Calendar API wrapper (chore creation)
│   ├── notifier.py        # Orchestration logic (check status → decide → notify)
│   └── config.py          # Configuration from env vars
└── tests/
    └── test_notifier.py   # Basic tests
```

## Key dependencies

- `pylitterbot` — unofficial Whisker API client (supports LR3, LR4, Feeder-Robot)
- `requests` — HTTP client for Skylight API
- `python-dotenv` — env var loading
- `google-cloud-storage` — GCS state persistence for Cloud Run

## Setup instructions (for the human)

1. **Whisker credentials**:
   - Copy `.env.example` to `.env`
   - Fill in your Whisker (Litter Robot app) email and password

2. **Skylight credentials**:
   - Add your Skylight email and password to `.env`

3. **Local run**:
   - `python -m src.main`
   - Uses local `state.json` for dedup tracking

## Configuration (via .env)

- `WHISKER_EMAIL` — Whisker account email
- `WHISKER_PASSWORD` — Whisker account password
- `SKYLIGHT_EMAIL` — Skylight Calendar account email
- `SKYLIGHT_PASSWORD` — Skylight Calendar account password
- `DRAWER_THRESHOLD` — Waste drawer % to trigger notification (default: 80)
- `CHORE_SUMMARY` — Chore title on Skylight (default: "🐱 Empty Litter Robot")
- `DEDUP_HOURS` — Don't create another chore within this many hours (default: 12)

## Cloud Run deployment

- **Project**: `litter-robot-notifications`
- **Region**: `us-central1`
- **Job**: `litter-robot-poller`
- **Scheduler**: `litter-robot-schedule` (every 3 hours)
- **Service account**: `litter-robot-runner@litter-robot-notifications.iam.gserviceaccount.com`
- **Image**: `us-central1-docker.pkg.dev/litter-robot-notifications/litter-robot/poller:latest`
- **GCS bucket**: `litter-robot-notifications-state` (stores `state.json`)
- **Secrets**: stored in Google Secret Manager, injected as env vars

To redeploy after code changes:
```bash
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/litter-robot-notifications/litter-robot/poller:latest .
docker push us-central1-docker.pkg.dev/litter-robot-notifications/litter-robot/poller:latest
gcloud run jobs update litter-robot-poller --image us-central1-docker.pkg.dev/litter-robot-notifications/litter-robot/poller:latest --region us-central1 --project litter-robot-notifications
```

## Important technical notes

- **pylitterbot is unofficial** — reverse-engineered from the Whisker app. It could break if Whisker changes their API. The library is actively maintained and used by 3700+ Home Assistant installations.
- **Skylight API is unofficial** — reverse-engineered from the Skylight web app (`https://app.ourskylight.com/api`). Uses email/password auth → session token → Basic Auth. Could break if Skylight changes their API.
- **Dedup logic** — state.json tracks the last notification timestamp per robot serial. If a notification was sent within DEDUP_HOURS, skip. Reset state when drawer level drops below threshold. In Cloud Run, state is stored in GCS.
- **LR3 vs LR4** — LR3 uses `isDFITriggered` flag. LR4 exposes `waste_drawer_level` as a percentage. Handle both.
- **Error handling** — if Whisker auth fails or Skylight API fails, log the error and exit cleanly. Don't crash the Cloud Run job.
- **Skylight chore category** — chores are created under the "Family" category (non-linked, shared across all household members).

## Style and conventions

- Python 3.11+
- Type hints everywhere
- Use `asyncio` (pylitterbot is async)
- Use `logging` module, not print statements
- Keep it simple — this is a single-purpose utility, not a framework
