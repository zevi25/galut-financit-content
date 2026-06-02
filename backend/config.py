import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WAVESPEED_API_KEY = os.getenv("WAVESPEED_API_KEY", "")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", 7))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", 30))

CLAUDE_MODEL = "claude-sonnet-4-6"

MARKET_TICKERS = {
    "S&P 500": "^GSPC",
    "נאסד\"ק": "^IXIC",
    "דאו ג'ונס": "^DJI",
    "ת\"א 125": "^TA125.TA",
}

GLOBES_RSS_URL = "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederNode?iID=1342"
THEMARKER_RSS_URL = "https://www.themarker.com/srv/rss"

WEEKLY_TOPICS = [
    "יסודות השקעה – מה זה מניה ולמה היא עולה ויורדת",
    "פסיכולוגיה של משקיע – כיצד לא לפנות בעת ירידות",
    "ניתוח בסיסי – כיצד לבחון חברה לפני שמשקיעים",
    "גיוון תיק – למה לא שמים את כל הביצים בסל אחד",
    "אגרות חוב ומניות – ההבדל ומתי להשתמש בכל אחד",
    "קרנות סל (ETF) – השקעה פשוטה לכולם",
    "שוק ישראלי לעומת שוק אמריקאי – יתרונות וחסרונות",
    "מס על השקעות – מה חשוב לדעת",
]
