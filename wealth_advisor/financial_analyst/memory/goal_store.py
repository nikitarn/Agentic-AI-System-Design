import json
import sqlite3
import uuid
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
            CREATE TABLE IF NOT EXISTS goals (
                goal_id TEXT PRIMARY KEY, user_id TEXT, description TEXT,
                target_type TEXT, target_value REAL, horizon_months INTEGER,
                created_at TEXT DEFAULT (datetime('now')), status TEXT DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS goal_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT REFERENCES goals(goal_id),
                plan_json TEXT, approved INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_goals_user ON goals(user_id);
        """)


def save_goal(
    user_id: str, description: str, target_type: str, target_value: float, horizon_months: int
) -> str:
    """Create a new goal row, return its generated goal_id."""
    _setup_db()
    goal_id = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO goals (goal_id, user_id, description, target_type, target_value, horizon_months)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (goal_id, user_id, description, target_type, target_value, horizon_months),
        )
    logger.info(f"Saved goal {goal_id} for user {user_id}")
    return goal_id


def save_goal_plan(goal_id: str, plan, approved: bool) -> None:
    """Persist a GoalPlan (pydantic model) as JSON, tied to its goal_id."""
    _setup_db()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO goal_plans (goal_id, plan_json, approved) VALUES (?, ?, ?)",
            (goal_id, plan.model_dump_json(), int(approved)),
        )
    logger.info(f"Saved plan for goal {goal_id} (approved={approved})")


def get_goal_history(user_id: str) -> list[dict]:
    """Return all goals for a user, each with its latest saved plan (if any)."""
    _setup_db()
    with _conn() as conn:
        goals = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM goals WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
            ).fetchall()
        ]
        for goal in goals:
            plan_row = conn.execute(
                "SELECT * FROM goal_plans WHERE goal_id = ? ORDER BY created_at DESC LIMIT 1",
                (goal["goal_id"],),
            ).fetchone()
            goal["latest_plan"] = json.loads(plan_row["plan_json"]) if plan_row else None
            goal["plan_approved"] = bool(plan_row["approved"]) if plan_row else False
    return goals
