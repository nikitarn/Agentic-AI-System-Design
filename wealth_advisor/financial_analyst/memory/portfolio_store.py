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
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, symbol TEXT, name TEXT, type TEXT,
                quantity REAL, avg_price REAL, current_price REAL,
                uploaded_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, date TEXT, description TEXT,
                debit REAL, credit REAL, balance REAL
            );
            CREATE INDEX IF NOT EXISTS idx_holdings_user ON holdings(user_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
        """)


def save_portfolio(user_id: str, holdings: list[dict]) -> None:
    """Replace the stored holdings for user_id with the given list (from load_portfolio())."""
    _setup_db()
    with _conn() as conn:
        conn.execute("DELETE FROM holdings WHERE user_id = ?", (user_id,))
        conn.executemany(
            """
            INSERT INTO holdings (user_id, symbol, name, type, quantity, avg_price, current_price)
            VALUES (:user_id, :symbol, :name, :type, :quantity, :avg_price, :current_price)
            """,
            [{"user_id": user_id, **h} for h in holdings],
        )
    logger.info(f"Saved {len(holdings)} holdings for user {user_id}")


def get_portfolio(user_id: str) -> list[dict]:
    _setup_db()
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM holdings WHERE user_id = ?", (user_id,)).fetchall()
    return [dict(r) for r in rows]


def save_statement(user_id: str, rows: list[dict]) -> None:
    """Append transaction rows for user_id (from load_statement())."""
    _setup_db()
    with _conn() as conn:
        conn.executemany(
            """
            INSERT INTO transactions (user_id, date, description, debit, credit, balance)
            VALUES (:user_id, :date, :description, :debit, :credit, :balance)
            """,
            [{"user_id": user_id, **r} for r in rows],
        )
    logger.info(f"Saved {len(rows)} transactions for user {user_id}")


def get_transactions(user_id: str) -> list[dict]:
    _setup_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY date", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]
