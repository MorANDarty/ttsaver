# Telegram Bot for Saving TikTok and Instagram Reels

## 1. Goal

Build a private Telegram bot for 5-10 trusted users that:

- accepts links to TikTok videos and Instagram Reels
- downloads the video
- sends the video back in Telegram
- does not depend on third-party "download websites"
- runs at zero infrastructure cost

Constraints:

- only public TikTok and Instagram Reel links are supported
- bot is private and protected by whitelist
- long-term video storage is not needed
- temporary cache is enough
- if the resulting file is larger than 50 MB and cannot be reduced safely, the bot returns an error

## 2. Product Scope

### MVP

- private Telegram bot in direct messages
- whitelist of allowed Telegram user IDs
- support for:
  - `tiktok.com`
  - `vt.tiktok.com`
  - `instagram.com/reel/...`
- download and return video to user
- temporary local file storage
- temporary metadata cache in SQLite
- repeated requests for the same link should reuse Telegram `file_id` if available
- basic rate limiting
- basic logs and admin stats

### Out of Scope for v1

- public bot for anyone
- private Instagram accounts
- Stories, carousels, live streams
- permanent media archive
- payment, subscriptions, analytics dashboards
- multi-server scaling

## 3. Recommended Stack

### Application

- `Python 3.12`
- `aiogram` for Telegram bot
- `yt-dlp` for extracting video from TikTok and Instagram
- `ffmpeg` for optional compression/remux
- `SQLite` for cache and service metadata

### Deployment

- primary option: `Northflank Sandbox`
- fallback option: `Render Free`

### Why this stack

- Python is the fastest path to a reliable bot
- `yt-dlp` is the most pragmatic downloader for these sources
- SQLite is sufficient for 5-10 users
- one process is enough, no queue broker required

## 4. Key Technical Constraint

Telegram Bot API is the main limiter for MVP:

- normal bot flow should assume a `50 MB` practical upload limit for returned video
- therefore the app must:
  - check output file size before sending
  - optionally try a compression pass
  - return a clear message if file is still too large

This should be treated as a product rule, not an edge case.

## 5. High-Level Architecture

One service is enough:

1. Telegram receives user message with URL
2. Bot validates user and link
3. Bot checks cache by normalized URL
4. If cached Telegram `file_id` exists, bot reuses it
5. If not cached:
   - download video with `yt-dlp`
   - inspect file size
   - if needed, compress with `ffmpeg`
   - send video to Telegram
   - save `file_id` in cache
6. Delete temporary file(s)

No separate worker is needed for MVP.

## 6. Proposed Project Structure

