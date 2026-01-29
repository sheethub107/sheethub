# utils/db.py
import sqlite3
from datetime import datetime

DB_PATH = "sheethub.db"
DAILY_LIMIT = 5


# -----------------------------
# Connection helper
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


# -----------------------------
# Init DB (SAFE)
# -----------------------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Users table (WITH PLAN)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            plan TEXT DEFAULT 'free'
        )
    """)

    # Usage table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usage (
            user_id INTEGER,
            date TEXT,
            count INTEGER,
            PRIMARY KEY (user_id, date)
        )
    """)

    # File history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS file_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_name TEXT,
            rows INTEGER,
            columns INTEGER,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# User
# -----------------------------
def get_or_create_user(email: str) -> int:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = cur.fetchone()

    if row:
        user_id = row[0]
    else:
        cur.execute(
            "INSERT INTO users (email, plan) VALUES (?, 'free')",
            (email,),
        )
        conn.commit()
        user_id = cur.lastrowid

    conn.close()
    return user_id


def get_user_plan(user_id: int) -> str:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT plan FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()

    conn.close()
    return row[0] if row else "free"


def upgrade_to_pro(user_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET plan = 'pro' WHERE id = ?",
        (user_id,),
    )

    conn.commit()
    conn.close()


# -----------------------------
# Usage limits
# -----------------------------
def remaining_quota(user_id: int) -> int:
    # Pro users have unlimited usage
    if get_user_plan(user_id) == "pro":
        return 9999

    today = datetime.utcnow().date().isoformat()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT count FROM usage WHERE user_id = ? AND date = ?",
        (user_id, today),
    )
    row = cur.fetchone()
    conn.close()

    used = row[0] if row else 0
    return max(0, DAILY_LIMIT - used)


def can_use(user_id: int) -> bool:
    # Pro users bypass limit
    if get_user_plan(user_id) == "pro":
        return True
    return remaining_quota(user_id) > 0


def increment_usage(user_id: int):
    # Do not count usage for Pro users
    if get_user_plan(user_id) == "pro":
        return

    today = datetime.utcnow().date().isoformat()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO usage (user_id, date, count)
        VALUES (?, ?, 1)
        ON CONFLICT(user_id, date)
        DO UPDATE SET count = count + 1
        """,
        (user_id, today),
    )

    conn.commit()
    conn.close()


# -----------------------------
# File history
# -----------------------------
def save_file_history(user_id: int, file_name: str, rows: int, columns: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO file_history (user_id, file_name, rows, columns, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            file_name,
            rows,
            columns,
            datetime.utcnow().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


def get_file_history(user_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT file_name, rows, columns, created_at
        FROM file_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (user_id,),
    )

    rows = cur.fetchall()
    conn.close()
    return rows
