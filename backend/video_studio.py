import anthropic
import json
from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Nano Banana 2 prompt engineering rules (from nano_banana_2_agent.md) ──────
_NB2_RULES = """
NANO BANANA 2 PROMPT RULES:
- Write in English only, narrative prose (NOT comma-separated keywords)
- 80–150 words per prompt, dense and cinematic
- Subject and main action FIRST (model weights opening phrase most)
- Include all 6 layers:
  1. Subject — physical detail, wardrobe, expression
  2. Action — movement or posture
  3. Location — specific setting with environmental texture
  4. Camera — shot type, angle, lens, aperture (use real equipment names)
  5. Lighting — direction, quality, color temperature (Kelvin), sources
  6. Style — film stock OR art movement + color grade + grain/texture
- Use two-word descriptors: "soft golden light" not "golden"
- Physical specificity: "steam catching backlight" not "misty"
- Real camera/lens names trigger precise behavior: Arri Alexa, Sony Venice, Kodak Portra
"""

# ── Channel visual identity ────────────────────────────────────────────────────
_CHANNEL_IDENTITY = """
CHANNEL: "לצאת מהגלות הפיננסית" (Getting Out of Financial Exile) — Israeli Jewish financial education.

TWO SCENE ARCHETYPES:

BIBLICAL / ANCIENT ISRAEL:
- Warm amber-gold tones, 2800-3200K
- Settings: Sinai desert, ancient Jerusalem, tribal camps, the Tabernacle, Temple Mount
- Figures: robed priests, prophets, warriors, Israelites in ancient garb
- Lighting: volumetric sun rays through desert dust, divine golden shafts
- Film: Kodak Portra 800 pushed, warm teal-orange grade

FINANCIAL / MODERN:
- Dark moody palette, charcoal silver, 2700K practicals
- Settings: corridors of stacked cash, foggy financial district, spotlit offices
- Main character: a religious Jewish man, full dark beard, kippah, round wire-frame glasses, dark charcoal suit, white shirt — usually seen from behind, back to camera, facing the light
- Lighting: single overhead spotlight, deep shadow fill, fog, motivated practicals
- Film: Kodak Vision3 500T, bleach bypass grade, desaturated silver retention

FORMAT: Always portrait 9:16 (1080×1920). Never include Hebrew text in the image.
"""

_SYSTEM = _NB2_RULES + "\n" + _CHANNEL_IDENTITY

_USER_TEMPLATE = """You are analyzing a Hebrew video script to create cinematic image prompts.

SCRIPT:
{script}

Create exactly {num_scenes} scene prompts.

For each scene:
- Identify the core CONCEPT of that script segment
- Biblical/Torah themes → BIBLICAL archetype
- Financial/money themes → FINANCIAL archetype
- Mixed → blend both creatively

Return ONLY valid JSON (no markdown, no explanation):
{{
  "scenes": [
    {{
      "scene_number": 1,
      "hebrew_text": "the Hebrew excerpt this scene represents",
      "english_prompt": "80-150 word narrative prose prompt following all 6 layers"
    }}
  ]
}}"""


def generate_scene_prompts(script: str, num_scenes: int = 15) -> list[dict]:
    user_msg = _USER_TEMPLATE.format(script=script, num_scenes=num_scenes)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=[{
            "type": "text",
            "text": _SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0].strip()

    data = json.loads(raw)
    return data["scenes"]
