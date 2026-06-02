import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "content.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
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
        conn.commit()


def save_draft(date: str, market_summary: str, investment_tip: str,
               news_analysis: str, raw_market_data: dict, raw_news: list):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM daily_content WHERE date = ?", (date,)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE daily_content SET
                    market_summary = ?,
                    investment_tip = ?,
                    news_analysis = ?,
                    market_summary_status = 'draft',
                    investment_tip_status = 'draft',
                    news_analysis_status = 'draft',
                    raw_market_data = ?,
                    raw_news = ?,
                    updated_at = datetime('now')
                WHERE date = ?
            """, (market_summary, investment_tip, news_analysis,
                  json.dumps(raw_market_data, ensure_ascii=False),
                  json.dumps(raw_news, ensure_ascii=False), date))
        else:
            conn.execute("""
                INSERT INTO daily_content
                    (date, market_summary, investment_tip, news_analysis,
                     raw_market_data, raw_news)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date, market_summary, investment_tip, news_analysis,
                  json.dumps(raw_market_data, ensure_ascii=False),
                  json.dumps(raw_news, ensure_ascii=False)))
        conn.commit()


def get_content(date: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM daily_content WHERE date = ?", (date,)
        ).fetchone()
        return dict(row) if row else None


def update_section(date: str, section: str, text: str):
    allowed = {"market_summary", "investment_tip", "news_analysis"}
    if section not in allowed:
        raise ValueError(f"Invalid section: {section}")
    with get_conn() as conn:
        conn.execute(
            f"UPDATE daily_content SET {section} = ?, updated_at = datetime('now') WHERE date = ?",
            (text, date)
        )
        conn.commit()


def approve_section(date: str, section: str):
    allowed = {"market_summary", "investment_tip", "news_analysis"}
    if section not in allowed:
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
            "SELECT date, market_summary_status, investment_tip_status, news_analysis_status, created_at "
            "FROM daily_content ORDER BY date DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
