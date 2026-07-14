import sqlite3
from contextlib import contextmanager
from pathlib import Path

from financial_analyst.config import config
from financial_analyst.memory import portfolio_store
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
            CREATE TABLE IF NOT EXISTS watchlist (
                user_id TEXT, symbol TEXT, source TEXT,
                added_at TEXT DEFAULT (datetime('now')), is_active INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, symbol)
            );
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT, price REAL, as_of TEXT,
                fetched_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, symbol TEXT, week_of TEXT,
                action TEXT, rationale TEXT, confidence TEXT, evidence TEXT,
                price_at_time REAL, created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending'
            );
            CREATE INDEX IF NOT EXISTS idx_price_history_symbol ON price_history(symbol, fetched_at);
            CREATE INDEX IF NOT EXISTS idx_recommendations_user ON recommendations(user_id, status);
        """)


def add_to_watchlist(user_id: str, symbol: str, source: str) -> None:
    """source: 'holding' (auto, via portfolio upload) or 'manual' (/watch)."""
    _setup_db()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO watchlist (user_id, symbol, source, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, symbol) DO UPDATE SET is_active = 1
            """,
            (user_id, symbol.upper(), source),
        )
    logger.info(f"Added {symbol} to watchlist for {user_id} (source={source})")


def get_watchlist(user_id: str) -> list[str]:
    """Union of current holding symbols + manually-watched symbols."""
    _setup_db()
    holdings = portfolio_store.get_portfolio(user_id)
    holding_symbols = {h["symbol"] for h in holdings}
    with _conn() as conn:
        rows = conn.execute(
            "SELECT symbol FROM watchlist WHERE user_id = ? AND is_active = 1", (user_id,)
        ).fetchall()
    manual_symbols = {r["symbol"] for r in rows}
    return sorted(holding_symbols | manual_symbols)


def record_price(symbol: str, price: float, as_of: str) -> None:
    _setup_db()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO price_history (symbol, price, as_of) VALUES (?, ?, ?)",
            (symbol.upper(), price, as_of),
        )


def get_price_history(symbol: str, days: int = 7) -> list[dict]:
    """Most-recent-first, limited to the last `days` days."""
    _setup_db()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM price_history
            WHERE symbol = ? AND fetched_at >= datetime('now', ?)
            ORDER BY fetched_at DESC
            """,
            (symbol.upper(), f"-{days} days"),
        ).fetchall()
    return [dict(r) for r in rows]


def save_recommendation(
    user_id: str, symbol: str, week_of: str, action: str, rationale: str,
    confidence: str, evidence: str, price_at_time: float | None,
) -> None:
    _setup_db()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO recommendations
                (user_id, symbol, week_of, action, rationale, confidence, evidence, price_at_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, symbol, week_of, action, rationale, confidence, evidence, price_at_time),
        )
    logger.info(f"Saved recommendation for {user_id}/{symbol} (week={week_of}, action={action})")


def get_pending_recommendations(user_id: str) -> list[dict]:
    _setup_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_reviewed(recommendation_id: int) -> None:
    _setup_db()
    with _conn() as conn:
        conn.execute(
            "UPDATE recommendations SET status = 'reviewed' WHERE id = ?", (recommendation_id,)
        )
