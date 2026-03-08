from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
TIKTOK_HOSTS = {"tiktok.com", "www.tiktok.com", "m.tiktok.com", "vt.tiktok.com", "vm.tiktok.com"}
INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}


class UrlValidationError(ValueError):
    """Raised when a URL is unsupported."""


class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


@dataclass(frozen=True)
class ParsedMediaUrl:
    original_url: str
    normalized_url: str
    platform: Platform


def extract_first_url(text: str) -> str | None:
    match = URL_RE.search(text)
    return match.group(0).rstrip(").,!?]") if match else None


def parse_media_url(url: str) -> ParsedMediaUrl:
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UrlValidationError("Only HTTP/HTTPS URLs are supported")

    host = parsed.netloc.lower()
    path = _normalize_path(parsed.path)

    if host in TIKTOK_HOSTS:
        normalized = _normalize_tiktok(host, path)
        return ParsedMediaUrl(original_url=url, normalized_url=normalized, platform=Platform.TIKTOK)

    if host in INSTAGRAM_HOSTS:
        normalized = _normalize_instagram(path)
        return ParsedMediaUrl(original_url=url, normalized_url=normalized, platform=Platform.INSTAGRAM)

    raise UrlValidationError("Unsupported domain")


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    cleaned = re.sub(r"/+", "/", path.strip())
    return cleaned if cleaned.startswith("/") else f"/{cleaned}"


def _normalize_tiktok(host: str, path: str) -> str:
    trimmed = path.rstrip("/") or "/"
    if host in {"vt.tiktok.com", "vm.tiktok.com"}:
        if trimmed == "/":
            raise UrlValidationError("Unsupported TikTok short link")
        return f"https://{host}{trimmed}/"

    if not re.match(r"^/@[^/]+/video/\d+$", trimmed):
        raise UrlValidationError("Unsupported TikTok URL format")
    return f"https://tiktok.com{trimmed}"


def _normalize_instagram(path: str) -> str:
    trimmed = path.rstrip("/")
    match = re.match(r"^/(?:reel|reels)/([A-Za-z0-9._-]+)$", trimmed)
    if not match:
        raise UrlValidationError("Unsupported Instagram Reel URL format")
    reel_id = match.group(1)
    return f"https://instagram.com/reel/{reel_id}"
