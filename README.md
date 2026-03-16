# Litter Robot → Skylight Chore Notifier

Automatically creates a chore on your [Skylight Calendar](https://www.ourskylight.com/) when your Litter Robot's waste drawer needs emptying.

Polls the [Whisker](https://www.litter-robot.com/) API every few hours, checks each robot's waste drawer level, and creates a Skylight chore when it crosses a configurable threshold (default: 80%).

## How it works

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│ Whisker API  │────▶│  Poller      │────▶│  Skylight API    │
│ (pylitterbot)│     │  (cron/Cloud │     │  (chore create)  │
│              │     │   Run Job)   │     │                  │
└─────────────┘     └──────────────┘     └──────────────────┘
```

1. Authenticates to Whisker using [pylitterbot](https://github.com/natekspencer/pylitterbot)
2. Checks each robot's waste drawer level (LR4 percentage) or DFI flag (LR3)
3. If above threshold, checks dedup state to avoid duplicate chores
4. Creates a Skylight chore (e.g. "🐱 Empty Litter Robot") in the Family category
5. When the drawer is emptied and drops below threshold, resets dedup state

## Quick start

### Prerequisites

- Python 3.11+
- A [Whisker](https://www.litter-robot.com/) account (the Litter Robot app)
- A [Skylight Calendar](https://www.ourskylight.com/) account

### Setup

```bash
git clone https://github.com/zgulsby/LitterRobot.git
cd LitterRobot
pip install .
```

Copy the environment template and fill in your credentials:

```bash
cp .env.example .env
# Edit .env with your Whisker and Skylight credentials
```

### Run

```bash
python -m src.main
```

On the first run, it will check all your Litter Robots and create a Skylight chore if any drawer is above the threshold.

### Run on a schedule

**Option A: crontab (local machine)**

```bash
crontab -e
# Add: */180 * * * * cd /path/to/LitterRobot && /path/to/python -m src.main
```

**Option B: Google Cloud Run Jobs (recommended)**

Deploy as a containerized job that runs on a schedule, independent of your local machine:

```bash
# Build and push
docker build --platform linux/amd64 -t us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/poller:latest .
docker push us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/poller:latest

# Create Cloud Run Job
gcloud run jobs create litter-robot-poller \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT/YOUR_REPO/poller:latest \
  --region us-central1 \
  --set-env-vars WHISKER_EMAIL=...,WHISKER_PASSWORD=...,SKYLIGHT_EMAIL=...,SKYLIGHT_PASSWORD=...

# Create Cloud Scheduler trigger (every 3 hours)
gcloud scheduler jobs create http litter-robot-schedule \
  --schedule "0 */3 * * *" \
  --uri "https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/YOUR_PROJECT/jobs/litter-robot-poller:run" \
  --http-method POST \
  --oauth-service-account-email YOUR_SERVICE_ACCOUNT
```

For persistent state across runs, set `GCS_BUCKET` to a GCS bucket name and the dedup state will be stored there instead of the local filesystem.

## Configuration

All configuration is via environment variables (or `.env` file):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WHISKER_EMAIL` | Yes | — | Your Whisker (Litter Robot) account email |
| `WHISKER_PASSWORD` | Yes | — | Your Whisker account password |
| `SKYLIGHT_EMAIL` | Yes | — | Your Skylight Calendar account email |
| `SKYLIGHT_PASSWORD` | Yes | — | Your Skylight Calendar account password |
| `DRAWER_THRESHOLD` | No | `80` | Waste drawer % to trigger a chore (0-100) |
| `CHORE_SUMMARY` | No | `🐱 Empty Litter Robot` | Chore title on Skylight |
| `DEDUP_HOURS` | No | `12` | Hours to wait before creating another chore |
| `GCS_BUCKET` | No | — | GCS bucket for state persistence (Cloud Run) |

## Supported devices

- **Litter-Robot 4** — uses `waste_drawer_level` percentage
- **Litter-Robot 3** — uses `isDFITriggered` boolean flag (full/not full)

## Technical notes

- **pylitterbot** is an unofficial, reverse-engineered Whisker API client. It's actively maintained and used by 3,700+ Home Assistant installations, but could break if Whisker changes their API.
- **Skylight API** is also unofficial/reverse-engineered (`https://app.ourskylight.com/api`). Uses email/password → session token auth. Could break if Skylight changes their API.
- **Dedup logic** prevents duplicate chores. A `state.json` file tracks when each robot was last notified. If a chore was created within `DEDUP_HOURS`, it won't create another. State resets when the drawer drops below threshold.

## License

MIT
