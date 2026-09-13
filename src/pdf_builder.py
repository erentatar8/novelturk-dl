import base64
from pathlib import Path
from typing import List, Optional
from xhtml2pdf import pisa
from .models import Novel, Chapter
from .cleaner import clean_chapter_html
from .config import BUNDLE_DIR

FONT_PATH = (BUNDLE_DIR / "assets" / "fonts" / "BookFont.ttf").resolve()

PDF_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @font-face {
            font-family: 'BookFont';
            src: url('%%FONT_PATH%%');
        }
        @page {
            size: a5;
            margin: 1.5cm;
            @frame footer {
                -pdf-frame-content: footerContent;
                bottom: 0.5cm;
                margin-left: 1.5cm;
                margin-right: 1.5cm;
                height: 1cm;
            }
        }
        body {
            font-family: 'BookFont', sans-serif;
            font-size: 9.5pt;
            line-height: 1.6;
            color: #1a1a1a;
            text-align: justify;
        }
        a {
            color: #4f46e5;
            text-decoration: none;
        }
        .cover-page {
            text-align: center;
            margin-top: 2cm;
            page-break-after: always;
        }
        .cover-img {
            max-width: 80%;
            height: auto;
            border-radius: 4px;
        }
        .title-page {
            text-align: center;
            margin-top: 3cm;
            page-break-after: always;
        }
        .novel-title {
            font-size: 18pt;
            font-weight: bold;
            margin-bottom: 0.4cm;
            color: #111;
        }
        .volume-subtitle {
            font-size: 13pt;
            color: #4f46e5;
            margin-bottom: 0.8cm;
            font-weight: bold;
        }
        .meta-info {
            font-size: 9.5pt;
            color: #555;
            line-height: 1.8;
            margin-top: 1cm;
        }
        .toc-container {
            page-break-before: always;
            page-break-after: always;
        }
        .toc-title {
            font-size: 16pt;
            font-weight: bold;
            text-align: center;
            margin-bottom: 0.8cm;
            border-bottom: 1.5pt solid #4f46e5;
            padding-bottom: 0.3cm;
        }
        .toc-list {
            margin: 0;
            padding: 0;
        }
        .toc-item {
            margin-bottom: 0.35cm;
            font-size: 9pt;
            line-height: 1.4;
            border-bottom: 0.5pt dashed #e2e8f0;
            padding-bottom: 2px;
        }
        .toc-item a {
            color: #1e293b;
            display: block;
        }
        .chapter-container {
            page-break-before: always;
        }
        .chapter-header {
            margin-top: 0.5cm;
            margin-bottom: 0.8cm;
            border-bottom: 1pt solid #ddd;
            padding-bottom: 0.3cm;
            text-align: center;
        }
        .chapter-title {
            font-size: 13pt;
            font-weight: bold;
            color: #111;
            margin-bottom: 4px;
        }
        .back-to-toc {
            font-size: 8pt;
            color: #6366f1;
            text-align: right;
            display: block;
        }
        p {
            text-indent: 1.2em;
            margin-top: 0;
            margin-bottom: 0.45em;
        }
        #footerContent {
            text-align: right;
            font-size: 8pt;
            color: #888;
        }
    </style>
</head>
<body>
    <div id="footerContent">
        <pdf:pagenumber/>
    </div>

    %%COVER_SECTION%%
    
    <div class="title-page">
        <a name="top"></a>
        <div class="novel-title">%%NOVEL_TITLE%%</div>
        %%VOLUME_SECTION%%
        <div class="meta-info">
            <p><strong>Yazar:</strong> %%AUTHOR%%</p>
            <p><strong>Kaynak:</strong> Novel Türk</p>
            <p><strong>Bölüm Sayısı:</strong> %%CHAPTER_COUNT%%</p>
        </div>
    </div>

    <!-- Etkileşimli İçindekiler Tablosu -->
    <div class="toc-container">
        <a name="toc-top"></a>
        <div class="toc-title">İçindekiler</div>
        <div class="toc-list">
            %%TOC_ITEMS%%
        </div>
    </div>

    <!-- Bölümler -->
    %%CHAPTERS_CONTENT%%
</body>
</html>
"""

class PdfBuilder:
    def __init__(self, novel: Novel, cover_bytes: Optional[bytes] = None):
        self.novel = novel
        self.cover_bytes = cover_bytes

    def build(self, chapters: List[Chapter], output_path: Path, volume_title: Optional[str] = None, only_numbered_titles: bool = False) -> Path:
        cover_section = ""
        if self.cover_bytes:
            b64_cover = base64.b64encode(self.cover_bytes).decode("utf-8")
            cover_section = f'<div class="cover-page"><img class="cover-img" src="data:image/jpeg;base64,{b64_cover}"/></div>'

        vol_section = f'<div class="volume-subtitle">{volume_title}</div>' if volume_title else ''

        toc_items = []
        chaps_html = []

        for ch in chapters:
            disp_title = f"Bölüm {ch.order_index}" if only_numbered_titles else ch.title
            target_id = f"chap_{ch.order_index}"

            # Tıklanabilir link
            toc_items.append(f'<div class="toc-item"><a href="#{target_id}">{disp_title}</a></div>')

            # Bölüm gövdesi ve iç çapa
            clean_content = clean_chapter_html(ch.content_html or "", disp_title)
            chaps_html.append(f"""
            <div class="chapter-container">
                <a name="{target_id}"></a>
                <div class="chapter-header">
                    <div class="chapter-title">{disp_title}</div>
                    <a href="#toc-top" class="back-to-toc">↑ İçindekiler</a>
                </div>
                {clean_content}
            </div>
            """)

        full_html = (
            PDF_TEMPLATE
            .replace("%%FONT_PATH%%", str(FONT_PATH))
            .replace("%%COVER_SECTION%%", cover_section)
            .replace("%%NOVEL_TITLE%%", self.novel.title)
            .replace("%%VOLUME_SECTION%%", vol_section)
            .replace("%%AUTHOR%%", self.novel.author or "Bilinmiyor")
            .replace("%%CHAPTER_COUNT%%", str(len(chapters)))
            .replace("%%TOC_ITEMS%%", "\n".join(toc_items))
            .replace("%%CHAPTERS_CONTENT%%", "\n".join(chaps_html))
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            pisa_status = pisa.CreatePDF(full_html, dest=f, encoding="utf-8")

        if pisa_status.err:
            raise RuntimeError(f"PDF oluşturma sırasında hata oluştu (pisa error: {pisa_status.err})")

        return output_path
