import anthropic
from datetime import datetime
from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, WEEKLY_TOPICS
from backend.data_fetcher import format_market_for_prompt, format_news_for_prompt

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """אתה עוזר תוכן מקצועי לקבוצות WhatsApp בשם "לצאת מהגלות הפיננסית".
הקהל הוא אנשים מהמגזר החרדי שמתחילים ללמוד על שוק ההון.

כללי כתיבה:
- עברית ברורה ופשוטה, ללא עברית "ספרותית"
- טון חם, קהילתי ומעודד – כמו שמדברים עם חבר מבין
- אין ז'רגון פיננסי ללא הסבר
- השתמש באמוג'ים בצורה מתונה לקריאות
- כל פוסט לVhatsApp מקסימום 200-250 מילים
- אל תציין שאתה AI
- כתוב ישירות בגוף הפוסט, ללא כותרת "כותרת:" או הקדמות"""


def _week_topic() -> str:
    week_num = datetime.now().isocalendar()[1]
    return WEEKLY_TOPICS[week_num % len(WEEKLY_TOPICS)]


def generate_market_summary(market_data: dict) -> str:
    market_text = format_market_for_prompt(market_data)
    today = datetime.now().strftime("%A, %d/%m/%Y")

    messages = [
        {
            "role": "user",
            "content": f"""כתוב פוסט סיכום שוק יומי לקבוצת WhatsApp.

תאריך: {today}
{market_text}

הפוסט צריך לכלול:
1. פתיחה חמה ומזמינה
2. מה קרה בשוק (המספרים חשובים, הסבר בשפה פשוטה מה הם אומרים)
3. משפט אחד: מה כדאי לשים לב אליו היום
4. סיום חיובי ומעודד

כתוב כפוסט אחד רציף, מוכן להדבקה ישירה לוואטסאפ."""
        }
    ]

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )
    return response.content[0].text.strip()


def generate_investment_tip() -> str:
    topic = _week_topic()

    messages = [
        {
            "role": "user",
            "content": f"""כתוב פוסט "טיפ השקעות יומי" לקבוצת WhatsApp.

נושא השבוע: {topic}

הפוסט צריך לכלול:
1. כותרת מושכת עם אמוג'י
2. הסבר ברור של המושג/טיפ
3. דוגמה פשוטה מהחיים
4. שאלה קצרה לעידוד מחשבה (לא חובה לענות)

כתוב כפוסט אחד רציף, מוכן להדבקה ישירה לוואטסאפ."""
        }
    ]

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )
    return response.content[0].text.strip()


def generate_news_analysis(news: list) -> str:
    news_text = format_news_for_prompt(news)

    messages = [
        {
            "role": "user",
            "content": f"""כתוב פוסט "חדשות כלכליות עם פרשנות" לקבוצת WhatsApp.

{news_text}

בחר 2-3 כותרות הכי רלוונטיות למשקיע הפרטי.
לכל כותרת הסבר בשורה-שתיים: מה זה אומר לי כמשקיע רגיל?

פורמט:
📰 כותרת הידיעה
➡️ מה זה אומר לך: [הסבר]

כתוב כפוסט אחד רציף, מוכן להדבקה ישירה לוואטסאפ."""
        }
    ]

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=700,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )
    return response.content[0].text.strip()


def generate_all(market_data: dict, news: list) -> tuple[str, str, str]:
    market_summary = generate_market_summary(market_data)
    investment_tip = generate_investment_tip()
    news_analysis = generate_news_analysis(news)
    return market_summary, investment_tip, news_analysis
