"""
main.py — Lambda Social Media Manager CLI

Usage:
    python main.py                  # generate new post
    python main.py --update-url     # add live URLs to an existing log entry
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv


def _check_env():
    missing = []
    if not os.getenv("REPLICATE_API_TOKEN"):
        missing.append("REPLICATE_API_TOKEN")
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        print("❌ .env файлд дараах түлхүүрүүд байхгүй байна:")
        for key in missing:
            print(f"   • {key}")
        print("\n💡 .env.example файлыг .env болгон хуулж, API түлхүүрээ оруулна уу.")
        sys.exit(1)


def _sanitize(name: str) -> str:
    """Turn a video title into a safe folder name (keeps Cyrillic)."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name[:60] or "video"


def main():
    load_dotenv()

    if "--update-url" in sys.argv:
        from logger import update_post_url
        update_post_url()
        return

    _check_env()

    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   Lambda Social Media Manager  🇲🇳           ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    url = input("YouTube URL оруулна уу: ").strip()
    if not url:
        print("URL оруулаагүй байна.")
        sys.exit(1)

    # ── Step 1: Video info ────────────────────────────────────────────────────
    print("\n▶ Видео мэдээлэл авч байна…")
    from transcript import get_video_info, get_transcript
    try:
        info = get_video_info(url)
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    title = info["title"]
    author = info.get("author", "")
    print(f"  Гарчиг : {title}")
    if author:
        print(f"  Суваг  : {author}")

    # ── Step 2: Transcript ────────────────────────────────────────────────────
    print("\n▶ Транскрипт татаж байна…")
    try:
        transcript = get_transcript(url)
    except (RuntimeError, ValueError) as e:
        print(f"❌ {e}")
        sys.exit(1)

    word_count = len(transcript.split())
    print(f"  {word_count:,} үг олдлоо")

    # ── Step 3: Claude content generation ────────────────────────────────────
    print("\n▶ Агуулга үүсгэж байна (Claude)…")
    from ai_processor import generate_post_content
    try:
        content = generate_post_content(transcript, title)
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)
    print("  Агуулга амжилттай үүслээ ✓")

    # ── Step 4: Output folder ─────────────────────────────────────────────────
    folder_name = _sanitize(title)
    output_dir = Path("output") / folder_name
    # Avoid collisions: append counter if folder exists
    if output_dir.exists():
        i = 2
        while (Path("output") / f"{folder_name}_{i}").exists():
            i += 1
        output_dir = Path("output") / f"{folder_name}_{i}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 5: Carousel image generation ────────────────────────────────────
    print("\n▶ Carousel зургуудыг үүсгэж байна (Replicate + Pillow)…")
    from image_generator import generate_carousel
    try:
        generate_carousel(content, output_dir)
    except Exception as e:
        print(f"❌ Зураг үүсгэж чадсангүй: {e}")
        sys.exit(1)

    # ── Step 6: Save captions ─────────────────────────────────────────────────
    ig_path = output_dir / "instagram_caption.txt"
    fb_path = output_dir / "facebook_caption.txt"

    ig_path.write_text(content.get("instagram_caption", ""), encoding="utf-8")
    fb_path.write_text(content.get("facebook_caption", ""), encoding="utf-8")

    # ── Step 7: Log ───────────────────────────────────────────────────────────
    from logger import log_post
    log_post(url, title, str(output_dir), content)

    # ── Done ──────────────────────────────────────────────────────────────────
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║   ✅  Амжилттай дууслаа!                     ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"\n📁 Хавтас  : {output_dir}/")
    print(f"   📸 slide_01.png … slide_06.png  (carousel)")
    print(f"   📝 instagram_caption.txt")
    print(f"   📝 facebook_caption.txt")
    print()
    print("💡 Нийтэлсний дараа URL нэмэхийн тулд:")
    print("   python update_log.py")
    print()


if __name__ == "__main__":
    main()
