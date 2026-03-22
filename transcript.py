"""
transcript.py — YouTube transcript and video info extraction.
Supports Mongolian Cyrillic and other languages.
Compatible with youtube-transcript-api >= 1.0.
"""

import re
import requests
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from any YouTube URL format."""
    url = url.strip()
    parsed = urlparse(url)

    if parsed.hostname in ("youtu.be",):
        return parsed.path[1:].split("?")[0]

    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/")[2]
        if parsed.path.startswith("/v/"):
            return parsed.path.split("/")[2]
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/")[2]

    # Last resort: look for ?v= or &v= in raw URL
    match = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)

    return None


def get_video_info(url: str) -> dict:
    """Get video title and author via YouTube oEmbed (no API key needed)."""
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
    try:
        response = requests.get(oembed_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "title": data.get("title", "Untitled"),
            "author": data.get("author_name", ""),
        }
    except Exception as e:
        raise RuntimeError(f"Видео мэдээлэл авч чадсангүй: {e}")


def get_transcript(url: str) -> str:
    """
    Extract full transcript text from a YouTube video.
    Tries Mongolian first, then falls back to any available transcript.
    Compatible with youtube-transcript-api >= 1.0 (instance-based API).
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"YouTube URL буруу байна: {url}")

    ytt = YouTubeTranscriptApi()

    try:
        transcript_list = ytt.list(video_id)
    except TranscriptsDisabled:
        raise RuntimeError("Энэ видеод хаалттай тайлбар (transcript) байна.")
    except Exception as e:
        raise RuntimeError(f"Транскрипт жагсаалт авч чадсангүй: {e}")

    # Priority order: Mongolian manual → Mongolian auto → any manual → any auto
    transcript = None
    for lang_codes in [["mn"], None]:
        for manual_only in [True, False]:
            try:
                if lang_codes:
                    if manual_only:
                        transcript = transcript_list.find_manually_created_transcript(lang_codes)
                    else:
                        transcript = transcript_list.find_generated_transcript(lang_codes)
                else:
                    for t in transcript_list:
                        if manual_only and t.is_generated:
                            continue
                        transcript = t
                        break
                if transcript:
                    break
            except (NoTranscriptFound, Exception):
                continue
        if transcript:
            break

    if not transcript:
        raise RuntimeError("Ямар ч транскрипт олдсонгүй.")

    fetched = transcript.fetch()
    # In v1.x, FetchedTranscript is iterable yielding FetchedTranscriptSnippet objects
    # Each snippet has a .text attribute (and also supports dict-style access)
    parts = []
    for snippet in fetched:
        text = snippet.text if hasattr(snippet, "text") else snippet["text"]
        parts.append(text)

    full_text = " ".join(parts)
    full_text = re.sub(r"\s+", " ", full_text).strip()
    return full_text
