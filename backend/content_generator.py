import anthropic
import json
import random
from backend.config import israel_now as _now_fn
from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, WEEKLY_TOPICS
from backend.data_fetcher import format_market_for_prompt, format_news_for_prompt

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """אתה עוזר תוכן מקצועי לערוצי מדיה חברתית בשם "לצאת מהגלות הפיננסית".
הקהל הוא אנשים מהמגזר החרדי שמתחילים ללמוד על שוק ההון.

כללי כתיבה:
- עברית ברורה ופשוטה, ללא עברית "ספרותית"
- טון חם, קהילתי ומעודד – כמו שמדברים עם חבר מבין
- אין ז'רגון פיננסי ללא הסבר
- השתמש באמוג'ים בצורה מתונה לקריאות
- אל תציין שאתה AI
- כתוב ישירות בגוף הפוסט, ללא כותרת "כותרת:" או הקדמות"""

WHATSAPP_RULE = "כל פוסט לוואטסאפ מקסימום 200-250 מילים. כתוב כפוסט אחד רציף, מוכן להדבקה ישירה."

# ── variation helpers ──────────────────────────────────────────

_VARIATION_ANGLES = [
    "התחל עם שאלה רטורית שמעוררת סקרנות",
    "התחל עם סיפור קצר מהחיים האמיתיים",
    "התחל עם עובדה מפתיעה או נתון בלתי צפוי",
    "התחל עם השוואה בין שני דברים מוכרים",
    "התחל עם ציטוט קצר של משקיע מפורסם ופרש אותו בעברית פשוטה",
    "התחל ישירות עם ה'bottom line' ואז הסבר את ה-'למה'",
    "התחל עם תרחיש היפותטי – 'מה היה קורה אם...'",
    "התחל עם טעות נפוצה שאנשים עושים, ואז תקן אותה",
]

_VARIATION_TONES = [
    "כתוב בטון אנרגטי ומלהיב",
    "כתוב בטון שקט ומרגיע, כמו שיחה בין חברים",
    "כתוב בטון מאתגר – כזה שגורם לקורא לחשוב מחדש",
    "כתוב בטון סיפורי – תן לקורא להרגיש שהוא בתוך הסיפור",
]

def _variation_hint() -> str:
    """Returns a random angle+tone instruction to force different output."""
    angle = random.choice(_VARIATION_ANGLES)
    tone  = random.choice(_VARIATION_TONES)
    return f"\n\n⚡ הנחיית וריאציה (חובה): {angle}. {tone}. כתוב משהו שונה לחלוטין ממה שכתבת בעבר."


# ── helpers ────────────────────────────────────────────────────

def _week_topic() -> str:
    week_num = _now_fn().isocalendar()[1]
    return WEEKLY_TOPICS[week_num % len(WEEKLY_TOPICS)]


def _call(prompt: str, max_tokens: int = 700, vary: bool = False) -> str:
    full_prompt = prompt + (_variation_hint() if vary else "")
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": full_prompt}],
    )
    return resp.content[0].text.strip()


# ══════════════════════════════════════════════════════════════
# WHATSAPP — 5 content types
# ══════════════════════════════════════════════════════════════

def generate_market_summary(market_data: dict, vary: bool = False) -> str:
    today = _now_fn().strftime("%A, %d/%m/%Y")
    market_text = format_market_for_prompt(market_data)
    return _call(f"""כתוב פוסט סיכום שוק יומי לקבוצת WhatsApp.
תאריך: {today}
{market_text}

כלול:
1. פתיחה חמה ומזמינה
2. מה קרה בשוק – המספרים + הסבר פשוט
3. מה כדאי לשים לב אליו היום
4. סיום חיובי ומעודד
{WHATSAPP_RULE}""", vary=vary)


def generate_investment_tip(vary: bool = False) -> str:
    topic = _week_topic()
    return _call(f"""כתוב פוסט "טיפ השקעות" לקבוצת WhatsApp.
נושא השבוע: {topic}

כלול:
1. כותרת מושכת עם אמוג'י
2. הסבר ברור של המושג
3. דוגמה פשוטה מהחיים
4. שאלה קצרה לעידוד מחשבה
{WHATSAPP_RULE}""", vary=vary)


def generate_news_analysis(news: list, vary: bool = False) -> str:
    news_text = format_news_for_prompt(news)
    return _call(f"""כתוב פוסט "חדשות כלכליות עם פרשנות" לקבוצת WhatsApp.
{news_text}

בחר 2-3 כותרות הכי רלוונטיות למשקיע הפרטי.
לכל כותרת: מה זה אומר לי כמשקיע רגיל?
פורמט:
📰 כותרת הידיעה
➡️ מה זה אומר לך: [הסבר]
{WHATSAPP_RULE}""", vary=vary)


