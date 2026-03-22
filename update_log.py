"""
update_log.py — Add live Instagram/Facebook URLs to posts_log.json
after manually uploading carousel slides.

Usage:
    python update_log.py
"""

from dotenv import load_dotenv
from logger import update_post_url

if __name__ == "__main__":
    load_dotenv()
    update_post_url()
