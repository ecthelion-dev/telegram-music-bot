import asyncio
import html
import importlib.util
import shutil
import subprocess

import yt_dlp

from config import POT_PROVIDER_HOME, YTDLP_COOKIES_FILE, YTDLP_PROXY
from services.download_service import base_ydl_opts

# A search, not a fixed video id: it exercises the same path the bot uses and
# cannot start failing because one particular upload got taken down.
PROBE_QUERY = "ytsearch1:music"
POT_PLUGIN_MODULE = "yt_dlp_plugins.extractor.getpot_bgutil_script"
NODE_TIMEOUT_SECONDS = 10
ERROR_EXCERPT_LIMIT = 300


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


def _pot_provider_status() -> str:
    if not POT_PROVIDER_HOME:
        return "➖ o‘chiq (POT_PROVIDER_HOME bo‘sh)"
    if importlib.util.find_spec(POT_PLUGIN_MODULE) is None:
        return "❌ pip plagini o‘rnatilmagan"
    return f"✅ yoqilgan ({POT_PROVIDER_HOME})"


def _probe_youtube() -> str:
    opts = {**base_ydl_opts(), "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(PROBE_QUERY, download=False)
    except Exception as e:
        return f"❌ {html.escape(str(e)[:ERROR_EXCERPT_LIMIT])}"

    entries = [entry for entry in (info or {}).get("entries") or [] if entry]
    if not entries:
        return "⚠️ qidiruv natija bermadi"

    audio_formats = [
        fmt for fmt in entries[0].get("formats", [])
        if fmt.get("acodec") not in (None, "none")
    ]
    return f"✅ ishladi — {len(audio_formats)} ta audio format"


def _collect() -> str:
    return "\n".join([
        "🔬 <b>Diagnostika</b>",
        "",
        f"<b>yt-dlp:</b> {yt_dlp.version.__version__}",
        f"<b>Node.js:</b> {_node_version()}",
        f"<b>FFmpeg:</b> {'✅ bor' if shutil.which('ffmpeg') else '❌ yo‘q'}",
        "",
        f"<b>PO token:</b> {_pot_provider_status()}",
        f"<b>Cookies:</b> {'✅ sozlangan' if YTDLP_COOKIES_FILE else '➖ yo‘q'}",
        f"<b>Proxy:</b> {'✅ sozlangan' if YTDLP_PROXY else '➖ yo‘q'}",
        "",
        "<b>YouTube sinovi:</b>",
        _probe_youtube(),
    ])


async def collect_diagnostics() -> str:
    """Report what this deployment actually has, so remote debugging is not guesswork."""
    return await asyncio.to_thread(_collect)
