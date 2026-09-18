import aiosqlite
from datetime import datetime
from config import DATABASE_PATH

async def init_db():
    """Initialize database tables for tracks caching and users."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_key TEXT UNIQUE,
                title TEXT,
                artist TEXT,
                telegram_file_id TEXT NOT NULL,
                duration INTEGER DEFAULT 0,
                download_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_or_update_user(user_id: int, username: str | None, first_name: str | None):
    """Add a new user or update details."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name))
        await db.commit()

async def get_cached_track(query_key: str) -> dict | None:
    """Retrieve cached track by query key."""
    normalized_key = query_key.strip().lower()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, query_key, title, artist, telegram_file_id, duration, download_count FROM tracks WHERE query_key = ?",
            (normalized_key,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                # Increment download count
                await db.execute(
                    "UPDATE tracks SET download_count = download_count + 1 WHERE id = ?",
                    (row["id"],)
                )
                await db.commit()
                return dict(row)
    return None

async def save_track(query_key: str, title: str, artist: str, telegram_file_id: str, duration: int = 0):
    """Save a newly uploaded track to cache."""
    normalized_key = query_key.strip().lower()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO tracks (query_key, title, artist, telegram_file_id, duration)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(query_key) DO UPDATE SET
                telegram_file_id = excluded.telegram_file_id,
                download_count = tracks.download_count + 1
        """, (normalized_key, title, artist, telegram_file_id, duration))
        await db.commit()

async def get_users_count() -> int:
    """Get total number of registered users."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_tracks_count() -> int:
    """Get total number of cached tracks."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM tracks") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_all_user_ids() -> list[int]:
    """Retrieve all user IDs for broadcasting."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_top_tracks(limit: int = 5) -> list[dict]:
    """Retrieve the most downloaded tracks."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT title, artist, download_count FROM tracks ORDER BY download_count DESC LIMIT ?",
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def search_cached_tracks(query: str, limit: int = 10) -> list[dict]:
    """Search tracks in the cache matching the query."""
    normalized_query = f"%{query.strip().lower()}%"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, title, artist, telegram_file_id, duration
            FROM tracks
            WHERE query_key LIKE ? OR title LIKE ? OR artist LIKE ?
            ORDER BY download_count DESC
            LIMIT ?
        """, (normalized_query, normalized_query, normalized_query, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

