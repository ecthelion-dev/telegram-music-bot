import logging
from shazamio import Shazam

logger = logging.getLogger(__name__)

# Singleton instance of Shazam
_shazam_client: Shazam | None = None

def get_shazam_client() -> Shazam:
    global _shazam_client
    if _shazam_client is None:
        _shazam_client = Shazam()
    return _shazam_client

async def recognize_audio_file(file_path: str) -> dict | None:
    """
    Recognize a track from an audio or voice file using Shazamio.
    
    Returns:
        dict with keys: 'title', 'artist', 'cover_url', 'query'
        or None if not recognized.
    """
    try:
        client = get_shazam_client()
        result = await client.recognize(file_path)
        
        track = result.get("track")
        if not track:
            logger.info("Shazam: No match found for file %s", file_path)
            return None
        
        title = track.get("title", "").strip()
        artist = track.get("subtitle", "").strip()
        
        images = track.get("images", {})
        cover_url = images.get("coverart") or images.get("background")
        
        query = f"{artist} - {title}".strip(" -")
        
        return {
            "title": title,
            "artist": artist,
            "cover_url": cover_url,
            "query": query,
            "raw": track
        }
    except Exception as e:
        logger.error("Error recognizing audio with Shazam: %s", e, exc_info=True)
        return None
