# ttsaver

Private Telegram bot for saving public TikTok videos and Instagram Reels for a small whitelist of trusted users.

## Stack

- Python 3.12
- aiogram
- yt-dlp
- ffmpeg
- SQLite

## Features

- direct-message Telegram bot
- whitelist by Telegram `user_id`
- support only for public TikTok and Instagram Reel links
- temporary SQLite cache with Telegram `file_id` reuse
- per-user daily rate limit
- one active download per user
- commands: `/start`, `/help`, `/stats`
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
- `ALLOWED_USER_IDS`: comma-separated whitelist
- `ADMIN_USER_IDS`: comma-separated admin IDs for `/stats`
- `DB_PATH`: SQLite database path
- `TEMP_DIR`: temporary working directory for downloads
- `MAX_VIDEO_SIZE_MB`: max upload size, default `50`
- `CACHE_TTL_HOURS`: cache TTL, default `72`
- `REQUESTS_PER_USER_PER_DAY`: per-user daily quota

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

## Northflank Sandbox

Recommended deploy target for this MVP: Northflank Sandbox.

Why:

- the bot is a long-running polling process
- it does not need inbound HTTP traffic
- Northflank Sandbox is positioned as always-on
- Docker deployment fits the `ffmpeg` requirement cleanly

Recommended service type:

- create a `combined service`
- build from Git with `Dockerfile`
- do not expose any public ports

Detailed instructions:

- [DEPLOY_NORTHFLANK.md](/Users/lilmir/Documents/ttsaver/DEPLOY_NORTHFLANK.md)

Important operational note:

- SQLite cache in `./data/app.db` is local to the container filesystem
- after redeploy or container replacement, cache can be lost
- this is acceptable for the current MVP because the cache is only an optimization

## Render Fallback

Render remains a valid fallback option, but it is less attractive for a polling bot because free services can sleep after inactivity.

If you still want Render, the repo already includes [render.yaml](/Users/lilmir/Documents/ttsaver/render.yaml) for a Docker-based worker deployment.

## Before Deploy

- create a real `.env`
- verify `ffmpeg` is available on the host
- make sure the bot token belongs to the correct BotFather bot
- set correct whitelist/admin IDs
- run a few real TikTok and Reel manual tests because `yt-dlp` behavior changes over time
- push the project to a Git remote before deploying to Northflank or Render
