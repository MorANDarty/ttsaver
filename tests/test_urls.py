import pytest

from app.utils.urls import Platform, UrlValidationError, extract_first_url, parse_media_url


def test_extract_first_url() -> None:
    text = "check this https://www.instagram.com/reel/ABC123/?utm_source=test now"
    assert extract_first_url(text) == "https://www.instagram.com/reel/ABC123/?utm_source=test"


@pytest.mark.parametrize(
    ("url", "platform", "normalized"),
    [
        (
            "https://www.tiktok.com/@alice/video/1234567890?is_from_webapp=1",
            Platform.TIKTOK,
            "https://tiktok.com/@alice/video/1234567890",
        ),
        (
            "https://vt.tiktok.com/ZS123abc/",
            Platform.TIKTOK,
            "https://vt.tiktok.com/ZS123abc/",
        ),
        (
            "https://www.instagram.com/reels/CrABC123/?utm_source=ig_web_copy_link",
            Platform.INSTAGRAM,
            "https://instagram.com/reel/CrABC123",
        ),
    ],
)
def test_parse_media_url_normalizes_supported_urls(url: str, platform: Platform, normalized: str) -> None:
    parsed = parse_media_url(url)
    assert parsed.platform == platform
    assert parsed.normalized_url == normalized


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/video",
        "https://example.com/video",
        "https://www.instagram.com/p/ABC123/",
        "https://www.tiktok.com/@alice",
    ],
)
def test_parse_media_url_rejects_invalid_inputs(url: str) -> None:
    with pytest.raises(UrlValidationError):
        parse_media_url(url)
