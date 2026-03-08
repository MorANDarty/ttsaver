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
    "/stats - admin statistics"
)

NOT_ALLOWED_TEXT = "You are not allowed to use this bot."
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
