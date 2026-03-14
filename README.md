# ttsaver

Private Telegram bot for saving public TikTok videos and Instagram Reels for approved Telegram users.

## Stack

- Python 3.12
- aiogram
- yt-dlp
- ffmpeg
- SQLite

## Features

- direct-message Telegram bot
- access request flow with admin approval via `/req_permission`
- support only for public TikTok and Instagram Reel links
- temporary SQLite cache with Telegram `file_id` reuse
- per-user daily rate limit
- one active download per user
- commands: `/start`, `/help`, `/req_permission`, `/stats`
- startup and per-request cleanup of temporary files
- clear error for oversized videos above the 50 MB Telegram bot limit

## Project Structure

```text
app/
  handlers/
  services/
  storage/
  utils/
data/
tests/
```

## Local Run

Prerequisites:

- Python 3.12
- `ffmpeg` installed on the host

Setup:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

## Configuration

Main environment variables:

- `BOT_TOKEN`: Telegram bot token
- `ADMIN_USER_IDS`: comma-separated admin IDs for `/stats`
- `ACCESS_REQUEST_COOLDOWN_HOURS`: cooldown after rejection, default `24`
- `DB_PATH`: SQLite database path
- `TEMP_DIR`: temporary working directory for downloads
- `MAX_VIDEO_SIZE_MB`: max upload size, default `50`
- `CACHE_TTL_HOURS`: cache TTL, default `72`
- `REQUESTS_PER_USER_PER_DAY`: per-user daily quota
- `ALLOWED_USER_IDS`: optional legacy fallback for already trusted users during migration

## Behavior Notes

- The bot accepts only HTTP/HTTPS links.
- Instagram support is limited to public Reels.
- TikTok short links are cached by their normalized short URL because the bot does not resolve redirects separately.
- Videos are not kept long-term. Files are deleted after each request, and only metadata plus Telegram `file_id` remain in SQLite.
- If the original file is too large, the bot makes one ffmpeg compression attempt. If the file still exceeds the configured limit, the bot returns a clear error.

## Tests

```bash
pytest
```

## Docker

Build and run:

```bash
docker build -t ttsaver .
docker run --env-file .env ttsaver
```

## Render Deploy

Recommended deploy path right now: Render with a keepalive workaround.

How this project is adapted for Render:

- the bot still uses Telegram polling
- the app now exposes `GET /healthz`
- Render can run it as a Docker-based `web` service
- an external monitor can ping `/healthz` every 10 minutes to prevent idle sleep on the free tier

Files:

- [render.yaml](/Users/lilmir/Documents/ttsaver/render.yaml)
- [DEPLOY_RENDER.md](/Users/lilmir/Documents/ttsaver/DEPLOY_RENDER.md)

Operational note:

- SQLite cache in `./data/app.db` is local to the container filesystem
- after redeploy or container replacement, cache can be lost
- this is acceptable for the current MVP because the cache is only an optimization

## Northflank Alternative

Northflank is still documented in [DEPLOY_NORTHFLANK.md](/Users/lilmir/Documents/ttsaver/DEPLOY_NORTHFLANK.md), but in practice account billing may still block service creation before you can use Sandbox.

## Before Deploy

- create a real `.env`
- verify `ffmpeg` is available on the host
- make sure the bot token belongs to the correct BotFather bot
- set correct admin IDs
- run a few real TikTok and Reel manual tests because `yt-dlp` behavior changes over time
- configure a keepalive monitor for `/healthz` if using Render free tier
- push the project to a Git remote before deploying to Northflank or Render
