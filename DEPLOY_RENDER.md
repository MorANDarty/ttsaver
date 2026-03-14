# Deploy to Render with Keepalive

Render free web services can spin down after inactivity, so this bot uses a small HTTP health endpoint and an external keepalive ping.

## Why This Works

- The bot still uses Telegram polling.
- The app now also exposes `GET /healthz`.
- Render can treat it like a web service.
- An external uptime monitor can hit `/healthz` every 10 minutes to keep the service warm.

## Render Setup

Use the Blueprint already included in [render.yaml](/Users/lilmir/Documents/ttsaver/render.yaml).

Service shape:

- type: `web`
- runtime: `docker`
- plan: `free`
- health check path: `/healthz`

## Environment Variables

Set these in Render:

```env
BOT_TOKEN=...
ADMIN_USER_IDS=123456789
ACCESS_REQUEST_COOLDOWN_HOURS=24
TEMP_DIR=./data/temp
DB_PATH=./data/app.db
MAX_VIDEO_SIZE_MB=50
CACHE_TTL_HOURS=72
REQUESTS_PER_USER_PER_DAY=20
CLEANUP_MAX_AGE_HOURS=12
LOG_LEVEL=INFO
FFMPEG_PATH=/usr/bin/ffmpeg
DOWNLOAD_TIMEOUT_SEC=180
FFMPEG_TIMEOUT_SEC=180
HEALTH_HOST=0.0.0.0
PORT=10000
```

Notes:

- `ADMIN_USER_IDS` are the Telegram users who can approve or reject access requests.
- User access is stored in SQLite and requested through `/req_permission`.
- `ALLOWED_USER_IDS` is no longer required for normal operation; keep it only as a temporary migration fallback if needed.

## Keepalive

Use an external pinger such as UptimeRobot, Better Stack, or any cron-based HTTP monitor.

Recommended ping target:

- `https://<your-render-service>.onrender.com/healthz`

Recommended interval:

- every 10 minutes

Why 10 minutes:

- Render free services sleep after about 15 minutes without inbound traffic
- 10 minutes gives enough margin without over-pinging

## Constraints

- This is a workaround, not a guaranteed always-on SLA.
- The service can still restart or rebuild independently of keepalive pings.
- SQLite remains ephemeral on free infrastructure, so cache can disappear after restart/redeploy.
- Keeping the service awake continuously will consume free monthly instance hours.
