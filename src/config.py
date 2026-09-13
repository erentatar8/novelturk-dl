import sys
import os
from pathlib import Path

# PyInstaller frozen bundle support
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BUNDLE_DIR = Path(sys._MEIPASS)
    # Binary'nin çalıştığı gerçek dizin veya Kullanıcı Belgeleri
    BASE_DIR = Path(sys.executable).parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent.parent
    BASE_DIR = BUNDLE_DIR

# İndirilen dosyalar için kullanıcıya açık downloads klasörü
if getattr(sys, 'frozen', False):
    DOWNLOADS_DIR = Path.home() / "Downloads" / "novelturk-dl"
else:
    DOWNLOADS_DIR = BASE_DIR / "downloads"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

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
