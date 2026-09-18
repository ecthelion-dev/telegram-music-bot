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