```text
ttsaver/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── bot.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py
│   │   └── links.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── downloader.py
│   │   ├── media.py
│   │   ├── cache.py
│   │   ├── rate_limit.py
│   │   └── auth.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   └── models.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   ├── urls.py
│   │   └── cleanup.py
│   └── texts.py
├── data/
│   ├── .gitkeep
│   └── temp/
│       └── .gitkeep
├── tests/
│   ├── test_urls.py
│   ├── test_auth.py
│   ├── test_rate_limit.py
│   └── test_cache.py
├── .env.example
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

## 7. Core Modules

### `config.py`

Responsibilities:

- load environment variables
- parse allowed users
- define temp directory path
- define max file size
- define cache TTL and rate limit settings

Suggested env vars:

```env
BOT_TOKEN=
ALLOWED_USER_IDS=12345,67890
ADMIN_USER_IDS=12345
TEMP_DIR=./data/temp
DB_PATH=./data/app.db
MAX_VIDEO_SIZE_MB=50
CACHE_TTL_HOURS=72
REQUESTS_PER_USER_PER_DAY=20
LOG_LEVEL=INFO
```

### `handlers/commands.py`

Commands:

- `/start`
- `/help`
- `/stats` for admin only

### `handlers/links.py`

Responsibilities:

- extract URL from incoming message
- validate URL
- reject unsupported domains
- coordinate download/send flow

### `services/auth.py`

Responsibilities:

- whitelist checks
- admin checks

### `services/rate_limit.py`

Responsibilities:

- count requests per user per rolling day or calendar day
- reject if limit exceeded

For MVP, storing counters in SQLite is enough.

### `services/cache.py`

Responsibilities:

- normalize URL
- find cached record by normalized URL
- return Telegram `file_id` if not expired
- save new cache records after successful send

### `services/downloader.py`

Responsibilities:

- call `yt-dlp`
- download best available mp4-compatible version
- return local file path and metadata
- map downloader failures to user-friendly errors

Design notes:

- prefer stable output template by request ID
- disable playlist behavior
- set reasonable timeouts
- clean up partial files on failure

### `services/media.py`

Responsibilities:

- inspect media file
- detect size
- optionally remux/compress via `ffmpeg`
- prepare final file for Telegram send

Compression strategy for MVP:

1. If file <= limit, send as is
2. If file > limit and not extremely large, attempt one compression pass
3. If still > limit, return a "too large" error

### `storage/db.py`

Responsibilities:

- SQLite connection setup
- migrations/init SQL
- transaction helpers

## 8. SQLite Schema

Minimal schema:

```sql
CREATE TABLE IF NOT EXISTS media_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_url TEXT NOT NULL UNIQUE,
    source_platform TEXT NOT NULL,
    telegram_file_id TEXT NOT NULL,
    file_size_bytes INTEGER,
    original_url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS request_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    original_url TEXT,
    normalized_url TEXT,
    status TEXT NOT NULL,
    error_code TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_rate_limit (
    user_id INTEGER NOT NULL,
    day_bucket TEXT NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day_bucket)
);
```

Notes:

- `media_cache` avoids repeat downloads
- `request_log` helps debugging
- `user_rate_limit` is enough for small private usage

## 9. URL Handling Rules

Supported patterns:

- TikTok full links
- TikTok short links
- Instagram Reel links

Validation rules:

- accept only HTTP/HTTPS
- reject unknown domains
- strip tracking query params when normalizing
- normalize mobile and desktop variants where possible

Examples of normalization:

- remove `utm_*`
- remove trailing slash differences
- resolve obvious redirect wrappers if link format is known

## 10. User Flow

### Successful Flow

1. User sends link
2. Bot verifies user is allowed
3. Bot verifies rate limit
4. Bot sends "processing" message
5. Bot checks cache
6. If cached:
   - send by `file_id`
7. If not cached:
   - download video
   - validate size
   - optionally compress
   - send video
   - save `file_id`
8. Bot removes temp files

### Error Flows

Return clear messages for:

- unsupported link
- user not allowed
- rate limit exceeded
- video unavailable
- private or restricted post
- download failed
- file too large for bot
- temporary internal error

## 11. Telegram Message Design

### `/start`

Short explanation:

- what links are supported
- that only approved users can use the bot
- that large videos may fail

### `/help`

Example input:

- send a TikTok link
- send an Instagram Reel link

### Processing message

Example:

- `Downloading video, please wait...`

### File too large

Example:

- `This video is too large for the current bot limit. Try another link.`

## 12. Downloader Implementation Notes

Recommended `yt-dlp` approach:

- use Python API or subprocess wrapper
- prefer explicit output format and destination directory
- log extractor errors

Suggested behavior:

- disable playlists
- fetch a single item only
- prefer mp4 output if possible
- keep implementation isolated so `yt-dlp` can be updated without touching handlers

Potential issue:

- Instagram and TikTok may change behavior over time, so updating `yt-dlp` should be part of maintenance

## 13. Temporary File Lifecycle

Rules:

- each request gets its own temp directory or unique file prefix
- delete files after successful send
- delete files after failure
- run periodic cleanup for old leftover files

Suggested cleanup:

- remove temp files older than 6-12 hours on startup
- optionally run cleanup after every N requests

## 14. Rate Limiting

For private usage, simple rules are enough:

- default limit: `20 requests/day/user`
- optional burst control: only one active download per user

Why:

- protects free host resources
- prevents accidental spam
- avoids simultaneous heavy downloads

## 15. Security and Abuse Prevention

Required:

- whitelist by Telegram `user_id`
- reject unsupported domains
- sanitize file paths
- never execute user input as shell
- enforce downloader and ffmpeg timeouts

Nice to have:

- mask sensitive values in logs
- admin notification on repeated failures

## 16. Local Development Plan

### Prerequisites

- Python 3.12+
- `ffmpeg`
- bot token from BotFather

### Local Setup

1. Create virtualenv
2. Install dependencies
3. Fill `.env`
4. Start bot with polling

Suggested commands:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

## 17. Dependency List

Initial `requirements.txt`:

```txt
aiogram
python-dotenv
yt-dlp
pydantic
pydantic-settings
pytest
```

Notes:

- `sqlite3` is built into Python
- `ffmpeg` should be installed on the host, not via pip

## 18. Deployment Plan

### Primary: Northflank Sandbox

Target model:

- one always-on service
- deploy from Git repository
- run bot with polling

Why polling:

- simpler than webhooks
- no public HTTPS endpoint required for MVP

Environment variables:

- `BOT_TOKEN`
- `ALLOWED_USER_IDS`
- `ADMIN_USER_IDS`
- `DB_PATH`
- `TEMP_DIR`
- `MAX_VIDEO_SIZE_MB`
- `REQUESTS_PER_USER_PER_DAY`
- `CACHE_TTL_HOURS`

Operational notes:

- ephemeral filesystem is acceptable if cache loss is not critical
- SQLite reset after redeploy is acceptable for MVP
- if host persistence is unavailable in free plan, the bot still works, only cache is weaker

### Fallback: Render Free

If using Render:

- deploy as a web service or worker depending on current platform options
- expect sleeping after inactivity on free tier
- first request after sleep may be slower

Render is less ideal for this bot because sleep behavior is annoying for chat UX.

## 19. Docker Plan

Minimal container should include:

- Python runtime
- app source code
- `ffmpeg`
- dependencies from `requirements.txt`

Container entrypoint:

```bash
python -m app.main
```

## 20. Logging and Observability

Minimum logs:

- startup config summary without secrets
- incoming request metadata
- cache hit / miss
- downloader success / failure
- compression attempted / skipped
- Telegram send success / failure

Admin stats should show:

- total requests
- success count
- failure count
- cache hit count
- most recent failures

## 21. Testing Plan

### Unit tests

- URL validation
- URL normalization
- whitelist logic
- rate limiting logic
- cache expiration logic

### Integration tests

Mock:

- Telegram send
- `yt-dlp` results
- ffmpeg result handling

### Manual tests

- valid TikTok link under limit
- valid Reel under limit
- invalid domain
- non-whitelisted user
- repeated same link uses cache
- oversized video returns expected error

## 22. Implementation Order

### Phase 1: Skeleton

- create project structure
- config loader
- bot startup
- `/start` and `/help`
- whitelist middleware/check

### Phase 2: URL and Cache

- URL parser and normalizer
- SQLite init
- cache service
- request logging

### Phase 3: Download Pipeline

- `yt-dlp` integration
- temp file handling
- Telegram send
- save `file_id`

### Phase 4: Robustness

- rate limiting
- better error mapping
- cleanup routine
- admin `/stats`

### Phase 5: Deployment

- Dockerfile
- `.env.example`
- README
- deploy to Northflank
- test with real accounts

## 23. Acceptance Criteria for MVP

MVP is complete if:

- allowed user can send a TikTok link and get video back
- allowed user can send an Instagram Reel link and get video back
- same link can be served again from Telegram `file_id` cache
- non-allowed user is rejected
- oversized file returns a clear error
- temp files are cleaned up
- app can run on a free host with no paid dependencies

## 24. Risks and Mitigations

### Risk: `yt-dlp` breakage after source changes

Mitigation:

- isolate downloader module
- keep dependency easy to update
- log extractor-specific failures

### Risk: file too large for Telegram bot limit

Mitigation:

- early size check
- one compression attempt
- clear user-facing error

### Risk: free hosting filesystem resets

Mitigation:

- design cache as optional optimization
- do not depend on stored files
- treat SQLite persistence as nice-to-have, not required

### Risk: CPU or memory spikes during compression

Mitigation:

- only one heavy task at a time
- add per-user active-task guard
- skip compression for obviously too-large files

## 25. Recommended First Deliverable

The first coding iteration should produce:

- working bot skeleton
- env-based config
- whitelist
- TikTok and Reel URL validation
- SQLite cache layer
- downloader integration
- send video if under 50 MB
- clear errors otherwise

This is the shortest path to a usable private bot.
