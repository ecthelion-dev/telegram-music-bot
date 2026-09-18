import asyncio
import logging
from pathlib import Path
import yt_dlp
from config import DOWNLOAD_DIR, MAX_DURATION_SECONDS

logger = logging.getLogger(__name__)

def _sync_search_and_download(query: str) -> dict | None:
    """
    Synchronous function that uses yt-dlp to search and download the top audio match.
    Runs inside asyncio thread pool.
    """
    outtmpl = str(DOWNLOAD_DIR / "%(id)s.%(ext)s")
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "mweb"]
            }
        },
    }

    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Search YouTube for top 1 match
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if not info:
                return None
            
            entries = info.get("entries")
            if not entries:
                return None
            
            entry = entries[0]
            duration = entry.get("duration") or 0
            
            if duration > MAX_DURATION_SECONDS:
                logger.warning("Track too long (%s seconds): %s", duration, query)
                return {"error": "too_long", "duration": duration}
            
            # Now download
            ydl.process_ie_result(entry, download=True)
            
            # Expected MP3 path
            video_id = entry.get("id")
            final_mp3_path = DOWNLOAD_DIR / f"{video_id}.mp3"
            
            title = entry.get("title", query)
            artist = entry.get("uploader") or entry.get("channel") or ""
            
            return {
                "title": title,
                "artist": artist,
                "duration": duration,
                "file_path": str(final_mp3_path),
                "thumbnail": entry.get("thumbnail"),
                "webpage_url": entry.get("webpage_url")
            }
    except Exception as e:
        logger.error("Error in yt-dlp download: %s", e, exc_info=True)
        return None

async def download_track_by_query(query: str) -> dict | None:
    """
    Search and download a track as MP3 asynchronously using yt-dlp.
    """
    return await asyncio.to_thread(_sync_search_and_download, query)

def _sync_download_url(url: str) -> dict | None:
    """
    Download audio directly from a social media link (Instagram, TikTok, YouTube Shorts).
    """
    outtmpl = str(DOWNLOAD_DIR / "%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios", "mweb"]
            }
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None
            
            # If playlist/multi-item entry
            if "entries" in info:
                entry = info["entries"][0]
            else:
                entry = info

            video_id = entry.get("id")
            final_mp3_path = DOWNLOAD_DIR / f"{video_id}.mp3"
            
            title = entry.get("title") or "Audio Trek"
            artist = entry.get("uploader") or entry.get("creator") or entry.get("channel") or ""
            duration = entry.get("duration") or 0

            return {
                "title": title,
                "artist": artist,
                "duration": duration,
                "file_path": str(final_mp3_path),
                "thumbnail": entry.get("thumbnail"),
                "webpage_url": entry.get("webpage_url") or url
            }
    except Exception as e:
        logger.error("Error downloading social media audio: %s", e, exc_info=True)
        return None

async def download_social_media_audio(url: str) -> dict | None:
    """
    Asynchronously download audio from social media link.
    """
    return await asyncio.to_thread(_sync_download_url, url)

