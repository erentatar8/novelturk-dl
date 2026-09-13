import os
import sys
import json
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import webview

from .config import DOWNLOADS_DIR
from .client import NovelTurkClient
from .storage import Storage
from .models import Novel, Chapter
from .epub_builder import EpubBuilder
from .pdf_builder import PdfBuilder

class WebApi:
    """
    Exposed to JavaScript window.pywebview.api.
    Provides methods to load novel details, select chapters, customize output,
    open file/directory pickers, and run parallel downloads / conversions.
    """
    def __init__(self):
        self._window: Optional[webview.Window] = None
        self.client = NovelTurkClient()
        self.current_novel: Optional[Novel] = None
        self.storage: Optional[Storage] = None
        self.all_chapters: List[Chapter] = []
        self._is_running = False
        self._cancel_requested = False
        self._worker_thread: Optional[threading.Thread] = None

    def set_window(self, window: webview.Window):
        self._window = window

    def _eval_js(self, js_code: str):
        if self._window:
            try:
                self._window.evaluate_js(js_code)
            except Exception as e:
                print(f"[WebApi] JS eval error: {e}", file=sys.stderr)

    def log(self, message: str, level: str = "info"):
        """Send log message to frontend terminal."""
        js_msg = json.dumps(str(message))
        js_lvl = json.dumps(str(level))
        self._eval_js(f"window.onLogReceived && window.onLogReceived({js_msg}, {js_lvl});")

    def update_progress(self, current: int, total: int, status_text: str):
        """Send progress bar update to frontend."""
        js_text = json.dumps(str(status_text))
        self._eval_js(f"window.onProgressUpdated && window.onProgressUpdated({int(current)}, {int(total)}, {js_text});")

    def update_chapter_status(self, ch_id: int, status: str):
        """Update single chapter status row in frontend."""
        js_status = json.dumps(str(status))
        self._eval_js(f"window.onChapterStatusUpdated && window.onChapterStatusUpdated({int(ch_id)}, {js_status});")

    def load_novel(self, url_or_slug: str) -> Dict[str, Any]:
        """Fetch novel info and chapter list using NovelTurkClient and Storage."""
        target = url_or_slug.strip()
        if not target:
            return {"success": False, "error": "Lütfen geçerli bir Novel URL'si veya slug girin."}

        try:
            slug = NovelTurkClient.extract_slug(target)
            self.log(f"🔎 Novel bilgileri getiriliyor: '{slug}'...")

            self.storage = Storage(slug)
            
            # 1. First check if cached novel exists in storage
            cached_novel = self.storage.get_novel_meta()
            cached_chapters = self.storage.get_all_chapters(only_downloaded=False)

            # If not cached or user refreshed, fetch from site
            if cached_novel and cached_chapters:
                novel = cached_novel
                self.log(f"⚡ Önbellekteki veriler yüklendi: {novel.title} ({len(cached_chapters)} bölüm)")
            else:
                novel, nonce, groups = self.client.fetch_novel_info(slug)
                self.log(f"📚 Bölüm fihristi taranıyor ({len(groups)} sekme)...")
                chapters = self.client.fetch_all_chapters_list(slug, novel.novel_id, groups, nonce)
                novel.total_chapters = len(chapters)
                self.storage.save_novel_meta(novel)
                self.storage.sync_chapters(chapters)
                cached_chapters = self.storage.get_all_chapters(only_downloaded=False)

            self.current_novel = novel
            self.all_chapters = cached_chapters
            stats = self.storage.get_stats()

            self.log(f"✓ Başarılı: {novel.title} ({len(self.all_chapters)} bölüm). Önbellek: {stats['downloaded']} indi.")

            return {
                "success": True,
                "novel": {
                    "id": novel.novel_id,
                    "title": novel.title,
                    "slug": novel.slug,
                    "author": novel.author or "Bilinmiyor",
                    "cover_url": novel.cover_url or "",
                    "description": novel.description or "",
                    "genres": getattr(novel, "genres", []) or [],
                    "total_chapters": len(self.all_chapters),
                    "downloaded_count": stats["downloaded"],
                    "percent": stats["percent"],
                    "default_output_dir": str(DOWNLOADS_DIR.resolve())
                },
                "chapters": [
                    {
                        "id": ch.id,
                        "order_index": ch.order_index,
                        "title": ch.title,
                        "is_downloaded": ch.is_downloaded
                    }
                    for ch in self.all_chapters
                ]
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log(f"❌ Novel yükleme hatası: {e}", "error")
            return {"success": False, "error": str(e)}

    def browse_custom_cover(self) -> Optional[str]:
        """Open native macOS file dialog to choose custom cover image."""
        if not self._window:
            return None
        file_types = ("Resim Dosyaları (*.png;*.jpg;*.jpeg;*.webp)", "Tüm Dosyalar (*.*)")
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=file_types
        )
        if result and len(result) > 0:
            return result[0]
        return None

    def get_image_data_uri(self, file_path: str) -> Optional[str]:
        """Convert local image file to base64 Data URI for immediate UI preview."""
        try:
            p = Path(file_path)
            if not p.exists() or not p.is_file():
                return None
            import base64
            import mimetypes
            mime_type, _ = mimetypes.guess_type(str(p))
            if not mime_type:
                mime_type = "image/jpeg"
            with open(p, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            return f"data:{mime_type};base64,{encoded}"
        except Exception as e:
            print(f"[WebApi] Error reading image data URI: {e}", file=sys.stderr)
            return None

    def browse_output_dir(self, current_dir: str = "") -> Optional[str]:
        """Open native macOS folder picker."""
        if not self._window:
            return None
        start_dir = current_dir if current_dir and Path(current_dir).exists() else str(DOWNLOADS_DIR)
        result = self._window.create_file_dialog(
            webview.FOLDER_DIALOG,
            directory=start_dir
        )
        if result and len(result) > 0:
            return result[0]
        return None

    def open_folder(self, path: str):
        """Open folder in system file manager (macOS Finder, Windows Explorer, Linux file manager)."""
        p = Path(path)
        if not p.exists():
            p = p.parent
        if p.exists():
            import subprocess
            import platform
            system = platform.system()
            if system == "Darwin":       # macOS
                subprocess.run(["open", str(p)])
            elif system == "Windows":     # Windows
                subprocess.run(["explorer", str(p)])
            else:                        # Linux / BSD
                subprocess.run(["xdg-open", str(p)])

    def stop_process(self):
        """Request worker thread to stop."""
        if self._is_running:
            self._cancel_requested = True
            self.log("⚠️ Durdurma isteği gönderildi, aktif parçacıklar durduruluyor...", "warning")

    def start_process(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Start parallel download and EPUB/PDF compilation in background thread."""
        if self._is_running:
            return {"success": False, "error": "Zaten devam eden bir işlem var."}
        if not self.current_novel or not self.all_chapters or not self.storage:
            return {"success": False, "error": "Önce bir novel yüklemelisiniz."}

        selected_ids = set(options.get("selected_chapter_ids", []))
        if not selected_ids:
            return {"success": False, "error": "Lütfen en az bir bölüm seçin."}

        build_epub = options.get("format_epub", True)
        build_pdf = options.get("format_pdf", False)
        if not build_epub and not build_pdf:
            return {"success": False, "error": "Lütfen en az bir çıktı formatı seçin (EPUB veya PDF)."}

        self._is_running = True
        self._cancel_requested = False

        self._worker_thread = threading.Thread(
            target=self._run_process_worker,
            args=(options, selected_ids),
            daemon=True
        )
        self._worker_thread.start()
        return {"success": True}

    def _run_process_worker(self, options: Dict[str, Any], selected_ids: set):
        try:
            selected_chapters = [ch for ch in self.all_chapters if ch.id in selected_ids]
            concurrency = int(options.get("concurrency", 4))
            total_selected = len(selected_chapters)

            self.log(f"🚀 İşlem başlatıldı: {self.current_novel.title} ({total_selected} seçili bölüm)")
            self.log(f"⚡ İndirme Motoru: {concurrency} Eşzamanlı İş Parçacığı (Paralel Mod)")

            # 1. Eksik bölümleri belirle
            pending = [ch for ch in selected_chapters if not ch.is_downloaded]
            if pending:
                self.log(f"📥 {len(pending)} eksik bölüm siteden paralel indiriliyor...")
            else:
                self.log("✓ Tüm seçili bölümler önbellekte mevcut, doğrudan derlemeye geçiliyor.")

            completed_count = 0
            total_to_download = len(pending)

            def download_single(ch: Chapter):
                if self._cancel_requested:
                    return None
                try:
                    title, content_html = self.client.fetch_chapter_content(ch.id)
                    self.storage.save_chapter_content(ch.id, content_html)
                    ch.content_html = content_html
                    ch.is_downloaded = True
                    return ch
                except Exception as e:
                    self.log(f"[-] Hata (Bölüm ID {ch.id}): {e}", "error")
                    return None

            if pending:
                with ThreadPoolExecutor(max_workers=concurrency) as executor:
                    futures = {executor.submit(download_single, ch): ch for ch in pending}
                    for future in as_completed(futures):
                        if self._cancel_requested:
                            executor.shutdown(wait=False, cancel_futures=True)
                            self.log("⚠️ İşlem kullanıcı tarafından durduruldu.", "warning")
                            self._eval_js("window.onProcessFinished && window.onProcessFinished(false, 'İşlem durduruldu.');")
                            self._is_running = False
                            return

                        ch = future.result()
                        completed_count += 1
                        if ch:
                            self.update_chapter_status(ch.id, "✓ İndi")
                            self.log(f"[{completed_count}/{total_to_download}] İndirildi: Bölüm {ch.order_index}")

                        self.update_progress(completed_count, total_to_download, f"İndiriliyor: {completed_count}/{total_to_download} bölüm")

            # 2. Kapak görseli
            cover_bytes = None
            custom_cover_path = options.get("custom_cover_path")
            if custom_cover_path:
                try:
                    with open(custom_cover_path, "rb") as f:
                        cover_bytes = f.read()
                    self.log("🖼️ Özel kapak resmi yüklendi.")
                except Exception as e:
                    self.log(f"[-] Özel kapak okunamadı: {e}", "error")

            if not cover_bytes and self.current_novel.cover_url:
                self.log("🖼️ Kapak resmi siteden alınıyor...")
                cover_bytes = self.client.download_image(self.current_novel.cover_url)

            # 3. İndirilmiş hazır bölümleri al
            all_downloaded = self.storage.get_all_chapters(only_downloaded=True)
            ready_chapters = [c for c in all_downloaded if c.id in selected_ids]

            if not ready_chapters:
                self.log("❌ Dönüştürülecek hazır bölüm bulunamadı.", "error")
                self._eval_js("window.onProcessFinished && window.onProcessFinished(false, 'Dönüştürülecek hazır bölüm bulunamadı.');")
                self._is_running = False
                return

            out_dir_str = options.get("output_dir") or str(DOWNLOADS_DIR.resolve())
            base_out = Path(out_dir_str) / self.current_novel.slug
            epub_dir = base_out / "epub"
            pdf_dir = base_out / "pdf"

            do_split = bool(options.get("do_split", True))
            split_size = int(options.get("split_size", 300))
            only_num = bool(options.get("only_numbered_titles", False))
            build_epub = bool(options.get("format_epub", True))
            build_pdf = bool(options.get("format_pdf", False))

            if build_epub:
                epub_dir.mkdir(parents=True, exist_ok=True)
            if build_pdf:
                pdf_dir.mkdir(parents=True, exist_ok=True)

            epub_builder = EpubBuilder(self.current_novel, cover_bytes) if build_epub else None
            pdf_builder = PdfBuilder(self.current_novel, cover_bytes) if build_pdf else None

            groups = []
            if do_split and split_size > 0 and len(ready_chapters) > split_size:
                total_vols = (len(ready_chapters) + split_size - 1) // split_size
                for v in range(total_vols):
                    start = v * split_size
                    end = min(start + split_size, len(ready_chapters))
                    vol_chaps = ready_chapters[start:end]
                    vol_title = f"Cilt {v+1:02d} (Bölüm {vol_chaps[0].order_index}-{vol_chaps[-1].order_index})"
                    groups.append((vol_chaps, vol_title, f"-cilt-{v+1:02d}"))
            else:
                groups.append((ready_chapters, None, "-tam"))

            self.update_progress(0, len(groups), "E-kitap dosyaları derleniyor...")
            for idx, (vol_chaps, vol_title, suffix) in enumerate(groups, start=1):
                if self._cancel_requested:
                    self.log("⚠️ Derleme durduruldu.", "warning")
                    self._eval_js("window.onProcessFinished && window.onProcessFinished(false, 'Derleme durduruldu.');")
                    self._is_running = False
                    return

                base_name = f"{self.current_novel.slug}{suffix}"

                if build_epub:
                    epub_path = epub_dir / f"{base_name}.epub"
                    self.log(f"📦 EPUB derleniyor: epub/{epub_path.name}")
                    epub_builder.build(vol_chaps, epub_path, volume_title=vol_title, only_numbered_titles=only_num)

                if build_pdf:
                    pdf_path = pdf_dir / f"{base_name}.pdf"
                    self.log(f"📄 PDF derleniyor (A5 + Tıklanabilir İçindekiler): pdf/{pdf_path.name}")
                    pdf_builder.build(vol_chaps, pdf_path, volume_title=vol_title, only_numbered_titles=only_num)

                self.update_progress(idx, len(groups), f"Cilt tamamlandı ({idx}/{len(groups)})")

            # Update stats
            stats = self.storage.get_stats()
            self._eval_js(f"window.onStatsUpdated && window.onStatsUpdated({stats['downloaded']}, {stats['total']}, {stats['percent']});")

            success_msg = f"Tüm dosyalar başarıyla oluşturuldu!\\n"
            if build_epub:
                success_msg += f"📦 EPUB: {epub_dir}\\n"
            if build_pdf:
                success_msg += f"📄 PDF: {pdf_dir}\\n"

            self.log(f"🎉 İşlem başarıyla tamamlandı! Çıktılar: {base_out}", "success")
            js_msg = json.dumps(success_msg)
            js_out = json.dumps(str(base_out))
            self._eval_js(f"window.onProcessFinished && window.onProcessFinished(true, {js_msg}, {js_out});")

        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            self.log(f"❌ Kritik Hata: {err_msg}", "error")
            js_err = json.dumps(str(e))
            self._eval_js(f"window.onProcessFinished && window.onProcessFinished(false, {js_err});")
        finally:
            self._is_running = False
