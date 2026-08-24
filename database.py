import aiosqlite
from datetime import datetime, timezone

DB_PATH = "security.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS members (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                account_created_at TEXT,
                first_join_at TEXT,
                last_join_at TEXT,
                leave_count INTEGER DEFAULT 0,
                invite_code TEXT,
                inviter_id INTEGER,
                risk_score INTEGER DEFAULT 0,
                risk_level TEXT DEFAULT 'low',
                status TEXT DEFAULT 'pending',
                is_valid_invite INTEGER DEFAULT 0,
                notes TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                code TEXT PRIMARY KEY,
                inviter_id INTEGER,
                uses INTEGER DEFAULT 0,
                max_uses INTEGER,
                temporary INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS invite_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invite_code TEXT,
                inviter_id INTEGER,
                user_id INTEGER,
                joined_at TEXT,
                left_at TEXT,
                is_valid INTEGER DEFAULT 0,
                risk_score INTEGER,
                status TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id INTEGER,
                details TEXT,
                created_at TEXT
            )
        """)
        await db.commit()


async def log_event(event_type: str, user_id: int, details: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (event_type, user_id, details, created_at) VALUES (?, ?, ?, ?)",
            (event_type, user_id, details, datetime.now(timezone.utc).isoformat())
        )
        await db.commit()
