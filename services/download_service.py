import asyncio
import logging
import yt_dlp
from config import (
    DOWNLOAD_DIR,
    MAX_DURATION_SECONDS,
    POT_PROVIDER_HOME,
    YTDLP_COOKIES_FILE,
    YTDLP_PROXY,
)

logger = logging.getLogger(__name__)

SEARCH_CANDIDATE_COUNT = 3

_BOT_CHECK_MARKERS = ("sign in to confirm", "not a bot", "confirm your age")
_UNAVAILABLE_MARKERS = (
    "unavailable",
    "private video",
    "removed by the uploader",
    "members-only",
    "does not exist",
)


def _base_ydl_opts() -> dict:
    """
    yt-dlp options shared by search and direct-URL downloads.

    Deliberately does not pin `player_client`: overriding it strips the modern
    audio-only formats and leaves only legacy format 18, which YouTube blocks
    first on datacenter IPs.
    """
    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    if YTDLP_COOKIES_FILE:
        opts = {**opts, "cookiefile": YTDLP_COOKIES_FILE}
    if YTDLP_PROXY:
        opts = {**opts, "proxy": YTDLP_PROXY}
    if POT_PROVIDER_HOME:
        opts = {**opts, "extractor_args": {
            "youtubepot-bgutilscript": {"server_home": [POT_PROVIDER_HOME]},
        }}
    return opts


def _classify_error(exc: Exception) -> dict:
    message = str(exc)
    lowered = message.lower()
    if any(marker in lowered for marker in _BOT_CHECK_MARKERS):
        return {"error": "bot_check", "detail": message}
    if any(marker in lowered for marker in _UNAVAILABLE_MARKERS):
        return {"error": "unavailable", "detail": message}
    return {"error": "download_failed", "detail": message}


def _build_track(entry: dict, fallback_title: str = "", source_url: str = "") -> dict | None:
    """Map a finished yt-dlp entry onto a track dict, or None if no MP3 was produced."""
    mp3_path = DOWNLOAD_DIR / f"{entry.get('id')}.mp3"
    if not mp3_path.exists():
        return None

    return {
        "title": entry.get("title") or fallback_title or "Audio trek",
        "artist": entry.get("uploader") or entry.get("creator") or entry.get("channel") or "",
        "duration": entry.get("duration") or 0,
        "file_path": str(mp3_path),
        "thumbnail": entry.get("thumbnail"),
        "webpage_url": entry.get("webpage_url") or source_url,
    }


def _sync_search_and_download(query: str) -> dict:
    """Search YouTube and download the first usable match. Runs in a worker thread."""
    try:
        with yt_dlp.YoutubeDL(_base_ydl_opts()) as ydl:
            info = ydl.extract_info(
                f"ytsearch{SEARCH_CANDIDATE_COUNT}:{query}", download=False
            )
            entries = [entry for entry in (info or {}).get("entries") or [] if entry]
            if not entries:
                return {"error": "not_found", "detail": f"No search results for {query!r}"}

            candidates = [
                entry for entry in entries
                if (entry.get("duration") or 0) <= MAX_DURATION_SECONDS
            ]
            if not candidates:
                return {
                    "error": "too_long",
                    "detail": f"All {len(entries)} candidates exceed {MAX_DURATION_SECONDS}s",
                }

            last_detail = ""
            for entry in candidates:
                try:
                    ydl.process_ie_result(entry, download=True)
                except Exception as dl_err:
                    last_detail = str(dl_err)
                    logger.warning("Candidate %s failed: %s", entry.get("id"), dl_err)
                    continue

                track = _build_track(entry, fallback_title=query)
                if track:
                    return track
                last_detail = f"No MP3 produced for {entry.get('id')}"

            return {
                "error": "download_failed",
                "detail": last_detail or "No candidate could be downloaded",
            }
    except Exception as e:
        logger.error("yt-dlp search failed for %r: %s", query, e, exc_info=True)
        return _classify_error(e)


def _sync_download_url(url: str) -> dict:
    """Download audio straight from a link (YouTube, Instagram, TikTok). Runs in a worker thread."""
    try:
        with yt_dlp.YoutubeDL(_base_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return {"error": "download_failed", "detail": "yt-dlp returned no metadata"}

            entries = [entry for entry in info.get("entries") or [] if entry]
            entry = entries[0] if entries else info

            track = _build_track(entry, source_url=url)
            if not track:
                return {
                    "error": "download_failed",
                    "detail": f"No MP3 produced for {entry.get('id')}",
                }
            return track
    except Exception as e:
        logger.error("yt-dlp URL download failed for %s: %s", url, e, exc_info=True)
        return _classify_error(e)


async def download_track_by_query(query: str) -> dict:
    """Search and download a track as MP3. Returns a track dict or an error dict."""
    return await asyncio.to_thread(_sync_search_and_download, query)


async def download_social_media_audio(url: str) -> dict:
    """Download audio from a direct link. Returns a track dict or an error dict."""
    return await asyncio.to_thread(_sync_download_url, url)