def generate_stock_of_week(market_data: dict, vary: bool = False) -> str:
    today = _now_fn().strftime("%d/%m/%Y")
    stocks = ["Apple (AAPL)", "Microsoft (MSFT)", "NVIDIA (NVDA)", "Amazon (AMZN)",
              "Tesla (TSLA)", "Alphabet (GOOGL)", "Meta (META)", "Berkshire Hathaway (BRK.B)",
              "JPMorgan (JPM)", "Johnson & Johnson (JNJ)", "Visa (V)", "Walmart (WMT)"]
    week_num = _now_fn().isocalendar()[1]
    # When vary=True, pick a random stock (not the weekly one)
    stock = random.choice(stocks) if vary else stocks[week_num % len(stocks)]
    return _call(f"""כתוב פוסט "מניה השבוע" לקבוצת WhatsApp.
תאריך: {today}
מניה השבוע: {stock}

כלול:
1. פתיחה מסקרנת
2. מה החברה עושה – בשפה של בן אדם רגיל
3. למה היא מעניינת עכשיו (גידול, מוצר חדש, מגמה בשוק)
4. נקודה אחת שצריך לדעת לפני שמשקיעים
5. סיום – "לא המלצת השקעה, רק הכרות 😊"
{WHATSAPP_RULE}""", vary=vary)


def generate_investor_psychology(vary: bool = False) -> str:
    topics = [
        "אפקט העדר – למה כולם קונים כשהשוק עולה ומוכרים כשהוא יורד",
        "אובדן שנאה – למה כאב הפסד גדול פי 2 מהנאת רווח",
        "אשליית השליטה – למה אנחנו חושבים שאנחנו יודעים מה השוק יעשה",
        "עוגן מחיר – למה קניית מניה ב-100 ש' גורמת לנו לחכות שתחזור ל-100",
        "הטיית אישור – למה אנחנו מחפשים רק מידע שמאשר מה שכבר חשבנו",
        "סבלנות לעומת חמדנות – ההבדל בין משקיע לספקולנט",
        "מהי 'זמן בשוק' ולמה עדיף על 'תזמון שוק'",
        "פחד מהחמצה (FOMO) – כשאנחנו קונים כי 'כולם מרוויחים'",
        "אפקט היוהרה – למה אנחנו חושבים שאנחנו טובים יותר ממה שאנחנו",
    ]
    week_num = _now_fn().isocalendar()[1]
    topic = random.choice(topics) if vary else topics[week_num % len(topics)]
    return _call(f"""כתוב פוסט "פסיכולוגיה של משקיע" לקבוצת WhatsApp.
נושא: {topic}

כלול:
1. פתיחה עם סיפור קצר או דוגמה מהחיים שממחישה את הנושא
2. הסבר מה הטיה זו ואיך היא פוגעת בנו
3. טיפ מעשי אחד להתמודדות
4. שאלה לקהל שמעוררת מחשבה
{WHATSAPP_RULE}""", vary=vary)


def generate_weekly_events(vary: bool = False) -> str:
    today = _now_fn()
    week_str = today.strftime("%d/%m/%Y")
    return _call(f"""כתוב פוסט "מה צפוי השבוע בשוק ההון" לקבוצת WhatsApp.
תאריך היום: {week_str}

כלול:
1. פתיחה – "השבוע עיניים על..."
2. 3-4 אירועים כלכליים חשובים שצפויים השבוע (דוחות חברות גדולות, החלטות ריבית Fed/בנק ישראל, נתוני אינפלציה/תעסוקה)
3. לכל אירוע: מה זה, מתי בערך, ולמה זה חשוב למשקיע הפרטי
4. סיום: "נשמור עיניים פקוחות 👀"

אם אינך בטוח בתאריכים מדויקים – ציין "בערך באמצע השבוע" וכד'.
{WHATSAPP_RULE}""", vary=vary)


# ══════════════════════════════════════════════════════════════
# FACEBOOK — long-form post
# ══════════════════════════════════════════════════════════════

