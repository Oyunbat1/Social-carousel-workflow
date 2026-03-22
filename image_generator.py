"""
image_generator.py — Generates branded carousel slides using:
  1. Replicate (black-forest-labs/flux-schnell) for the background image
  2. Pillow to compose each of 6 slides with Mongolian text + Lambda branding

Brand colors:
  - Dark background: #0A0F19
  - White text:      #FFFFFF
  - Teal accent:     #00C896
  - Muted gray:      #A0A8B8
"""

import io
import os
import textwrap
from pathlib import Path

import replicate
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Brand palette ─────────────────────────────────────────────────────────────
DARK_BG   = (10,  15,  25)
WHITE     = (255, 255, 255)
TEAL      = (0,   200, 150)
GRAY      = (160, 168, 184)
OVERLAY_A = 185          # alpha for dark overlay (0-255)

SLIDE_W, SLIDE_H = 1080, 1080
LOGO_W = 210             # logo width in pixels
PADDING = 60


# ── Font management ───────────────────────────────────────────────────────────

FONT_URLS = {
    "bold":    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Bold.ttf",
    "regular": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf",
}

def _ensure_fonts() -> dict[str, Path]:
    """Download Noto Sans (Cyrillic-capable) if not already cached."""
    font_dir = Path("fonts")
    font_dir.mkdir(exist_ok=True)
    paths = {}
    for weight, url in FONT_URLS.items():
        dest = font_dir / f"NotoSans-{weight.capitalize()}.ttf"
        if not dest.exists():
            print(f"   Фонт татаж байна ({weight})…")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            dest.write_bytes(r.content)
        paths[weight] = dest
    return paths


def _font(paths: dict, weight: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(paths[weight]), size)


# ── Text helpers ──────────────────────────────────────────────────────────────

def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []

    for word in words:
        trial = " ".join(current + [word])
        w = draw.textlength(trial, font=font)
        if w <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines or [""]


def _draw_text_block(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    color: tuple,
    center_x: int,
    start_y: int,
    line_gap: int = 14,
) -> int:
    """Draw centered multiline text, return bottom y."""
    y = start_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((center_x - w // 2, y), line, fill=color, font=font)
        y += h + line_gap
    return y


# ── Background from Replicate ─────────────────────────────────────────────────

def _generate_background(image_prompt: str) -> Image.Image:
    """Run Replicate flux-schnell and return a PIL Image."""
    output = replicate.run(
        "black-forest-labs/flux-schnell",
        input={
            "prompt": image_prompt,
            "aspect_ratio": "1:1",
            "num_outputs": 1,
            "output_format": "png",
            "go_fast": True,
        },
    )

    # SDK >= 0.34 returns FileOutput objects; convert to URL string
    item = output[0]
    url = str(item)

    r = requests.get(url, timeout=60)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    return img.resize((SLIDE_W, SLIDE_H), Image.LANCZOS)


def _dark_bg_image() -> Image.Image:
    """Fallback: solid dark background if Replicate fails."""
    img = Image.new("RGBA", (SLIDE_W, SLIDE_H), (*DARK_BG, 255))
    return img


def _apply_overlay(bg: Image.Image) -> Image.Image:
    """Composite a semi-transparent dark overlay over the background."""
    bg = bg.convert("RGBA")
    overlay = Image.new("RGBA", (SLIDE_W, SLIDE_H), (*DARK_BG, OVERLAY_A))
    return Image.alpha_composite(bg, overlay).convert("RGB")


# ── Logo ──────────────────────────────────────────────────────────────────────

def _load_logo() -> Image.Image | None:
    logo_path = Path("brand/Lambda-logo-white.png")
    if not logo_path.exists():
        return None
    logo = Image.open(logo_path).convert("RGBA")
    ratio = LOGO_W / logo.width
    new_h = int(logo.height * ratio)
    return logo.resize((LOGO_W, new_h), Image.LANCZOS)


# ── Teal decorative elements ──────────────────────────────────────────────────

def _draw_teal_bar(draw: ImageDraw.ImageDraw, y: int, full: bool = False):
    """Draw a horizontal teal accent bar."""
    if full:
        draw.rectangle([PADDING, y, SLIDE_W - PADDING, y + 4], fill=TEAL)
    else:
        draw.rectangle([PADDING, y, PADDING + 120, y + 4], fill=TEAL)


# ── Slide composers ───────────────────────────────────────────────────────────

def _compose_cover(base: Image.Image, slide: dict, fonts: dict, logo: Image.Image | None, slide_num: int, total: int) -> Image.Image:
    img = base.copy()
    draw = ImageDraw.Draw(img)
    cx = SLIDE_W // 2

    # Logo top-left
    if logo:
        img.paste(logo, (PADDING, PADDING), logo)

    # Slide counter top-right
    draw.text((SLIDE_W - PADDING, PADDING + 10), f"{slide_num}/{total}",
              fill=GRAY, font=_font(fonts, "regular", 30), anchor="rt")

    # Teal bar below logo
    logo_h = logo.height if logo else 50
    _draw_teal_bar(draw, PADDING + logo_h + 20)

    # Main title (large, centered, lower half)
    title_font = _font(fonts, "bold", 68)
    lines = _wrap(slide.get("title", ""), title_font, SLIDE_W - PADDING * 2, draw)
    title_bottom = _draw_text_block(draw, lines, title_font, WHITE, cx, 380, line_gap=18)

    # Subtitle
    if slide.get("subtitle"):
        sub_font = _font(fonts, "regular", 38)
        sub_lines = _wrap(slide["subtitle"], sub_font, SLIDE_W - PADDING * 2, draw)
        _draw_text_block(draw, sub_lines, sub_font, GRAY, cx, title_bottom + 30)

    # Bottom teal full-width bar
    _draw_teal_bar(draw, SLIDE_H - PADDING - 4, full=True)

    # Website footer
    draw.text((cx, SLIDE_H - PADDING + 12), "www.lambda.global",
              fill=GRAY, font=_font(fonts, "regular", 26), anchor="mt")

    return img


def _compose_point(base: Image.Image, slide: dict, fonts: dict, logo: Image.Image | None, slide_num: int, total: int) -> Image.Image:
    img = base.copy()
    draw = ImageDraw.Draw(img)
    cx = SLIDE_W // 2

    # Logo top-left
    if logo:
        img.paste(logo, (PADDING, PADDING), logo)

    # Slide counter top-right
    draw.text((SLIDE_W - PADDING, PADDING + 10), f"{slide_num}/{total}",
              fill=GRAY, font=_font(fonts, "regular", 30), anchor="rt")

    # Teal label badge (e.g. "Гол санаа #1")
    label = slide.get("label", f"Гол санаа #{slide_num - 1}")
    label_font = _font(fonts, "bold", 30)
    lw = draw.textlength(label, font=label_font)
    badge_pad = 16
    badge_x = cx - lw // 2 - badge_pad
    badge_y = 220
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + lw + badge_pad * 2, badge_y + 52],
        radius=26, fill=TEAL,
    )
    draw.text((cx, badge_y + 10), label, fill=DARK_BG, font=label_font, anchor="mt")

    # Main point text
    body_font = _font(fonts, "bold", 48)
    text = slide.get("text", "")
    lines = _wrap(text, body_font, SLIDE_W - PADDING * 2, draw)
    _draw_text_block(draw, lines, body_font, WHITE, cx, 320, line_gap=20)

    # Footer
    draw.text((cx, SLIDE_H - PADDING + 12), "lambda.global",
              fill=GRAY, font=_font(fonts, "regular", 26), anchor="mt")

    return img


