import asyncio
import html
import importlib.util
import shutil
import subprocess
from pathlib import Path

import yt_dlp

from config import POT_PROVIDER_HOME, YTDLP_PROXY
from services.cookies import resolve_cookies_file
from services.download_service import SEARCH_PREFIXES, base_ydl_opts

# A search, not a fixed video id: it exercises the same path the bot uses and
# cannot start failing because one particular upload got taken down.
PROBE_QUERY = "music"
SOURCE_LABELS = {"scsearch": "SoundCloud", "ytsearch": "YouTube"}
POT_PLUGIN_MODULE = "yt_dlp_plugins.extractor.getpot_bgutil_script"
NODE_TIMEOUT_SECONDS = 10
ERROR_EXCERPT_LIMIT = 300
PROBE_RESULT_LIMIT = 5
DRM_MARKERS = ("drm protected", "drm-protected")


def _node_version() -> str:
    node = shutil.which("node")
    if not node:
        return "❌ o‘rnatilmagan"
    try:
        result = subprocess.run(
            [node, "--version"],
            capture_output=True,
            text=True,
            timeout=NODE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return f"⚠️ {e}"
    return result.stdout.strip() or "⚠️ noma’lum"


def _cookies_status() -> str:
    path = resolve_cookies_file()
    if not path:
        return "➖ yo‘q"

    jar = Path(path)
    if not jar.is_file():
        return f"❌ fayl topilmadi ({path})"

    try:
        lines = jar.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return f"⚠️ o‘qib bo‘lmadi: {e}"

    entries = [line for line in lines if line.strip() and not line.startswith("#")]
    youtube_entries = [line for line in entries if "youtube.com" in line]
    if not youtube_entries:
        return f"⚠️ {len(entries)} ta yozuv, lekin youtube.com uchun yo‘q"
    return f"✅ {len(youtube_entries)} ta youtube.com cookie"


def _pot_provider_status() -> str:
    if not POT_PROVIDER_HOME:
        return "➖ o‘chiq (POT_PROVIDER_HOME bo‘sh)"
    if importlib.util.find_spec(POT_PLUGIN_MODULE) is None:
        return "❌ pip plagini o‘rnatilmagan"
    return f"✅ yoqilgan ({POT_PROVIDER_HOME})"


def _probe_source(prefix: str) -> str:
    opts = {**base_ydl_opts(), "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"{prefix}1:{PROBE_QUERY}", download=False)
    except Exception as e:
        return f"❌ {html.escape(str(e)[:ERROR_EXCERPT_LIMIT])}"

    entries = [entry for entry in (info or {}).get("entries") or [] if entry]
    if not entries:
        return "⚠️ qidiruv natija bermadi"

    audio_formats = [
        fmt for fmt in entries[0].get("formats", [])
        if fmt.get("acodec") not in (None, "none")
    ]
    return f"✅ {len(audio_formats)} ta audio format"


def _source_health() -> str:
    return "\n".join(
        f"<b>{SOURCE_LABELS.get(prefix, prefix)}:</b> {_probe_source(prefix)}"
        for prefix in SEARCH_PREFIXES
    )


def _collect() -> str:
    return "\n".join([
        "🔬 <b>Diagnostika</b>",
        "",
        f"<b>yt-dlp:</b> {yt_dlp.version.__version__}",
        f"<b>Node.js:</b> {_node_version()}",
        f"<b>FFmpeg:</b> {'✅ bor' if shutil.which('ffmpeg') else '❌ yo‘q'}",
        "",
        f"<b>PO token:</b> {_pot_provider_status()}",
        f"<b>Cookies:</b> {_cookies_status()}",
        f"<b>Proxy:</b> {'✅ sozlangan' if YTDLP_PROXY else '➖ yo‘q'}",
        "",
        "<b>Manbalar (tartib bo‘yicha):</b>",
        _source_health(),
    ])


async def collect_diagnostics() -> str:
    """Report what this deployment actually has, so remote debugging is not guesswork."""
    return await asyncio.to_thread(_collect)


def _entry_status(ydl: yt_dlp.YoutubeDL, entry: dict) -> str:
    """Whether this hit could actually be downloaded, not merely that it is listed."""
    url = entry.get("url") or entry.get("webpage_url")
    if not url:
        return "❔"
    try:
        info = ydl.extract_info(url, download=False)
    except Exception as e:
        lowered = str(e).lower()
        return "🔒" if any(marker in lowered for marker in DRM_MARKERS) else "❌"

    audio_formats = [
        fmt for fmt in (info or {}).get("formats", [])
        if fmt.get("acodec") not in (None, "none")
    ]
    return "✅" if audio_formats else "❌"


def _search_probe(prefix: str, query: str) -> str:
    list_opts = {**base_ydl_opts(), "skip_download": True, "extract_flat": "in_playlist"}
    try:
        with yt_dlp.YoutubeDL(list_opts) as ydl:
            info = ydl.extract_info(f"{prefix}{PROBE_RESULT_LIMIT}:{query}", download=False)
    except Exception as e:
        return f"❌ {html.escape(str(e)[:ERROR_EXCERPT_LIMIT])}"

    entries = [entry for entry in (info or {}).get("entries") or [] if entry]
    if not entries:
        return "➖ natija yo‘q"

    check_opts = {**base_ydl_opts(), "skip_download": True}
    with yt_dlp.YoutubeDL(check_opts) as ydl:
        return "\n".join(
            f"{_entry_status(ydl, entry)} "
            f"{html.escape((entry.get('uploader') or entry.get('channel') or '?')[:20])}"
            f" — {html.escape((entry.get('title') or '?')[:45])}"
            for entry in entries
        )


def _probe(query: str) -> str:
    return "\n".join([
        f"🔎 <b>{html.escape(query)}</b>",
        "",
        "<b>YouTube:</b>",
        _search_probe("ytsearch", query),
        "",
        "<b>SoundCloud:</b>",
        _search_probe("scsearch", query),
        "",
        "<i>✅ yuklanadi · 🔒 DRM · ❌ bloklangan</i>",
    ])


async def probe_sources(query: str) -> str:
    """Show what each catalogue holds for a query, to compare sources before switching."""
    return await asyncio.to_thread(_probe, query)
