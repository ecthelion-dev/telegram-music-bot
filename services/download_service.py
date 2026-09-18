import asyncio
import logging
from pathlib import Path

import yt_dlp
from config import DOWNLOAD_DIR, MAX_DURATION_SECONDS, POT_PROVIDER_HOME, YTDLP_PROXY
from services.cookies import resolve_cookies_file

logger = logging.getLogger(__name__)

# Several candidates per source: SoundCloud mixes DRM-locked uploads in with
# playable ones, and a DRM hit should cost a retry rather than the whole search.
SEARCH_CANDIDATE_COUNT = 6

# YouTube first: it has the deeper catalogue and works from a clean IP. SoundCloud
# stays as a fallback, though it is unreachable from Uzbekistan, so it only ever
# helps a deployment hosted elsewhere.
SEARCH_PREFIXES = ("ytsearch", "scsearch")

# Ordered by preference, since the postprocessor's output extension varies.
AUDIO_EXTENSIONS = (".m4a", ".mp3", ".opus", ".ogg", ".webm", ".mp4")

_BOT_CHECK_MARKERS = ("sign in to confirm", "not a bot", "confirm your age")
_DRM_MARKERS = ("drm protected", "drm-protected")
_UNAVAILABLE_MARKERS = (
    "unavailable",
    "private video",
    "removed by the uploader",
    "members-only",
    "does not exist",
)


def base_ydl_opts() -> dict:
    """
    yt-dlp options shared by search and direct-URL downloads.

    Deliberately does not pin `player_client`: overriding it strips the modern
    audio-only formats and leaves only legacy format 18, which YouTube blocks
    first on datacenter IPs.
    """
    opts = {
        # Prefer the AAC stream YouTube already serves: re-encoding it to MP3 cost
        # ~4.6s a track on this host, whose emulated CPU has no SSE4.2 or AVX for
        # ffmpeg to use. Matching the source codec lets the postprocessor remux
        # rather than re-encode, and it only really encodes on the rare fallback.
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
        }],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }
    cookies_file = resolve_cookies_file()
    if cookies_file:
        opts = {**opts, "cookiefile": cookies_file}
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
    if any(marker in lowered for marker in _DRM_MARKERS):
        return {"error": "drm", "detail": message}
    if any(marker in lowered for marker in _UNAVAILABLE_MARKERS):
        return {"error": "unavailable", "detail": message}
    return {"error": "download_failed", "detail": message}


def _find_audio_file(track_id: str) -> Path | None:
    """Locate the file yt-dlp produced; its extension depends on the chosen source."""
    for extension in AUDIO_EXTENSIONS:
        candidate = DOWNLOAD_DIR / f"{track_id}{extension}"
        if candidate.exists():
            return candidate
    return None


def _build_track(entry: dict, fallback_title: str = "", source_url: str = "") -> dict | None:
    """Map a finished yt-dlp entry onto a track dict, or None if no audio was produced."""
    audio_path = _find_audio_file(str(entry.get("id")))
    if not audio_path:
        return None

    return {
        "title": entry.get("title") or fallback_title or "Audio trek",
        "artist": entry.get("uploader") or entry.get("creator") or entry.get("channel") or "",
        "duration": entry.get("duration") or 0,
        "file_path": str(audio_path),
        "thumbnail": entry.get("thumbnail"),
        "webpage_url": entry.get("webpage_url") or source_url,
    }


def _search_one_source(prefix: str, query: str) -> dict:
    """
    Search a single catalogue and download its first usable hit.

    The listing is flat and the hits are resolved one at a time: resolving the whole
    candidate list up front costs a round trip per hit, and all but the first are
    normally thrown away.
    """
    try:
        list_opts = {**base_ydl_opts(), "extract_flat": "in_playlist"}
        with yt_dlp.YoutubeDL(list_opts) as ydl:
            info = ydl.extract_info(
                f"{prefix}{SEARCH_CANDIDATE_COUNT}:{query}", download=False
            )

        entries = [entry for entry in (info or {}).get("entries") or [] if entry]
        if not entries:
            return {"error": "not_found", "detail": "natija yo‘q"}

        candidates = [
            entry for entry in entries
            if (entry.get("duration") or 0) <= MAX_DURATION_SECONDS
        ]
        if not candidates:
            return {
                "error": "too_long",
                "detail": f"{len(entries)} ta natija {MAX_DURATION_SECONDS}s dan uzun",
            }

        last_detail = ""
        with yt_dlp.YoutubeDL(base_ydl_opts()) as ydl:
            for entry in candidates:
                url = entry.get("url") or entry.get("webpage_url")
                if not url:
                    continue
                try:
                    resolved = ydl.extract_info(url, download=True)
                except Exception as dl_err:
                    last_detail = str(dl_err)
                    logger.warning("%s candidate %s failed: %s", prefix, entry.get("id"), dl_err)
                    continue

                track = _build_track(resolved or {}, fallback_title=query)
                if track:
                    return track
                last_detail = f"No MP3 produced for {entry.get('id')}"

        return {
            "error": "download_failed",
            "detail": last_detail or "hech biri yuklanmadi",
        }
    except Exception as e:
        logger.error("%s search failed for %r: %s", prefix, query, e, exc_info=True)
        return _classify_error(e)


def _sync_search_and_download(query: str) -> dict:
    """Try each catalogue in turn and return the first track that downloads."""
    failures = []
    for prefix in SEARCH_PREFIXES:
        result = _search_one_source(prefix, query)
        if not result.get("error"):
            return result
        failures.append(result)

    details = " | ".join(f"{p}: {f['detail']}" for p, f in zip(SEARCH_PREFIXES, failures))
    # A real failure is more actionable than "not found", which every source reports
    # when it simply lacks the track.
    blocking = [f for f in failures if f["error"] != "not_found"]
    chosen = blocking[0] if blocking else failures[-1]
    return {**chosen, "detail": details}


def _sync_download_url(url: str) -> dict:
    """Download audio straight from a link (YouTube, Instagram, TikTok). Runs in a worker thread."""
    try:
        with yt_dlp.YoutubeDL(base_ydl_opts()) as ydl:
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
