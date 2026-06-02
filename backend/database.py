import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "content.db"

# All editable sections with their status columns
ALL_SECTIONS = [
    "market_summary",
    "investment_tip",
    "news_analysis",
    "stock_of_week",
    "investor_psychology",
    "weekly_events",
    "facebook_post",
    "instagram_carousel",
    "instagram_story",
]


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        # Base table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                market_summary TEXT,
                investment_tip TEXT,
                news_analysis TEXT,
                market_summary_status TEXT DEFAULT 'draft',
                investment_tip_status TEXT DEFAULT 'draft',
                news_analysis_status TEXT DEFAULT 'draft',
                raw_market_data TEXT,
                raw_news TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # Add new columns if they don't exist (safe migration)
        new_cols = [
            ("stock_of_week",            "TEXT"),
            ("stock_of_week_status",     "TEXT DEFAULT 'draft'"),
            ("investor_psychology",      "TEXT"),
            ("investor_psychology_status","TEXT DEFAULT 'draft'"),
            ("weekly_events",            "TEXT"),
            ("weekly_events_status",     "TEXT DEFAULT 'draft'"),
            ("facebook_post",            "TEXT"),
            ("facebook_post_status",     "TEXT DEFAULT 'draft'"),
            ("instagram_carousel",       "TEXT"),
            ("instagram_carousel_status","TEXT DEFAULT 'draft'"),
            ("instagram_story",          "TEXT"),
            ("instagram_story_status",   "TEXT DEFAULT 'draft'"),
        ]
        existing = {row[1] for row in conn.execute("PRAGMA table_info(daily_content)")}
        for col, col_type in new_cols:
            if col not in existing:
                conn.execute(f"ALTER TABLE daily_content ADD COLUMN {col} {col_type}")
        conn.commit()


def save_draft(date: str, **fields):
    """Save or update a draft. Pass any subset of section fields as kwargs."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM daily_content WHERE date = ?", (date,)
        ).fetchone()

        if existing:
            set_clauses = ", ".join(f"{k} = ?" for k in fields)
            set_clauses += ", updated_at = datetime('now')"
            # Reset statuses to draft for updated fields
            for key in list(fields.keys()):
                if key in ALL_SECTIONS:
                    fields[f"{key}_status"] = "draft"
            set_clauses = ", ".join(f"{k} = ?" for k in fields)
            set_clauses += ", updated_at = datetime('now')"
            conn.execute(
                f"UPDATE daily_content SET {set_clauses} WHERE date = ?",
                (*fields.values(), date)
            )
        else:
            fields["date"] = date
            cols = ", ".join(fields.keys())
            placeholders = ", ".join("?" * len(fields))
            conn.execute(
                f"INSERT INTO daily_content ({cols}) VALUES ({placeholders})",
                tuple(fields.values())
            )
        conn.commit()


def get_content(date: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM daily_content WHERE date = ?", (date,)
        ).fetchone()
        return dict(row) if row else None


def update_section(date: str, section: str, text: str):
    if section not in ALL_SECTIONS:
        raise ValueError(f"Invalid section: {section}")
    with get_conn() as conn:
        conn.execute(
            f"UPDATE daily_content SET {section} = ?, updated_at = datetime('now') WHERE date = ?",
            (text, date)
        )
        conn.commit()


def approve_section(date: str, section: str):
    if section not in ALL_SECTIONS:
        raise ValueError(f"Invalid section: {section}")
    col = f"{section}_status"
    with get_conn() as conn:
        conn.execute(
            f"UPDATE daily_content SET {col} = 'approved', updated_at = datetime('now') WHERE date = ?",
            (date,)
        )
        conn.commit()


def get_history(limit: int = 14):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, market_summary_status, investment_tip_status, news_analysis_status, "
            "stock_of_week_status, investor_psychology_status, weekly_events_status, "
            "facebook_post_status, instagram_carousel_status, instagram_story_status, created_at "
            "FROM daily_content ORDER BY date DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
