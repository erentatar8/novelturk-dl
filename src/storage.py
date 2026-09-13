import sqlite3
import threading
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from .models import Novel, Chapter
from .config import DOWNLOADS_DIR

class Storage:
    def __init__(self, novel_slug: str):
        self.novel_slug = novel_slug
        self.db_path = DOWNLOADS_DIR / f"{novel_slug}.db"
        self._lock = threading.Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=45.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Çoklu thread eşzamanlılığı için WAL modu ve performans ayarları
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 45000;")
        return conn

    def _init_db(self):
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS novel_meta (
                        slug TEXT PRIMARY KEY,
                        novel_id TEXT,
                        title TEXT,
                        author TEXT,
                        description TEXT,
                        cover_url TEXT,
                        total_chapters INTEGER DEFAULT 0,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chapters (
                        id INTEGER PRIMARY KEY,
                        novel_slug TEXT,
                        order_index INTEGER,
                        title TEXT,
                        url TEXT,
                        content_html TEXT,
                        is_downloaded INTEGER DEFAULT 0,
                        downloaded_at TIMESTAMP,
                        FOREIGN KEY(novel_slug) REFERENCES novel_meta(slug)
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_chap_order ON chapters(order_index)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_chap_down ON chapters(is_downloaded)")
                conn.commit()

    def save_novel_meta(self, novel: Novel):
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO novel_meta (slug, novel_id, title, author, description, cover_url, total_chapters)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                        novel_id=excluded.novel_id,
                        title=excluded.title,
                        author=excluded.author,
                        description=excluded.description,
                        cover_url=excluded.cover_url,
                        total_chapters=excluded.total_chapters,
                        updated_at=CURRENT_TIMESTAMP
                """, (
                    novel.slug, novel.novel_id, novel.title,
                    novel.author, novel.description, novel.cover_url,
                    novel.total_chapters
                ))
                conn.commit()

    def get_novel_meta(self) -> Optional[Novel]:
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM novel_meta WHERE slug = ?", (self.novel_slug,))
                row = cursor.fetchone()
                if not row:
                    return None
                return Novel(
                    slug=row["slug"],
                    title=row["title"],
                    novel_id=row["novel_id"],
                    author=row["author"],
                    description=row["description"],
                    cover_url=row["cover_url"],
                    total_chapters=row["total_chapters"]
                )

    def sync_chapters(self, chapters: List[Chapter]):
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                for ch in chapters:
                    cursor.execute("""
                        INSERT INTO chapters (id, novel_slug, order_index, title, url)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            order_index=excluded.order_index,
                            title=excluded.title,
                            url=excluded.url
                    """, (ch.id, ch.novel_slug, ch.order_index, ch.title, ch.url))
                conn.commit()

    def save_chapter_content(self, chapter_id: int, content_html: str):
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE chapters
                    SET content_html = ?, is_downloaded = 1, downloaded_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (content_html, chapter_id))
                conn.commit()

    def get_pending_chapters(self) -> List[Chapter]:
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM chapters
                    WHERE novel_slug = ? AND is_downloaded = 0
                    ORDER BY order_index ASC
                """, (self.novel_slug,))
                rows = cursor.fetchall()
                return [
                    Chapter(
                        id=r["id"],
                        novel_slug=r["novel_slug"],
                        order_index=r["order_index"],
                        title=r["title"],
                        url=r["url"],
                        content_html=r["content_html"],
                        is_downloaded=bool(r["is_downloaded"])
                    )
                    for r in rows
                ]

    def get_all_chapters(self, only_downloaded: bool = True) -> List[Chapter]:
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM chapters WHERE novel_slug = ?"
                if only_downloaded:
                    query += " AND is_downloaded = 1"
                query += " ORDER BY order_index ASC"
                cursor.execute(query, (self.novel_slug,))
                rows = cursor.fetchall()
                return [
                    Chapter(
                        id=r["id"],
                        novel_slug=r["novel_slug"],
                        order_index=r["order_index"],
                        title=r["title"],
                        url=r["url"],
                        content_html=r["content_html"],
                        is_downloaded=bool(r["is_downloaded"])
                    )
                    for r in rows
                ]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM chapters WHERE novel_slug = ?", (self.novel_slug,))
                total = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM chapters WHERE novel_slug = ? AND is_downloaded = 1", (self.novel_slug,))
                downloaded = cursor.fetchone()[0]
                return {
                    "total": total,
                    "downloaded": downloaded,
                    "remaining": total - downloaded,
                    "percent": (downloaded / total * 100) if total > 0 else 0
                }
