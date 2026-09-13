import io
from pathlib import Path
from typing import List, Optional
from PIL import Image
import ebooklib
from ebooklib import epub
from .models import Novel, Chapter
from .cleaner import clean_chapter_html

EPUB_CSS = """
@namespace epub "http://www.idpf.org/2007/ops";

body {
    font-family: "Merriweather", "Lora", "Georgia", "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.65;
    margin: 5% 5%;
    padding: 0;
    text-align: justify;
}

h1, h2, h3 {
    font-family: "Helvetica Neue", Arial, sans-serif;
    text-align: center;
    font-weight: bold;
    margin-top: 1.5em;
    margin-bottom: 1.2em;
    line-height: 1.3;
}

a {
    color: #4f46e5;
    text-decoration: none;
}

p {
    text-indent: 1.5em;
    margin-top: 0;
    margin-bottom: 0.6em;
}

.chapter-title {
    font-size: 1.4em;
    border-bottom: 1px solid #ddd;
    padding-bottom: 0.4em;
    margin-bottom: 1.5em;
}

.intro-box {
    border: 1px solid #ccc;
    padding: 15px;
    margin: 20px 0;
    border-radius: 5px;
    background-color: rgba(128, 128, 128, 0.05);
}

.toc-page {
    margin: 2em 0;
}

.toc-title {
    font-size: 1.5em;
    text-align: center;
    margin-bottom: 1em;
    border-bottom: 2px solid #4f46e5;
    padding-bottom: 0.3em;
}

.toc-list {
    list-style-type: none;
    padding-left: 0;
}

.toc-item {
    margin-bottom: 0.6em;
    padding-bottom: 0.2em;
    border-bottom: 1px dashed rgba(128, 128, 128, 0.2);
}

.toc-item a {
    display: block;
    color: inherit;
}

.back-to-toc {
    display: block;
    text-align: right;
    font-size: 0.85em;
    color: #6366f1;
    margin-bottom: 1em;
}
"""

class EpubBuilder:
    def __init__(self, novel: Novel, cover_bytes: Optional[bytes] = None):
        self.novel = novel
        self.cover_bytes = self._normalize_cover(cover_bytes)

    @staticmethod
    def _normalize_cover(cover_bytes: Optional[bytes]) -> Optional[bytes]:
        if not cover_bytes:
            return None
        try:
            img = Image.open(io.BytesIO(cover_bytes))
            out = io.BytesIO()
            img.convert("RGB").save(out, format="JPEG", quality=92)
            return out.getvalue()
        except Exception:
            return cover_bytes

    def build(self, chapters: List[Chapter], output_path: Path, volume_title: Optional[str] = None, only_numbered_titles: bool = False) -> Path:
        book = epub.EpubBook()
        
        identifier = f"novelturk-{self.novel.slug}"
        if volume_title:
            identifier += f"-{volume_title.lower().replace(' ', '-')}"
            full_title = f"{self.novel.title} – {volume_title}"
        else:
            full_title = self.novel.title

        book.set_identifier(identifier)
        book.set_title(full_title)
        book.set_language("tr")
        book.add_author(self.novel.author or "Bilinmiyor")

        if self.novel.description:
            book.add_metadata("DC", "description", self.novel.description)

        if self.cover_bytes:
            book.set_cover("cover.jpg", self.cover_bytes)

        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/main.css",
            media_type="text/css",
            content=EPUB_CSS
        )
        book.add_item(nav_css)

        # 1. Giriş Sayfası
        intro_content = f"""
        <h1>{self.novel.title}</h1>
        {f'<h3>{volume_title}</h3>' if volume_title else ''}
        <div class="intro-box">
            <p><strong>Yazar:</strong> {self.novel.author}</p>
            <p><strong>Kaynak:</strong> Novel Türk</p>
            <p><strong>Bölüm Sayısı:</strong> {len(chapters)}</p>
        </div>
        """
        if self.novel.description:
            intro_content += f"<h3>Tanıtım</h3><p>{self.novel.description.replace(chr(10), '<br/>')}</p>"

        intro_page = epub.EpubHtml(
            title="Kapak ve Tanıtım",
            file_name="intro.xhtml",
            lang="tr"
        )
        intro_page.content = intro_content
        intro_page.add_item(nav_css)
        book.add_item(intro_page)

        # 2. Etkileşimli Görsel İçindekiler Sayfası (Tıklanabilir Liste)
        toc_items_html = []
        for idx, ch in enumerate(chapters, start=1):
            disp_title = f"Bölüm {ch.order_index}" if only_numbered_titles else ch.title
            file_name = f"chap_{idx:04d}.xhtml"
            toc_items_html.append(f'<li class="toc-item"><a href="{file_name}">{disp_title}</a></li>')

        toc_page_content = f"""
        <div class="toc-page" id="toc">
            <h2 class="toc-title">İçindekiler</h2>
            <ul class="toc-list">
                {"".join(toc_items_html)}
            </ul>
        </div>
        """
        toc_page = epub.EpubHtml(
            title="İçindekiler",
            file_name="toc_page.xhtml",
            lang="tr"
        )
        toc_page.content = toc_page_content
        toc_page.add_item(nav_css)
        book.add_item(toc_page)

        # 3. Bölümleri Ekle
        spine = ["nav", intro_page, toc_page]
        toc = [intro_page, toc_page]

        for idx, ch in enumerate(chapters, start=1):
            file_name = f"chap_{idx:04d}.xhtml"
            disp_title = f"Bölüm {ch.order_index}" if only_numbered_titles else ch.title
            clean_html = clean_chapter_html(ch.content_html or "", disp_title)
            
            chapter_doc = f"""
            <a href="toc_page.xhtml" class="back-to-toc">↑ İçindekiler</a>
            <h2 class="chapter-title">{disp_title}</h2>
            {clean_html}
            """

            epub_ch = epub.EpubHtml(
                title=disp_title,
                file_name=file_name,
                lang="tr"
            )
            epub_ch.content = chapter_doc
            epub_ch.add_item(nav_css)
            book.add_item(epub_ch)
            
            spine.append(epub_ch)
            toc.append(epub_ch)

        book.toc = toc
        book.spine = spine

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        output_path.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(output_path), book, {})
        return output_path
