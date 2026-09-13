import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

BASE_URL = "https://novelturk.com"
AJAX_URL = f"{BASE_URL}/wp-admin/admin-ajax.php"
REST_CHAPTER_URL = f"{BASE_URL}/wp-json/wp/v2/chapter"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Nazik indirme hızı (saniye cinsinden istek arası bekleme)
DEFAULT_DELAY = 0.25
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3
