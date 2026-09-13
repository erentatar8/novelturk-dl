import re
import time
import threading
import requests
from bs4 import BeautifulSoup
from typing import Tuple, List, Optional, Dict, Any
from .models import Novel, Chapter
from .config import (
    BASE_URL, AJAX_URL, REST_CHAPTER_URL,
    DEFAULT_HEADERS, DEFAULT_DELAY, REQUEST_TIMEOUT, MAX_RETRIES
)

class NovelTurkClient:
    def __init__(self, delay: float = DEFAULT_DELAY):
        self.delay = delay
        self._local = threading.local()

    def _get_session(self) -> requests.Session:
        if not hasattr(self._local, "session"):
            s = requests.Session()
            s.headers.update(DEFAULT_HEADERS)
            self._local.session = s
        return self._local.session

    @staticmethod
    def extract_slug(url_or_slug: str) -> str:
        url_or_slug = url_or_slug.strip().strip("/")
        if "novel/" in url_or_slug:
            match = re.search(r"novel/([^/?#]+)", url_or_slug)
            if match:
                raw_slug = match.group(1)
            else:
                raw_slug = url_or_slug.split("/")[-1]
        else:
            raw_slug = url_or_slug.split("/")[-1]
        
        # Path traversal koruması: Sadece güvenli karakterleri tut
        sanitized = re.sub(r"[^a-zA-Z0-9_\-]", "", raw_slug)
        return sanitized or "novel"

    def _get(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        session = self._get_session()
        for attempt in range(MAX_RETRIES):
            try:
                resp = session.get(url, **kwargs)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in [429, 503]:
                    # Sunucu yoğun uyarısı - nazikçe bekle (exponential backoff)
                    wait_time = (attempt + 1) * 3
                    time.sleep(wait_time)
                else:
                    time.sleep(1 + attempt)
            except requests.RequestException:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(1 + attempt)
        raise requests.HTTPError(f"İstek başarısız oldu: {url}")

    def _post(self, url: str, data: Dict[str, Any], **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        session = self._get_session()
        for attempt in range(MAX_RETRIES):
            try:
                resp = session.post(url, data=data, **kwargs)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in [429, 503]:
                    wait_time = (attempt + 1) * 3
                    time.sleep(wait_time)
                else:
                    time.sleep(1 + attempt)
            except requests.RequestException:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(1 + attempt)
        raise requests.HTTPError(f"POST isteği başarısız oldu: {url}")

    def fetch_novel_info(self, slug: str) -> Tuple[Novel, str, List[str]]:
        url = f"{BASE_URL}/novel/{slug}/"
        resp = self._get(url)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        # 1. Nonce
        nonce_match = re.search(r'ntAjax\s*=\s*\{[^\}]*\"nonce\":\"([a-f0-9]+)\"', html)
        if not nonce_match:
            nonce_match = re.search(r'\"nonce\":\"([a-f0-9]+)\"', html)
        nonce = nonce_match.group(1) if nonce_match else ""

        # 2. Novel ID
        novel_id_input = soup.find("input", {"name": "nt_novel_id"})
        if novel_id_input and novel_id_input.get("value"):
            novel_id = novel_id_input["value"]
        else:
            id_match = re.search(r'/wp/v2/novel/(\d+)', html)
            novel_id = id_match.group(1) if id_match else ""

        # 3. Başlık
        title_el = soup.find("h1") or soup.find("title")
        title = title_el.get_text(strip=True) if title_el else slug
        title = re.sub(r"\s*Türkçe Novel Oku.*$", "", title)

        # 4. Yazar
        author = "Bilinmiyor"
        author_link = soup.find("a", href=re.compile(r"nauthor="))
        if author_link:
            author = author_link.get_text(strip=True)

        # 5. Özet
        desc_parts = []
        synopsis_div = soup.find(class_=re.compile(r"(synopsis|novel-description|entry-content)", re.I))
        if synopsis_div:
            for p in synopsis_div.find_all("p"):
                t = p.get_text(strip=True)
                if t and not t.startswith("Not:"):
                    desc_parts.append(t)
        description = "\n\n".join(desc_parts[:5])

        # 6. Kapak
        cover_url = None
        img_el = soup.find("meta", property="og:image")
        if img_el and img_el.get("content"):
            cover_url = img_el["content"]
        else:
            thumb = soup.find("div", class_=re.compile(r"thumb|cover|poster", re.I))
            if thumb and thumb.find("img"):
                cover_url = thumb.find("img").get("src")

        # 7. Gruplar
        groups = re.findall(r'data-group=\"([^\"]+)\"', html)
        if groups and "-" in groups[0]:
            try:
                def group_sort_key(g):
                    nums = [int(x) for x in g.split("-") if x.isdigit()]
                    return min(nums) if nums else 0
                groups = sorted(list(dict.fromkeys(groups)), key=group_sort_key)
            except Exception:
                groups = list(reversed(groups))

        novel = Novel(
            slug=slug,
            title=title,
            novel_id=novel_id,
            author=author,
            description=description,
            cover_url=cover_url
        )
        return novel, nonce, groups

    def fetch_all_chapters_list(self, novel_slug: str, novel_id: str, groups: List[str], nonce: str) -> List[Chapter]:
        raw_chapters = []

        for group in groups:
            payload = {
                "action": "nt_load_chapter_group",
                "novel_id": novel_id,
                "group": group,
                "nonce": nonce
            }
            resp = self._post(AJAX_URL, data=payload)
            data = resp.json()
            if not data.get("success"):
                continue

            html_chunk = data.get("data", {}).get("html", "")
            soup = BeautifulSoup(html_chunk, "html.parser")
            
            for a in soup.find_all("a", class_="eph-num"):
                chap_id = a.get("data-chapter-id")
                if not chap_id:
                    continue
                chap_id = int(chap_id)
                href = a.get("href", "")
                
                num_span = a.find("span", class_="ch-num-pill")
                sub_span = a.find("span", class_="ch-sub-title")
                
                num_text = num_span.get_text(strip=True) if num_span else ""
                sub_text = sub_span.get_text(strip=True) if sub_span else ""
                
                if num_text and sub_text:
                    full_title = f"{num_text} – {sub_text}"
                elif num_text:
                    full_title = num_text
                else:
                    full_title = a.get_text(" ", strip=True)

                raw_chapters.append({
                    "id": chap_id,
                    "title": full_title,
                    "url": href
                })
            
            time.sleep(self.delay)

        def extract_chapter_num(item):
            match = re.search(r"Bölüm\s*(\d+)", item["title"], re.I)
            if match:
                return int(match.group(1))
            match_slug = re.search(r"bolum-(\d+)", item["url"], re.I)
            if match_slug:
                return int(match_slug.group(1))
            return 0

        seen_ids = set()
        unique_chapters = []
        for item in raw_chapters:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                unique_chapters.append(item)

        unique_chapters.sort(key=extract_chapter_num)

        chapters = []
        for idx, item in enumerate(unique_chapters, start=1):
            chapters.append(Chapter(
                id=item["id"],
                novel_slug=novel_slug,
                order_index=idx,
                title=item["title"],
                url=item["url"]
            ))

        return chapters

    def fetch_chapter_content(self, chapter_id: int) -> Tuple[str, str]:
        if self.delay > 0:
            time.sleep(self.delay)
        url = f"{REST_CHAPTER_URL}/{chapter_id}"
        resp = self._get(url)
        data = resp.json()
        
        title = data.get("title", {}).get("rendered", "")
        content = data.get("content", {}).get("rendered", "")
        return title, content

    def download_image(self, url: str) -> Optional[bytes]:
        try:
            resp = self._get(url)
            return resp.content
        except Exception:
            return None
