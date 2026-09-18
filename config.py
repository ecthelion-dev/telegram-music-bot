import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Storage and Directories
DOWNLOAD_DIR = BASE_DIR / os.getenv("DOWNLOAD_DIR", "downloads")
TEMP_DIR = BASE_DIR / "temp"
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "bot_database.db")

# Ensure directories exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Admin IDs
raw_admins = os.getenv("ADMIN_IDS", "796239061")
ADMIN_IDS = [int(x.strip()) for x in raw_admins.split(",") if x.strip().isdigit()]

# Constraints
# Default 15 minutes limit for downloaded tracks
MAX_DURATION_SECONDS = int(os.getenv("MAX_DURATION_SECONDS", "900"))

# yt-dlp network options. YouTube blocks datacenter IPs far more aggressively than
# residential ones, so a cloud deployment may need cookies or an outbound proxy.
YTDLP_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "").strip()
YTDLP_PROXY = os.getenv("YTDLP_PROXY", "").strip()

# Base64 of a Netscape cookie jar, for hosts that offer env vars but not secret
# files. Base64 because the format is tab-separated and dashboards mangle tabs.
# The repository is public, so the jar itself must never be committed.
YTDLP_COOKIES_B64 = os.getenv("YTDLP_COOKIES_B64", "").strip()

# Checkout directory of bgutil-ytdlp-pot-provider, which mints the proof-of-origin
# token YouTube demands from datacenter IPs. The Dockerfile builds it and sets this.
POT_PROVIDER_HOME = os.getenv("POT_PROVIDER_HOME", "").strip()
