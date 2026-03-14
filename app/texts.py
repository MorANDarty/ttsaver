from __future__ import annotations

START_TEXT = (
    "Send a public TikTok link or Instagram Reel link and I will return the video.\n\n"
    "Access is limited to approved Telegram users.\n"
    "Very large videos may fail if they cannot be kept under the bot upload limit."
)

HELP_TEXT = (
    "Supported links:\n"
    "- Public TikTok videos\n"
    "- Public Instagram Reels\n\n"
    "Examples:\n"
    "- https://www.tiktok.com/@user/video/1234567890\n"
    "- https://www.instagram.com/reel/ABC123xyz/\n\n"
    "Commands:\n"
    "/start - bot description\n"
    "/help - usage help\n"
    "/req_permission - request access\n"
    "/stats - admin statistics"
)

NOT_ALLOWED_TEXT = "You are not allowed to use this bot. Send /req_permission to request access."
PRIVATE_CHAT_ONLY_TEXT = "Use this bot in a direct message only."
NO_URL_TEXT = "Send a public TikTok or Instagram Reel link."
UNSUPPORTED_URL_TEXT = "Unsupported link. Only public TikTok links and Instagram Reels are supported."
PROCESSING_TEXT = "Downloading video, please wait..."
RATE_LIMIT_TEXT = "Daily request limit reached. Try again tomorrow."
ACTIVE_REQUEST_TEXT = "One download is already running for your account. Wait for it to finish."
VIDEO_UNAVAILABLE_TEXT = "The video is unavailable, private, or restricted."
DOWNLOAD_FAILED_TEXT = "Failed to download the video. Try again later."
TOO_LARGE_TEXT = "This video is too large for the current bot limit and could not be compressed safely."
INTERNAL_ERROR_TEXT = "Temporary internal error. Try again later."
REQUEST_ACCESS_PROMPT_TEXT = "Access is not granted yet. Send /req_permission to request access."
ACCESS_REQUEST_PROMPT_TEXT = REQUEST_ACCESS_PROMPT_TEXT
ACCESS_REQUEST_CREATED_TEXT = "Your access request has been sent to the administrators."
ACCESS_ALREADY_GRANTED_TEXT = "Access is already granted. You can use the bot."
ACCESS_REQUEST_PENDING_TEXT = "Your access request is already pending administrator review."
ACCESS_REQUEST_REJECTED_TEXT = "Your previous access request was rejected. Send /req_permission later to try again."
ACCESS_REQUESTS_UNAVAILABLE_TEXT = "Access requests are temporarily unavailable. Try again later."
ACCESS_GRANTED_TEXT = "Access has been granted. You can now use the bot."
ACCESS_REJECTED_TEXT = "Your access request was rejected by an administrator."
ADMIN_ONLY_ACTION_TEXT = "Only administrators can process access requests."
STALE_ACCESS_REQUEST_TEXT = "This access request no longer exists."
ACCESS_REQUEST_ALREADY_PROCESSED_TEXT = "This access request has already been processed."
ACCESS_APPROVED_BY_ADMIN_TEXT = "Access granted."
ACCESS_REJECTED_BY_ADMIN_TEXT = "Access rejected."


def build_access_request_cooldown_text(retry_after_seconds: int | None) -> str:
    if not retry_after_seconds or retry_after_seconds <= 0:
        return ACCESS_REQUEST_REJECTED_TEXT

    hours, remainder = divmod(retry_after_seconds, 3600)
    minutes = remainder // 60
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append("less than a minute")
    wait_time = " ".join(parts)
    return f"Your previous access request was rejected. Try again in {wait_time}."