def generate_facebook_post(market_data: dict, news: list, vary: bool = False) -> str:
    market_text = format_market_for_prompt(market_data)
    news_text = format_news_for_prompt(news[:3])
    today = _now_fn().strftime("%A, %d/%m/%Y")
    return _call(f"""כתוב פוסט פייסבוק ארוך ומעמיק לדף "לצאת מהגלות הפיננסית".
תאריך: {today}
{market_text}
{news_text}

הפוסט צריך להיות 350-450 מילים ולכלול:
1. Hook חזק – שורה ראשונה שגורמת לאנשים לעצור ולקרוא
2. סיפור קצר או שאלה שמחברת לחוויה האישית של הקורא
3. התוכן הכלכלי – מה קרה, מה זה אומר, מה ללמוד מזה
4. נקודה אחת מעשית שהקורא יכול לקחת איתו
5. CTA בסוף: "שתפו עם מי שצריך לשמוע את זה" או שאלה שמזמינה תגובות

טון: חם, אישי, לא יבש. כאילו מדבר עם חבר.
כתוב בפסקאות קצרות לקריאות.
אל תוסיף hashtags.""", max_tokens=900, vary=vary)


# ══════════════════════════════════════════════════════════════
# INSTAGRAM — carousel + story
# ══════════════════════════════════════════════════════════════

def generate_instagram_carousel(market_data: dict, vary: bool = False) -> str:
    """Returns JSON string with carousel slides."""
    topic = random.choice(WEEKLY_TOPICS) if vary else _week_topic()
    market_text = format_market_for_prompt(market_data)
    today = _now_fn().strftime("%d/%m/%Y")

    raw = _call(f"""צור קרוסלה לאינסטגרם בנושא השקעות לקהל חרדי.
נושא השבוע: {topic}
{market_text}
תאריך: {today}

צור 7 שקופיות. החזר JSON בלבד ללא הסברים:
{{
  "topic": "נושא הקרוסלה",
  "slides": [
    {{
      "num": 1,
      "type": "hook",
      "headline": "שורה אחת מושכת תשומת לב – שאלה או טענה מפתיעה",
      "sub": "תת-כותרת קצרה שמסבירה"
    }},
    {{
      "num": 2,
      "type": "point",
      "emoji": "💡",
      "title": "נקודה 1 – כותרת קצרה",
      "body": "2-3 משפטים שמסבירים את הנקודה בפשטות"
    }},
    {{
      "num": 3,
      "type": "point",
      "emoji": "📊",
      "title": "נקודה 2",
      "body": "2-3 משפטים"
    }},
    {{
      "num": 4,
      "type": "point",
      "emoji": "⚠️",
      "title": "נקודה 3",
      "body": "2-3 משפטים"
    }},
    {{
      "num": 5,
      "type": "point",
      "emoji": "✅",
      "title": "נקודה 4",
      "body": "2-3 משפטים"
    }},
    {{
      "num": 6,
      "type": "summary",
      "headline": "הנקודה הכי חשובה לזכור",
      "body": "משפט אחד חזק שמסכם הכל"
    }},
    {{
      "num": 7,
      "type": "cta",
      "headline": "רוצה ללמוד עוד?",
      "action": "הצטרף לקבוצת הוואטסאפ שלנו – קישור בביו 👆"
    }}
  ]
}}""", max_tokens=1200)

    # Strip markdown fences if present
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0].strip()

    # Validate JSON
    json.loads(raw)
    return raw


def generate_instagram_story(market_data: dict, vary: bool = False) -> str:
    market_text = format_market_for_prompt(market_data)
    return _call(f"""כתוב טקסט לסטורי אינסטגרם על שוק ההון.
{market_text}

הסטורי צריך:
- שורה ראשונה: hook חזק/שאלה (מקסימום 6 מילים)
- 3-4 שורות קצרות עם ערך
- שורה אחרונה: CTA קצר ("הצטרף לקבוצה", "לינק בביו")
- שימוש ב-emojis בצורה אסתטית
- מקסימום 60 מילים סה"כ
- כתוב כך שיתאים לשקף אחד""", max_tokens=200, vary=vary)


# ══════════════════════════════════════════════════════════════
# MAIN — generate all
# ══════════════════════════════════════════════════════════════

def generate_all(market_data: dict, news: list) -> dict:
    return {
        "market_summary":       generate_market_summary(market_data),
        "investment_tip":       generate_investment_tip(),
        "news_analysis":        generate_news_analysis(news),
        "stock_of_week":        generate_stock_of_week(market_data),
        "investor_psychology":  generate_investor_psychology(),
        "weekly_events":        generate_weekly_events(),
        "facebook_post":        generate_facebook_post(market_data, news),
        "instagram_carousel":   generate_instagram_carousel(market_data),
        "instagram_story":      generate_instagram_story(market_data),
    }
