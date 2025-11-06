import sqlite3
import threading
import time
from pathlib import Path

_DB_PATH = Path("storage") / "credits.sqlite3"
_LOCK = threading.RLock()


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


_CONN = _connect()


def init_db() -> None:
    with _LOCK, _CONN:
        _CONN.execute(
            """
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            credits INTEGER NOT NULL DEFAULT 0,
            welcomed INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        );"""
        )
        _CONN.execute(
            """
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,                -- 'bonus'|'spend'|'purchase'|'adjust'
            amount INTEGER NOT NULL,           -- + / - в кредитах
            meta TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );"""
        )
        _CONN.execute(
            """
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,            -- 'yookassa'
            provider_id TEXT NOT NULL UNIQUE,  -- payment_id
            user_id INTEGER NOT NULL,
            credits INTEGER NOT NULL,
            amount INTEGER NOT NULL,           -- в минорных единицах (копейки)
            currency TEXT NOT NULL,
            status TEXT NOT NULL,              -- 'new'|'succeeded'|'applied'|'canceled'
            created_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );"""
        )


def ensure_user(user_id: int, welcome_credits: int = 0) -> tuple[bool, int]:
    """Возвращает (is_new, current_credits). Начисляет welcome один раз."""
    now = int(time.time())
    with _LOCK, _CONN:
        cur = _CONN.execute("SELECT credits, welcomed FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if row is None:
            _CONN.execute(
                "INSERT INTO users(user_id, credits, welcomed, created_at) VALUES(?,?,?,?)",
                (user_id, 0, 0, now),
            )
            is_new = True
            credits = 0
        else:
            credits, welcomed = row
            is_new = False

        if is_new and welcome_credits > 0:
            _CONN.execute(
                "UPDATE users SET credits=?, welcomed=1 WHERE user_id=?", (welcome_credits, user_id)
            )
            _CONN.execute(
                "INSERT INTO transactions(user_id, type, amount, meta, created_at) VALUES(?,?,?,?,?)",
                (user_id, "bonus", welcome_credits, "welcome", now),
            )
            credits = welcome_credits
    return is_new, credits


def get_balance(user_id: int) -> int:
    with _LOCK, _CONN:
        cur = _CONN.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return int(row[0]) if row else 0


def add_credits(user_id: int, amount: int, reason: str) -> None:
    now = int(time.time())
    if amount <= 0:
        return
    with _LOCK, _CONN:
        _CONN.execute(
            "UPDATE users SET credits=COALESCE(credits,0)+? WHERE user_id=?", (amount, user_id)
        )
        _CONN.execute(
            "INSERT INTO transactions(user_id, type, amount, meta, created_at) VALUES(?,?,?,?,?)",
            (user_id, "purchase", amount, reason, now),
        )


def spend_credits(user_id: int, amount: int) -> bool:
    if amount <= 0:
        return True
    with _LOCK, _CONN:
        cur = _CONN.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        have = int(row[0]) if row else 0
        if have < amount:
            return False
        _CONN.execute("UPDATE users SET credits=credits-? WHERE user_id=?", (amount, user_id))
        _CONN.execute(
            "INSERT INTO transactions(user_id, type, amount, meta, created_at) VALUES(?,?,?,?,?)",
            (user_id, "spend", -amount, "image", int(time.time())),
        )
    return True


def register_payment(
    provider_id: str, user_id: int, credits: int, amount_minor: int, currency: str
) -> None:
    with _LOCK, _CONN:
        _CONN.execute(
            """INSERT OR IGNORE INTO payments(provider, provider_id, user_id, credits, amount, currency, status, created_at)
                         VALUES('yookassa',?,?,?,?,?,'new',?)""",
            (provider_id, user_id, credits, amount_minor, currency, int(time.time())),
        )


def set_payment_status(provider_id: str, status: str) -> None:
    with _LOCK, _CONN:
        _CONN.execute("UPDATE payments SET status=? WHERE provider_id=?", (status, provider_id))


def mark_payment_applied(provider_id: str) -> tuple[int, int] | None:
    """Возвращает (user_id, credits) если переведён в applied, иначе None."""
    with _LOCK, _CONN:
        cur = _CONN.execute(
            "SELECT user_id, credits, status FROM payments WHERE provider_id=?", (provider_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        user_id, credits, status = row
        if status == "applied":
            return None
        _CONN.execute("UPDATE payments SET status='applied' WHERE provider_id=?", (provider_id,))
        return (user_id, credits)
