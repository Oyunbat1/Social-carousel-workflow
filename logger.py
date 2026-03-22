"""
logger.py — Maintains a running JSON log of all generated posts.
Live URLs are added manually via update_log.py after uploading.
"""

import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("posts_log.json")


def _load_log() -> list:
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_log(entries: list) -> None:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def log_post(url: str, title: str, output_folder: str, content: dict) -> None:
    """Append a new post entry to posts_log.json."""
    entries = _load_log()

    entry = {
        "id": len(entries) + 1,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "video_url": url,
        "video_title": title,
        "output_folder": output_folder,
        "slides": [f"slide_{i:02d}.png" for i in range(1, 7)],
        "instagram_caption_preview": content.get("instagram_caption", "")[:120] + "…",
        "facebook_caption_preview": content.get("facebook_caption", "")[:120] + "…",
        "instagram_post_url": "",
        "facebook_post_url": "",
        "status": "generated",   # generated → published
    }

    entries.append(entry)
    _save_log(entries)
    print(f"   📒 Лог бичигдлээ (нийт {len(entries)} нийтлэл).")


def update_post_url() -> None:
    """Interactive CLI to add live URLs after manual upload."""
    entries = _load_log()
    if not entries:
        print("Лог хоосон байна.")
        return

    print("\n📒 Нийтлэлийн лог:")
    print("-" * 60)
    for e in entries:
        ig  = e.get("instagram_post_url") or "(байхгүй)"
        fb  = e.get("facebook_post_url")  or "(байхгүй)"
        print(f"[{e['id']}] {e['date']} — {e['video_title'][:40]}")
        print(f"     Instagram: {ig}")
        print(f"     Facebook:  {fb}")
        print(f"     Статус:    {e.get('status', '?')}")
    print("-" * 60)

    try:
        idx = int(input("\nШинэчлэх нийтлэлийн ID оруулна уу: ").strip())
    except ValueError:
        print("Буруу оролт.")
        return

    entry = next((e for e in entries if e["id"] == idx), None)
    if not entry:
        print(f"ID {idx} олдсонгүй.")
        return

    ig_url = input("Instagram нийтлэлийн URL (хоосон үлдээвэл өөрчлөгдөхгүй): ").strip()
    fb_url = input("Facebook нийтлэлийн URL  (хоосон үлдээвэл өөрчлөгдөхгүй): ").strip()

    if ig_url:
        entry["instagram_post_url"] = ig_url
    if fb_url:
        entry["facebook_post_url"] = fb_url
    if ig_url or fb_url:
        entry["status"] = "published"
        entry["published_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    _save_log(entries)
    print("✅ Лог шинэчлэгдлээ.")
