import feedparser
import yfinance as yf
from datetime import datetime, timedelta
from backend.config import MARKET_TICKERS, GLOBES_RSS_URL, THEMARKER_RSS_URL


def fetch_market_data() -> dict:
    result = {}
    for name, ticker in MARKET_TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if len(hist) < 2:
                continue
            yesterday = hist.iloc[-1]
            prev_day = hist.iloc[-2]
            change = yesterday["Close"] - prev_day["Close"]
            change_pct = (change / prev_day["Close"]) * 100
            result[name] = {
                "close": round(float(yesterday["Close"]), 2),
                "change": round(float(change), 2),
                "change_pct": round(float(change_pct), 2),
                "date": str(hist.index[-1].date()),
            }
        except Exception as e:
            result[name] = {"error": str(e)}
    return result


def fetch_globes_news(max_items: int = 8) -> list:
    items = []
    for url in [GLOBES_RSS_URL, THEMARKER_RSS_URL]:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_items // 2]:
                items.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300],
                    "link": entry.get("link", ""),
                    "source": "גלובס" if "globes" in url else "TheMarker",
                })
        except Exception:
            pass
    return items[:max_items]


def format_market_for_prompt(data: dict) -> str:
    lines = ["נתוני שוק (סגירה אחרונה):"]
    for name, d in data.items():
        if "error" in d:
            continue
        arrow = "📈" if d["change_pct"] >= 0 else "📉"
        sign = "+" if d["change_pct"] >= 0 else ""
        lines.append(
            f"  {arrow} {name}: {d['close']:,.2f} ({sign}{d['change_pct']:.2f}%)"
        )
    return "\n".join(lines)


def format_news_for_prompt(news: list) -> str:
    lines = ["כותרות עדכניות:"]
    for i, item in enumerate(news, 1):
        lines.append(f"  {i}. [{item['source']}] {item['title']}")
        if item.get("summary"):
            lines.append(f"     {item['summary'][:150]}...")
    return "\n".join(lines)
