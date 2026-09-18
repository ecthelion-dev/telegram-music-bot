import base64
import binascii
import logging
from functools import cache

from config import TEMP_DIR, YTDLP_COOKIES_B64, YTDLP_COOKIES_FILE

logger = logging.getLogger(__name__)

COOKIE_FILE_MODE = 0o600


@cache
def resolve_cookies_file() -> str:
    """
    Path to the cookie jar for yt-dlp, or "" when none is configured.

    A host that offers secret files can point YTDLP_COOKIES_FILE straight at one.
    YTDLP_COOKIES_B64 covers hosts that only offer env vars: the jar is decoded to
    disk once, keeping the secret out of this public repository either way.
    """
    if not YTDLP_COOKIES_B64:
        return YTDLP_COOKIES_FILE

    try:
        jar = base64.b64decode(YTDLP_COOKIES_B64, validate=True).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError) as e:
        logger.error(
            "YTDLP_COOKIES_B64 is not valid base64-encoded UTF-8 (%s); "
            "falling back to YTDLP_COOKIES_FILE", e,
        )
        return YTDLP_COOKIES_FILE

    path = TEMP_DIR / "cookies.txt"
    path.write_text(jar, encoding="utf-8")
    path.chmod(COOKIE_FILE_MODE)
    logger.info("Cookie jar decoded to %s (%d bytes)", path, len(jar))
    return str(path)
