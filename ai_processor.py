"""
ai_processor.py — Uses Claude API to generate Mongolian social media content
from a YouTube transcript. Produces 6 carousel slides + captions.
"""

import json
import re
import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Та Lambda компанийн нийгмийн мэдээллийн сүлжээний контент менежер байна.
Lambda нь Монголын технологийн компани бөгөөд ажил хайгчдыг компаниудтай холбодог.
Вебсайт: https://www.lambda.global

Танд YouTube видеоны транскрипт өгнө. Та үүнийг Instagram болон Facebook зурган цуврал (carousel) нийтлэлд тохируулан монгол хэлээр агуулга үүсгэнэ үү.

ЧУХАЛ ДҮРЭМ:
- Бүх текст МОНГОЛ КИРИЛЛ үсгээр байна
- Хэл нь хялбар, ойлгомжтой, мэргэжлийн байна
- Lambda брэндийн дүр төрхийг хадгалах
- Зурагт товч, цэгцтэй текст ашиглах
"""

USER_TEMPLATE = """Дараах YouTube видеоны транскриптийг уншаад монгол хэлээр carousel нийтлэл үүсгэнэ үү.

Видеоны нэр: {title}

Транскрипт:
{transcript}

---

Дараах JSON форматаар хариулна уу (өөр юм бичихгүй, зөвхөн JSON):

{{
  "slides": [
    {{
      "type": "cover",
      "title": "Анхаарал татахуйц товч гарчиг (монголоор, 8-12 үг)",
      "subtitle": "Видеоны сэдвийн тайлбар (4-6 үг)"
    }},
    {{
      "type": "point",
      "label": "Гол санаа #1",
      "text": "Видеоноос гол санаа 1 (2-3 өгүүлбэр, монголоор)"
    }},
    {{
      "type": "point",
      "label": "Гол санаа #2",
      "text": "Видеоноос гол санаа 2 (2-3 өгүүлбэр, монголоор)"
    }},
    {{
      "type": "point",
      "label": "Гол санаа #3",
      "text": "Видеоноос гол санаа 3 (2-3 өгүүлбэр, монголоор)"
    }},
    {{
      "type": "point",
      "label": "Гол санаа #4",
      "text": "Видеоноос гол санаа 4 (2-3 өгүүлбэр, монголоор)"
    }},
    {{
      "type": "cta",
      "text": "Уриалга: Ажил хайж байна уу? Lambda.global-д бүртгүүлж, мөрөөдлийн ажлаа ол! (2-3 өгүүлбэр)"
    }}
  ],
  "instagram_caption": "Бүтэн Instagram caption монголоор. Видеоны гол санааг товч дүгнэж, Lambda-г дурдана. #hashtag1 #hashtag2 (5-7 хэштэг монголоор болон англиар)",
  "facebook_caption": "Бүтэн Facebook caption монголоор. Instagram-аас арай урт, дэлгэрэнгүй. Lambda болон www.lambda.global-г дурдана.",
  "image_prompt": "Professional dark minimal technology background for social media carousel, dark gradient from charcoal to deep navy, subtle teal geometric accents, clean modern corporate design, no text no people, abstract professional, suitable for Instagram 1080x1080"
}}
"""


def _extract_json(text: str) -> dict:
    """Extract and parse JSON from Claude's response."""
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(text.strip())


def generate_post_content(transcript: str, title: str) -> dict:
    """
    Send transcript to Claude and get structured carousel content back.
    Returns a dict with 'slides', 'instagram_caption', 'facebook_caption', 'image_prompt'.
    """
    client = anthropic.Anthropic()

    # Truncate very long transcripts to ~12k chars to stay within token limits
    max_chars = 12000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "..."

    user_message = USER_TEMPLATE.format(
        title=title,
        transcript=transcript,
    )

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = message.content[0].text

    try:
        content = _extract_json(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude-аас JSON задлах алдаа: {e}\n\nХариулт:\n{raw[:500]}")

    # Validate structure
    if "slides" not in content or len(content["slides"]) != 6:
        raise RuntimeError(f"Claude 6 слайд буцаасангүй. Слайдын тоо: {len(content.get('slides', []))}")

    return content
