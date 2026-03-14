# Deploy to Northflank Sandbox

This bot is a good fit for Northflank Sandbox because:

- it is a long-running background process
- it uses Telegram polling, not webhooks
- it does not need a public HTTP port
- the app already ships with a Dockerfile that installs `ffmpeg`

## Recommended Northflank Setup

Create a `combined service` from your Git repository.

Use these settings:

- Source: your Git repository
- Branch: your main branch
- Build type: `Dockerfile`
- Dockerfile path: `/Dockerfile`
- Build context: `/`
- Ports: none
- Public networking: disabled

Northflank docs used for this setup:

- [Build and deploy your code](https://northflank.com/docs/v1/application/getting-started/build-and-deploy-your-code)
- [Build with a Dockerfile](https://northflank.com/docs/v1/application/build/build-with-a-dockerfile)

## Environment Variables

Set these runtime environment variables in the Northflank service:

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
```

Notes:

- `BOT_TOKEN` should be added as a secret
- `ADMIN_USER_IDS` can also be stored as a secret if you prefer
- user access is requested through `/req_permission` and stored in SQLite
- `ALLOWED_USER_IDS` is optional now and should only be kept as a migration fallback
- `DB_PATH` stays inside the container filesystem, so cache is temporary across redeploys

## Deploy Flow

1. Push this project to GitHub, GitLab, or another Git provider supported by Northflank.
2. Create a new project in Northflank.
3. Create a new `combined service`.
4. Select the repository and branch.
5. Choose `Dockerfile` build.
6. Set Dockerfile path to `/Dockerfile` and build context to `/`.
7. Do not add any public port.
8. Add the runtime environment variables.
9. Create the service and wait for the first build/deploy to finish.

## Verification

After deploy:

1. Open service logs in Northflank.
2. Confirm you see bot startup logs and polling start.
3. Send `/start` to the bot in Telegram.
4. Send one TikTok link and one Instagram Reel.
5. Call `/stats` from the admin account.

## Expected Constraints

- The SQLite cache is not durable across container replacement or redeploy.
- If Northflank changes Sandbox limits, available resources may become too small for some downloads or compression jobs.
- `yt-dlp` will require maintenance over time as TikTok and Instagram change.
