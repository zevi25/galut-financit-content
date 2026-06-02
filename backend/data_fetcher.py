"""
Market data fetching — multi-source with fallback:
  1. yfinance library              — primary (handles auth internally)
  2. Yahoo Finance (crumb+cookie)  — fallback
  3. CNBC Markets API              — fallback 2
  4. "market closed" message       — last resort (Claude still writes a useful post)
"""

import feedparser
import requests
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from backend.config import GLOBES_RSS_URL, THEMARKER_RSS_URL

log = logging.getLogger(__name__)
_CACHE_FILE = Path(__file__).parent.parent / "market_cache.json"

try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    _HAS_YFINANCE = False

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
_crumb = None  # type: Optional[str]


# ── Source 0: yfinance library ───────────────────────────────

def _yfinance_ticker(symbol: str) -> dict:
    """Use yfinance package — handles cookies/crumb internally."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d", auto_adjust=True)
    if hist.empty or len(hist) < 2:
        raise ValueError("Not enough data from yfinance")
    last_close = float(hist["Close"].iloc[-1])
    prev_close = float(hist["Close"].iloc[-2])
    change = last_close - prev_close
    return {
        "close":      round(last_close, 2),
        "change":     round(change, 2),
        "change_pct": round((change / prev_close) * 100, 2),
        "date":       hist.index[-1].strftime("%Y-%m-%d"),
    }


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


# ── Cache helpers ─────────────────────────────────────────────

def _save_cache(data: dict):
    """Save successful market data to local cache file."""
    try:
        good = {k: v for k, v in data.items() if "error" not in v}
        if good:
            _CACHE_FILE.write_text(json.dumps({"fetched": datetime.now().strftime("%Y-%m-%d"), "data": good}))
    except Exception:
        pass

def _load_cache() -> dict:
    """Load last cached market data; returns {} if none."""
    try:
        if _CACHE_FILE.exists():
            saved = json.loads(_CACHE_FILE.read_text())
            fetched = saved.get("fetched", "")
            return {k: {**v, "_cache_date": fetched} for k, v in saved.get("data", {}).items()}
    except Exception:
        pass
    return {}


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

    for name, ticker in TICKERS.items():
        # Try 1: yfinance
        if _HAS_YFINANCE:
            try:
                result[name] = _yfinance_ticker(ticker)
                continue
            except Exception:
                pass

        # Try 2: Yahoo Finance direct (crumb+cookie)
        try:
            result[name] = _yahoo_ticker(ticker)
            continue
        except Exception as e:
            result[name] = {"error": str(e)}

    # Try 3: CNBC for any still-failed US indices
    if any("error" in v for v in result.values()):
        try:
            cnbc = _cnbc_all()
            for name, data in cnbc.items():
                if "error" in result.get(name, {}):
                    result[name] = data
        except Exception:
            pass

    # Save successful data to cache
    _save_cache(result)

    # Try 4: Last cached data for anything still failing
    if any("error" in v for v in result.values()):
        cached = _load_cache()
        for name in list(result.keys()):
            if "error" in result.get(name, {}) and name in cached:
                result[name] = cached[name]
                log.warning("Using cached market data for %s from %s", name, cached[name].get("_cache_date"))

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

    # Check if any are from cache
    cached_dates = {v.get("_cache_date") for v in good.values() if v.get("_cache_date")}
    cache_note = f" [נתוני גיבוי מ-{min(cached_dates)}]" if cached_dates else ""

    lines = [f"נתוני שוק (סגירה אחרונה){cache_note}:"]
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
