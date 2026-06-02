"""
Market data fetching — multi-source with fallback:
  1. Yahoo Finance (crumb+cookie) — primary
  2. CNBC Markets API              — fallback
  3. "market closed" message       — last resort (Claude still writes a useful post)
"""

import feedparser
import requests
import json
from datetime import datetime
from backend.config import GLOBES_RSS_URL, THEMARKER_RSS_URL

TICKERS = {
    "S&P 500":   "^GSPC",
    'נאסד"ק':    "^IXIC",
    "דאו ג'ונס": "^DJI",
    'ת"א 125':   "^TA125.TA",
}

CNBC_SYMBOLS = {
    "S&P 500":   ".SPX",
    'נאסד"ק':    ".NDX",
    "דאו ג'ונס": ".DJIA",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_yf_session = requests.Session()
_yf_session.headers.update(_HEADERS)
_crumb: str | None = None


# ── Source 1: Yahoo Finance ───────────────────────────────────

def _get_crumb() -> str:
    global _crumb
    _yf_session.get("https://finance.yahoo.com/", timeout=10)
    r = _yf_session.get(
        "https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10
    )
    if r.status_code == 200 and r.text and r.text.strip() not in ("", "null"):
        _crumb = r.text.strip()
        return _crumb
    raise RuntimeError(f"Yahoo crumb failed: {r.status_code}")


def _yahoo_ticker(symbol: str) -> dict:
    crumb = _get_crumb()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    r = _yf_session.get(url, params={"interval": "1d", "range": "5d", "crumb": crumb}, timeout=15)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    closes = res["indicators"]["quote"][0]["close"]
    ts = res["timestamp"]
    pairs = [(t, c) for t, c in zip(ts, closes) if c is not None]
    if len(pairs) < 2:
        raise ValueError("Not enough data")
    last_ts, last_c = pairs[-1]
    prev_ts, prev_c = pairs[-2]
    change = last_c - prev_c
    return {
        "close":      round(last_c, 2),
        "change":     round(change, 2),
        "change_pct": round((change / prev_c) * 100, 2),
        "date":       datetime.utcfromtimestamp(last_ts).strftime("%Y-%m-%d"),
    }


# ── Source 2: CNBC ────────────────────────────────────────────

def _cnbc_all() -> dict:
    symbols = "|".join(CNBC_SYMBOLS.values())
    url = (
        "https://quote.cnbc.com/quote-html-webservice/restservices/cff/quote"
        f"?symbols={symbols}&requestMethod=itv&noform=1&partnerId=2"
        "&fund=1&exthrs=1&output=json&events=1"
    )
    r = requests.get(url, headers=_HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()
    results = {}
    quotes = data.get("FormattedQuoteResult", {}).get("FormattedQuote", [])
    for q in quotes:
        symbol = q.get("symbol", "")
        for heb_name, cnbc_sym in CNBC_SYMBOLS.items():
            if symbol == cnbc_sym:
                try:
                    last = float(str(q.get("last", "0")).replace(",", ""))
                    change = float(str(q.get("change", "0")).replace(",", ""))
                    change_pct = float(str(q.get("change_pct", "0")).replace(",", "").replace("%", ""))
                    results[heb_name] = {
                        "close":      round(last, 2),
                        "change":     round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "date":       datetime.now().strftime("%Y-%m-%d"),
                    }
                except Exception:
                    pass
    return results


# ── Public interface ──────────────────────────────────────────

def fetch_market_data() -> dict:
    global _crumb
    _crumb = None  # fresh crumb every day

    result = {}

    # Try Yahoo Finance first
    yahoo_ok = True
    for name, ticker in TICKERS.items():
        try:
            result[name] = _yahoo_ticker(ticker)
        except Exception as e:
            result[name] = {"error": str(e)}
            yahoo_ok = False

    # If Yahoo failed, try CNBC for US indices
    if not yahoo_ok:
        try:
            cnbc = _cnbc_all()
            for name, data in cnbc.items():
                if "error" in result.get(name, {}):
                    result[name] = data
        except Exception:
            pass

    return result


# ── News ──────────────────────────────────────────────────────

def fetch_globes_news(max_items: int = 8) -> list:
    items = []
    for url in [GLOBES_RSS_URL, THEMARKER_RSS_URL]:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[: max_items // 2]:
                items.append({
                    "title":   entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300],
                    "link":    entry.get("link", ""),
                    "source":  "גלובס" if "globes" in url else "TheMarker",
                })
        except Exception:
            pass
    return items[:max_items]


# ── Prompt formatting ─────────────────────────────────────────

def format_market_for_prompt(data: dict) -> str:
    good = {k: v for k, v in data.items() if "error" not in v}
    if not good:
        return "נתוני שוק: לא זמינים כרגע (ייתכן שהבורסה סגורה או שיש בעיית חיבור)"
    lines = ["נתוני שוק (סגירה אחרונה):"]
    for name, d in good.items():
        arrow = "📈" if d["change_pct"] >= 0 else "📉"
        sign  = "+" if d["change_pct"] >= 0 else ""
        lines.append(f"  {arrow} {name}: {d['close']:,.2f} ({sign}{d['change_pct']:.2f}%)")
    return "\n".join(lines)


def format_news_for_prompt(news: list) -> str:
    if not news:
        return "כותרות: לא זמינות כרגע"
    lines = ["כותרות עדכניות:"]
    for i, item in enumerate(news, 1):
        lines.append(f"  {i}. [{item['source']}] {item['title']}")
        if item.get("summary"):
            lines.append(f"     {item['summary'][:150]}...")
    return "\n".join(lines)
