import sqlite3
from contextlib import contextmanager
from pathlib import Path

from financial_analyst.config import config
from financial_analyst.observability.logger import get_logger

logger = get_logger(__name__)


@contextmanager
def _conn():
    """Open a fresh connection, enable WAL, yield, commit, close."""
    db_path = config["memory"]["db_path"]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _setup_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                user_id TEXT PRIMARY KEY,
                age INTEGER,
                monthly_income REAL,
                risk_tolerance TEXT,
                dependents INTEGER,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)


def save_profile(user_id: str, profile: dict) -> None:
    """Upsert a user's profile fields (age, monthly_income, risk_tolerance, dependents).
    Fields absent from `profile` leave the existing stored value untouched."""
    _setup_db()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO profile (user_id, age, monthly_income, risk_tolerance, dependents, updated_at)
            VALUES (:user_id, :age, :monthly_income, :risk_tolerance, :dependents, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                age = COALESCE(excluded.age, profile.age),
                monthly_income = COALESCE(excluded.monthly_income, profile.monthly_income),
                risk_tolerance = COALESCE(excluded.risk_tolerance, profile.risk_tolerance),
                dependents = COALESCE(excluded.dependents, profile.dependents),
                updated_at = excluded.updated_at
            """,
            {
                "user_id": user_id,
                "age": profile.get("age"),
                "monthly_income": profile.get("monthly_income"),
                "risk_tolerance": profile.get("risk_tolerance"),
                "dependents": profile.get("dependents"),
            },
        )
    logger.info(f"Saved profile for user {user_id}")


def get_profile(user_id: str) -> dict | None:
    _setup_db()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM profile WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None