def _compose_cta(base: Image.Image, slide: dict, fonts: dict, logo: Image.Image | None, slide_num: int, total: int) -> Image.Image:
    img = base.copy()
    draw = ImageDraw.Draw(img)
    cx = SLIDE_W // 2

    # Logo top-left
    if logo:
        img.paste(logo, (PADDING, PADDING), logo)

    # Slide counter top-right
    draw.text((SLIDE_W - PADDING, PADDING + 10), f"{slide_num}/{total}",
              fill=GRAY, font=_font(fonts, "regular", 30), anchor="rt")

    # Full-width teal top bar
    logo_h = logo.height if logo else 50
    _draw_teal_bar(draw, PADDING + logo_h + 20, full=True)

    # CTA text centered
    cta_font = _font(fonts, "bold", 50)
    text = slide.get("text", "Lambda.global-д нэгдэж, мөрөөдлийн ажлаа ол!")
    lines = _wrap(text, cta_font, SLIDE_W - PADDING * 2, draw)
    bottom = _draw_text_block(draw, lines, cta_font, WHITE, cx, 360, line_gap=20)

    # Prominent website URL
    url_font = _font(fonts, "bold", 56)
    draw.text((cx, bottom + 60), "www.lambda.global", fill=TEAL, font=url_font, anchor="mt")

    return img


# ── Main entry point ──────────────────────────────────────────────────────────

COMPOSERS = {
    "cover": _compose_cover,
    "point": _compose_point,
    "cta":   _compose_cta,
}


def generate_carousel(content: dict, output_dir: Path) -> None:
    """
    Generate 6 carousel slide images and save them to output_dir.
    content: dict returned by ai_processor.generate_post_content()
    """
    slides = content["slides"]
    image_prompt = content.get("image_prompt", "professional dark minimal technology background, teal accents, no text, abstract corporate")

    # 1. Ensure fonts
    print("   Фонт бэлдэж байна…")
    fonts = _ensure_fonts()

    # 2. Load logo
    logo = _load_logo()

    # 3. Generate background from Replicate
    print("   Дэвсгэр зураг үүсгэж байна (Replicate)…")
    try:
        raw_bg = _generate_background(image_prompt)
    except Exception as e:
        print(f"   ⚠️  Replicate алдаа ({e}) — хар дэвсгэр ашиглана.")
        raw_bg = _dark_bg_image()

    # Apply dark overlay once; reuse for all slides
    base = _apply_overlay(raw_bg)

    # 4. Compose each slide
    total = len(slides)
    for i, slide in enumerate(slides, start=1):
        slide_type = slide.get("type", "point")
        composer = COMPOSERS.get(slide_type, _compose_point)

        print(f"   Слайд {i}/{total} үүсгэж байна…")
        slide_img = composer(base, slide, fonts, logo, i, total)

        out_path = output_dir / f"slide_{i:02d}.png"
        slide_img.save(str(out_path), "PNG")

    print(f"   ✅ {total} слайд хадгалагдлаа → {output_dir}/")
