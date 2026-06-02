"""
Market data fetching — multi-source with fallback:
  1. Nasdaq public API (SPY/QQQ/DIA ETFs + COMP index) — primary, no auth needed
  2. yfinance library                                   — fallback
  3. Yahoo Finance (crumb+cookie)                       — fallback 2
  4. File cache (last successful fetch)                 — last resort
"""

import os
import feedparser
import requests
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from backend.config import GLOBES_RSS_URL, THEMARKER_RSS_URL

log = logging.getLogger(__name__)
_data_dir = Path(os.environ.get("DATA_DIR", str(Path(__file__).parent.parent)))
_CACHE_FILE = _data_dir / "market_cache.json"

try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    _HAS_YFINANCE = False

# ── Ticker maps ───────────────────────────────────────────────

# Nasdaq API: ETF proxies for US indices (free, no auth)
_NASDAQ_ETF = {
    "S&P 500":    ("SPY",  "etf"),
    'נאסד"ק':     ("COMP", "index"),
    "דאו ג'ונס":  ("DIA",  "etf"),
}

# yfinance / Yahoo Finance tickers
_YF_TICKERS = {
    "S&P 500":   "^GSPC",
    'נאסד"ק':    "^IXIC",
    "דאו ג'ונס": "^DJI",
    'ת"א 125':   "^TA125.TA",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}

_yf_session = requests.Session()
_yf_session.headers.update({
    "User-Agent": _HEADERS["User-Agent"],
    "Accept-Language": _HEADERS["Accept-Language"],
})
_crumb: Optional[str] = None


# ── Source 1: Nasdaq public API ───────────────────────────────

def _clean_num(s: str) -> str:
    """Strip $, commas, +, spaces from a numeric string."""
    return s.replace("$", "").replace(",", "").replace("+", "").strip()


def _nasdaq_ticker(symbol: str, asset_class: str) -> dict:
    """Free Nasdaq API — works without any auth or API key."""
    url = f"https://api.nasdaq.com/api/quote/{symbol}/info?assetclass={asset_class}"
    r = requests.get(url, headers=_HEADERS, timeout=12)
    r.raise_for_status()
    data = r.json().get("data", {})
    primary  = data.get("primaryData", {})
    summary  = data.get("summaryData", {})

    # Price — try lastSalePrice, fall back to previousClose from summary
    raw_price = _clean_num(primary.get("lastSalePrice", "") or "")
    if not raw_price:
        # summaryData["PreviousClose"] is a dict {"value": "$xxx"}
        pc = summary.get("PreviousClose", {}) or summary.get("previousClose", {})
        raw_price = _clean_num((pc.get("value") or "").replace("$", ""))
    if not raw_price:
        raise ValueError(f"No price data available for {symbol}")

    last_close = float(raw_price)

    # % change
    raw_pct = _clean_num(primary.get("percentageChange", "0%").replace("%", ""))
    try:
        change_pct = float(raw_pct) if raw_pct else 0.0
    except ValueError:
        change_pct = 0.0

    # Absolute change
    prev_close = last_close / (1 + change_pct / 100) if change_pct != -100 else last_close
    change = last_close - prev_close

    return {
        "close":      round(last_close, 2),
        "change":     round(change, 2),
        "change_pct": round(change_pct, 2),
        "date":       datetime.now().strftime("%Y-%m-%d"),
    }


# ── Source 2: yfinance library ────────────────────────────────

def _yfinance_ticker(symbol: str) -> dict:
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


# ── Source 3: Yahoo Finance (crumb+cookie) ────────────────────

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
    try:
        good = {k: v for k, v in data.items() if "error" not in v}
        if good:
            _CACHE_FILE.write_text(
                json.dumps({"fetched": datetime.now().strftime("%Y-%m-%d"), "data": good},
                           ensure_ascii=False)
            )
    except Exception:
        pass


def _load_cache() -> dict:
    try:
        if _CACHE_FILE.exists():
            saved = json.loads(_CACHE_FILE.read_text())
            fetched = saved.get("fetched", "")
            return {k: {**v, "_cache_date": fetched} for k, v in saved.get("data", {}).items()}
    except Exception:
        pass
    return {}


# ── Public interface ──────────────────────────────────────────

def fetch_market_data() -> dict:
    global _crumb
    _crumb = None

    result = {}

    # ── US Indices via Nasdaq API (primary) ──
    for name, (sym, cls) in _NASDAQ_ETF.items():
        try:
            result[name] = _nasdaq_ticker(sym, cls)
            log.info("Nasdaq API OK: %s = %s", name, result[name].get("close"))
        except Exception as e:
            log.warning("Nasdaq API failed for %s: %s", name, e)
            result[name] = {"error": str(e)}

    # ── TA-125 via yfinance (Israeli index — not on Nasdaq API) ──
    ta125_name = 'ת"א 125'
    ta125_sym  = _YF_TICKERS[ta125_name]

    if _HAS_YFINANCE:
        try:
            result[ta125_name] = _yfinance_ticker(ta125_sym)
        except Exception as e:
            log.warning("yfinance failed for TA-125: %s", e)
            try:
                result[ta125_name] = _yahoo_ticker(ta125_sym)
            except Exception as e2:
                log.warning("Yahoo direct failed for TA-125: %s", e2)
                result[ta125_name] = {"error": str(e2)}
    else:
        try:
            result[ta125_name] = _yahoo_ticker(ta125_sym)
        except Exception as e:
            result[ta125_name] = {"error": str(e)}

    # ── Fallback for any still-failed items: use cache ──
    _save_cache(result)
    if any("error" in v for v in result.values()):
        cached = _load_cache()
        for name in list(result.keys()):
            if "error" in result.get(name, {}) and name in cached:
                result[name] = cached[name]
                log.warning("Using cached data for %s (from %s)", name, cached[name].get("_cache_date"))

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
