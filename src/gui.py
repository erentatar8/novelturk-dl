import os
import sys
import time
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QRadioButton, QButtonGroup, QSpinBox,
    QFileDialog, QProgressBar, QTextEdit, QSplitter, QGroupBox,
    QMessageBox, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QColor, QFont

from .config import DOWNLOADS_DIR
from .client import NovelTurkClient
from .storage import Storage
from .models import Novel, Chapter
from .epub_builder import EpubBuilder
from .pdf_builder import PdfBuilder

DARK_STYLE = """
QMainWindow {
    background-color: #090a0f;
}
QWidget {
    background-color: #090a0f;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}
QGroupBox {
    background-color: #12141e;
    border: 1px solid #1e2235;
    border-radius: 10px;
    margin-top: 20px;
    font-weight: 600;
    font-size: 13px;
    color: #c7d2fe;
    padding: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #12141e;
    border-radius: 4px;
}
QLineEdit, QSpinBox {
    background-color: #181b28;
    border: 1px solid #282d45;
    border-radius: 7px;
    padding: 7px 12px;
    color: #ffffff;
    selection-background-color: #6366f1;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #818cf8;
    background-color: #1d2030;
}
QPushButton {
    background-color: #1c1f2e;
    border: 1px solid #2d334d;
    border-radius: 7px;
    padding: 8px 16px;
    color: #f8fafc;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #262b40;
    border-color: #434c73;
}
QPushButton:pressed {
    background-color: #161824;
}
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #8b5cf6);
    border: none;
    font-weight: 700;
    font-size: 14px;
    padding: 11px 20px;
    border-radius: 8px;
    color: #ffffff;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #7c3aed);
}
QPushButton#primaryBtn:disabled {
    background: #1f2233;
    color: #64748b;
}
QPushButton#stopBtn {
    background-color: #3f1d24;
    border: 1px solid #7f1d1d;
    color: #fca5a5;
    font-weight: 600;
}
QPushButton#stopBtn:hover {
    background-color: #5c242e;
}
QPushButton#stopBtn:disabled {
    background-color: #1c1f2e;
    border-color: #2d334d;
    color: #64748b;
}
QTableWidget {
    background-color: #12141e;
    border: 1px solid #1e2235;
    border-radius: 10px;
    gridline-color: #1a1d2b;
    selection-background-color: #312e81;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #161824;
    color: #94a3b8;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #22263a;
    font-weight: 600;
}
QScrollBar:vertical {
    border: none;
    background: #090a0f;
    width: 8px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: #252a3d;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #6366f1;
}
QProgressBar {
    background-color: #161824;
    border: 1px solid #22263a;
    border-radius: 8px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 20px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #a855f7);
    border-radius: 7px;
}
QTextEdit {
    background-color: #0b0c12;
    border: 1px solid #1a1d2b;
    border-radius: 8px;
    font-family: Menlo, Monaco, "SF Mono", monospace;
    font-size: 11.5px;
    color: #cbd5e1;
    padding: 6px;
}
QRadioButton, QCheckBox {
    spacing: 9px;
    font-size: 13px;
    color: #cbd5e1;
}
QRadioButton:hover, QCheckBox:hover {
    color: #ffffff;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 17px;
    height: 17px;
}
"""

class WorkerThread(QThread):
    chapter_downloaded_signal = pyqtSignal(int, int, str)
    progress_signal = pyqtSignal(int, int, str)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, client: NovelTurkClient, storage: Storage, novel: Novel,
                 selected_chapters: List[Chapter], options: dict):
        super().__init__()
        self.client = client
        self.storage = storage
        self.novel = novel
        self.selected_chapters = selected_chapters
        self.options = options
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            total_selected = len(self.selected_chapters)
            concurrency = self.options.get("concurrency", 4)
            self.log_signal.emit(f"🚀 İşlem başlatıldı: {self.novel.title} ({total_selected} seçili bölüm)")
            self.log_signal.emit(f"⚡ İndirme Motoru: {concurrency} Eşzamanlı İş Parçacığı (Paralel Mod)")

            # 1. Eksik bölümleri belirle
            pending = [ch for ch in self.selected_chapters if not ch.is_downloaded]
            if pending:
                self.log_signal.emit(f"📥 {len(pending)} eksik bölüm paralel olarak indiriliyor...")
            else:
                self.log_signal.emit("✓ Tüm seçili bölümler önbellekte mevcut, doğrudan dönüştürmeye geçiliyor.")

            completed_count = 0
            total_to_download = len(pending)

            def download_single_chapter(ch: Chapter):
                if self._is_cancelled:
                    return None
                try:
                    title, content_html = self.client.fetch_chapter_content(ch.id)
                    self.storage.save_chapter_content(ch.id, content_html)
                    ch.content_html = content_html
                    ch.is_downloaded = True
                    return ch
                except Exception as e:
                    self.log_signal.emit(f"[-] Hata (Bölüm ID {ch.id}): {e}")
                    return None

            if pending:
                with ThreadPoolExecutor(max_workers=concurrency) as executor:
                    futures = {executor.submit(download_single_chapter, ch): ch for ch in pending}
                    for future in as_completed(futures):
                        if self._is_cancelled:
                            executor.shutdown(wait=False, cancel_futures=True)
                            self.log_signal.emit("⚠️ İşlem kullanıcı tarafından durduruldu.")
                            self.finished_signal.emit(False, "İndirme durduruldu.")
                            return

                        ch = future.result()
                        completed_count += 1
                        if ch:
                            self.chapter_downloaded_signal.emit(ch.id, ch.order_index, "✓ İndi")
                            self.log_signal.emit(f"[{completed_count}/{total_to_download}] İndirildi: Bölüm {ch.order_index}")
                        
                        self.progress_signal.emit(completed_count, total_to_download, f"İndiriliyor: {completed_count}/{total_to_download} bölüm")

            # 2. Kapak görseli
            cover_bytes = None
            if self.options.get("custom_cover_path"):
                try:
                    with open(self.options["custom_cover_path"], "rb") as f:
                        cover_bytes = f.read()
                    self.log_signal.emit("🖼️ Özel kapak resmi yüklendi.")
                except Exception as e:
                    self.log_signal.emit(f"[-] Özel kapak okunamadı: {e}")

            if not cover_bytes and self.novel.cover_url:
                self.log_signal.emit("🖼️ Kapak resmi siteden alınıyor...")
                cover_bytes = self.client.download_image(self.novel.cover_url)

            # 3. İndirilmiş bölümleri al
            all_downloaded = self.storage.get_all_chapters(only_downloaded=True)
            sel_ids = {c.id for c in self.selected_chapters}
            ready_chapters = [c for c in all_downloaded if c.id in sel_ids]

            if not ready_chapters:
                self.finished_signal.emit(False, "Dönüştürülecek hazır bölüm bulunamadı.")
                return

            base_out = Path(self.options["output_dir"]) / self.novel.slug
            epub_dir = base_out / "epub"
            pdf_dir = base_out / "pdf"

            do_split = self.options["do_split"]
            split_size = self.options["split_size"]
            only_num = self.options["only_numbered_titles"]
            build_epub = self.options["format_epub"]
            build_pdf = self.options["format_pdf"]

            if build_epub:
                epub_dir.mkdir(parents=True, exist_ok=True)
            if build_pdf:
                pdf_dir.mkdir(parents=True, exist_ok=True)

            epub_builder = EpubBuilder(self.novel, cover_bytes) if build_epub else None
            pdf_builder = PdfBuilder(self.novel, cover_bytes) if build_pdf else None

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

            self.progress_signal.emit(0, len(groups), "E-kitap dosyaları derleniyor...")
            for idx, (vol_chaps, vol_title, suffix) in enumerate(groups, start=1):
                base_name = f"{self.novel.slug}{suffix}"
                
                if build_epub:
                    epub_path = epub_dir / f"{base_name}.epub"
                    self.log_signal.emit(f"📦 EPUB derleniyor: epub/{epub_path.name}")
                    epub_builder.build(vol_chaps, epub_path, volume_title=vol_title, only_numbered_titles=only_num)

                if build_pdf:
                    pdf_path = pdf_dir / f"{base_name}.pdf"
                    self.log_signal.emit(f"📄 PDF derleniyor (A5 + Tıklanabilir İçindekiler): pdf/{pdf_path.name}")
                    pdf_builder.build(vol_chaps, pdf_path, volume_title=vol_title, only_numbered_titles=only_num)

                self.progress_signal.emit(idx, len(groups), f"Cilt tamamlandı ({idx}/{len(groups)})")

            msg = f"Tüm dosyalar başarıyla oluşturuldu!\n\n"
            if build_epub:
                msg += f"📦 EPUB Klasörü: {epub_dir}\n"
            if build_pdf:
                msg += f"📄 PDF Klasörü:  {pdf_dir}\n"

            self.log_signal.emit(f"🎉 İşlem tamamlandı! EPUB: {epub_dir} | PDF: {pdf_dir}")
            self.finished_signal.emit(True, msg)

        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            self.log_signal.emit(f"❌ Kritik Hata: {err_msg}")
            self.finished_signal.emit(False, str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NovelTürk Downloader & Converter (HakuNeko 2.0 Edition)")
        self.resize(1220, 780)

        self.client = NovelTurkClient()
        self.current_novel: Optional[Novel] = None
        self.storage: Optional[Storage] = None
        self.all_chapters: List[Chapter] = []
        self.chapter_row_map = {}
        self.worker: Optional[WorkerThread] = None

        self._init_ui()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(10)

        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)

        mid_panel = self._create_mid_panel()
        splitter.addWidget(mid_panel)

        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([330, 510, 380])
        main_layout.addWidget(splitter, stretch=1)

        bottom_panel = self._create_bottom_panel()
        main_layout.addWidget(bottom_panel)

    def _create_left_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(12)

        gb = QGroupBox("Novel Arama & Fihrist")
        gbl = QVBoxLayout(gb)
        gbl.setSpacing(10)

        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("Novel URL veya Slug (örn: reverend-insanity)")
        self.txt_url.setText("https://novelturk.com/novel/reverend-insanity/")
        gbl.addWidget(self.txt_url)

        self.btn_load = QPushButton("🔍 Fihristi Getir")
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.clicked.connect(self._on_load_novel)
        gbl.addWidget(self.btn_load)

        layout.addWidget(gb)

        self.card_group = QGroupBox("Novel Bilgileri")
        cl = QVBoxLayout(self.card_group)
        cl.setAlignment(Qt.AlignmentFlag.AlignTop)
        cl.setSpacing(10)

        self.lbl_cover = QLabel()
        self.lbl_cover.setFixedSize(145, 205)
        self.lbl_cover.setStyleSheet("""
            background-color: #161824;
            border: 1px solid #282d45;
            border-radius: 8px;
        """)
        self.lbl_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cover.setText("Kapak Yok")
        cl.addWidget(self.lbl_cover, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_title = QLabel("Novel Adı: -")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setStyleSheet("font-weight: 700; font-size: 14.5px; color: #ffffff;")
        cl.addWidget(self.lbl_title)

        self.lbl_author = QLabel("Yazar: -")
        self.lbl_author.setStyleSheet("color: #a5b4fc; font-weight: 500;")
        cl.addWidget(self.lbl_author)

        self.lbl_stats = QLabel("Bölüm Durumu: -")
        self.lbl_stats.setStyleSheet("color: #38bdf8; font-weight: 600;")
        cl.addWidget(self.lbl_stats)

        self.txt_desc = QTextEdit()
        self.txt_desc.setReadOnly(True)
        self.txt_desc.setPlaceholderText("Özet bilgisi...")
        self.txt_desc.setFixedHeight(115)
        cl.addWidget(self.txt_desc)

        layout.addWidget(self.card_group, stretch=1)
        return w

    def _create_mid_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(12)

        gb = QGroupBox("Bölüm Listesi")
        gbl = QVBoxLayout(gb)
        gbl.setSpacing(10)

        top_ctrl = QHBoxLayout()
        top_ctrl.setSpacing(8)

        self.btn_sel_all = QPushButton("Tümünü Seç")
        self.btn_sel_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sel_all.clicked.connect(self._select_all_chapters)
        top_ctrl.addWidget(self.btn_sel_all)

        self.btn_desel_all = QPushButton("Kaldır")
        self.btn_desel_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_desel_all.clicked.connect(self._deselect_all_chapters)
        top_ctrl.addWidget(self.btn_desel_all)

        top_ctrl.addSpacing(6)
        lbl_r = QLabel("Aralık:")
        lbl_r.setStyleSheet("color: #94a3b8; font-weight: 500;")
        top_ctrl.addWidget(lbl_r)

        self.spin_range_from = QSpinBox()
        self.spin_range_from.setRange(1, 99999)
        self.spin_range_from.setValue(1)
        self.spin_range_from.setFixedWidth(65)
        top_ctrl.addWidget(self.spin_range_from)

        lbl_dash = QLabel("-")
        lbl_dash.setStyleSheet("color: #94a3b8;")
        top_ctrl.addWidget(lbl_dash)

        self.spin_range_to = QSpinBox()
        self.spin_range_to.setRange(1, 99999)
        self.spin_range_to.setValue(300)
        self.spin_range_to.setFixedWidth(65)
        top_ctrl.addWidget(self.spin_range_to)

        self.btn_apply_range = QPushButton("Seç")
        self.btn_apply_range.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply_range.clicked.connect(self._apply_range_selection)
        top_ctrl.addWidget(self.btn_apply_range)

        gbl.addLayout(top_ctrl)

        self.tbl_chapters = QTableWidget()
        self.tbl_chapters.setColumnCount(3)
        self.tbl_chapters.setHorizontalHeaderLabels(["No", "Bölüm Başlığı", "Durum"])
        self.tbl_chapters.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_chapters.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_chapters.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_chapters.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_chapters.verticalHeader().setDefaultSectionSize(32)
        gbl.addWidget(self.tbl_chapters)

        self.lbl_sel_count = QLabel("Seçilen: 0 / 0 Bölüm")
        self.lbl_sel_count.setStyleSheet("color: #a5b4fc; font-weight: 700; font-size: 13.5px;")
        gbl.addWidget(self.lbl_sel_count)

        layout.addWidget(gb)
        return w

    def _create_right_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(6, 0, 0, 0)
        layout.setSpacing(10)

        # 1. HIZ / EŞZAMANLILIK
        gb_speed = QGroupBox("⚡ İndirme Hızı (Paralel Bağlantı)")
        gsl_speed = QVBoxLayout(gb_speed)
        gsl_speed.setSpacing(6)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Eşzamanlı İş Parçacığı:"))
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 8)
        self.spin_threads.setValue(4)
        self.spin_threads.setFixedWidth(60)
        speed_row.addWidget(self.spin_threads)
        gsl_speed.addLayout(speed_row)

        self.lbl_speed_hint = QLabel("✓ 4 Thread (Dengeli: Sunucuyu yormaz, 4 kat hızlı)")
        self.lbl_speed_hint.setStyleSheet("color: #34d399; font-size: 11.5px; font-weight: 500;")
        gsl_speed.addWidget(self.lbl_speed_hint)

        def on_speed_change(val):
            if val <= 2:
                self.lbl_speed_hint.setText(f"✓ {val} Thread (Ultra Nazik: Düşük sunucu yükü)")
                self.lbl_speed_hint.setStyleSheet("color: #94a3b8; font-size: 11.5px;")
            elif val <= 5:
                self.lbl_speed_hint.setText(f"✓ {val} Thread (Dengeli & Güvenli: Hızlı indirme)")
                self.lbl_speed_hint.setStyleSheet("color: #34d399; font-size: 11.5px; font-weight: 500;")
            else:
                self.lbl_speed_hint.setText(f"⚡ {val} Thread (Maksimum Hız: Güçlü bağlantılar)")
                self.lbl_speed_hint.setStyleSheet("color: #fbbf24; font-size: 11.5px; font-weight: 500;")

        self.spin_threads.valueChanged.connect(on_speed_change)
        layout.addWidget(gb_speed)

        # 2. FORMAT
        gb_format = QGroupBox("📄 Çıktı Formatı (Ayrı Klasörlenir)")
        gfl = QVBoxLayout(gb_format)
        self.chk_epub = QCheckBox("EPUB (.epub ➔ epub/ klasörüne)")
        self.chk_epub.setChecked(True)
        gfl.addWidget(self.chk_epub)

        self.chk_pdf = QCheckBox("PDF (.pdf ➔ pdf/ klasörüne - Tıklanabilir TOC)")
        self.chk_pdf.setChecked(True)
        gfl.addWidget(self.chk_pdf)
        layout.addWidget(gb_format)

        # 3. CİLTLEME
        gb_split = QGroupBox("📚 Ciltleme (Bölme)")
        gsl = QVBoxLayout(gb_split)
        self.rb_split = QRadioButton("Ciltlere Böl (Önerilen)")
        self.rb_split.setChecked(True)
        gsl.addWidget(self.rb_split)

        split_spin_layout = QHBoxLayout()
        split_spin_layout.setContentsMargins(22, 0, 0, 0)
        split_spin_layout.addWidget(QLabel("Cilt Başına Bölüm:"))
        self.spin_split_size = QSpinBox()
        self.spin_split_size.setRange(10, 2000)
        self.spin_split_size.setValue(300)
        self.spin_split_size.setFixedWidth(75)
        split_spin_layout.addWidget(self.spin_split_size)
        gsl.addLayout(split_spin_layout)

        self.rb_single = QRadioButton("Tek Büyük Dosya Yap")
        gsl.addWidget(self.rb_single)
        layout.addWidget(gb_split)

        # 4. KAPAK
        gb_cover = QGroupBox("🖼️ Kapak Resmi")
        gcl = QVBoxLayout(gb_cover)
        self.rb_auto_cover = QRadioButton("Siteden Otomatik Al")
        self.rb_auto_cover.setChecked(True)
        gcl.addWidget(self.rb_auto_cover)

        self.rb_custom_cover = QRadioButton("Özel Resim Kullan")
        gcl.addWidget(self.rb_custom_cover)

        custom_cover_row = QHBoxLayout()
        custom_cover_row.setContentsMargins(22, 0, 0, 0)
        self.txt_custom_cover = QLineEdit()
        self.txt_custom_cover.setPlaceholderText("Resim dosyası seçin...")
        self.txt_custom_cover.setEnabled(False)
        custom_cover_row.addWidget(self.txt_custom_cover)

        self.btn_browse_cover = QPushButton("Gözat...")
        self.btn_browse_cover.setEnabled(False)
        self.btn_browse_cover.clicked.connect(self._browse_cover)
        custom_cover_row.addWidget(self.btn_browse_cover)
        gcl.addLayout(custom_cover_row)

        self.rb_custom_cover.toggled.connect(lambda checked: (
            self.txt_custom_cover.setEnabled(checked),
            self.btn_browse_cover.setEnabled(checked)
        ))
        layout.addWidget(gb_cover)

        # 5. BAŞLIK
        gb_title = QGroupBox("🏷️ Bölüm Başlığı Biçimi")
        gtl = QVBoxLayout(gb_title)
        self.rb_full_title = QRadioButton("Tam Başlık ('Bölüm 1 – Bir şeytanın...')")
        self.rb_full_title.setChecked(True)
        gtl.addWidget(self.rb_full_title)

        self.rb_num_title = QRadioButton("Sadece Numara ('Bölüm 1')")
        gtl.addWidget(self.rb_num_title)
        layout.addWidget(gb_title)

        # 6. KAYDETME YERİ
        gb_dest = QGroupBox("📁 Ana Kaydetme Dizini")
        gdl = QHBoxLayout(gb_dest)
        self.txt_out_dir = QLineEdit()
        self.txt_out_dir.setText(str(DOWNLOADS_DIR.resolve()))
        gdl.addWidget(self.txt_out_dir)

        self.btn_browse_out = QPushButton("Seç...")
        self.btn_browse_out.clicked.connect(self._browse_output_dir)
        gdl.addWidget(self.btn_browse_out)
        layout.addWidget(gb_dest)

        # EYLEM
        layout.addSpacing(6)
        action_layout = QHBoxLayout()
        self.btn_start = QPushButton("🚀 İNDİR VE DÖNÜŞTÜR")
        self.btn_start.setObjectName("primaryBtn")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setFixedHeight(48)
        self.btn_start.clicked.connect(self._on_start_process)
        action_layout.addWidget(self.btn_start, stretch=2)

        self.btn_stop = QPushButton("⏹ Durdur")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setFixedHeight(48)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_process)
        action_layout.addWidget(self.btn_stop, stretch=1)

        layout.addLayout(action_layout)
        layout.addStretch()
        return w

    def _create_bottom_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        status_row = QHBoxLayout()
        self.lbl_status = QLabel("Durum: Hazır")
        self.lbl_status.setStyleSheet("color: #a5b4fc; font-weight: 600;")
        status_row.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        status_row.addWidget(self.progress_bar, stretch=1)
        layout.addLayout(status_row)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(85)
        layout.addWidget(self.txt_log)
        return w

    def _log(self, text: str):
        self.txt_log.append(text)
        self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())

    def _on_load_novel(self):
        target = self.txt_url.text().strip()
        if not target:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir Novel URL'si veya adı girin.")
            return

        slug = NovelTurkClient.extract_slug(target)
        self.btn_load.setEnabled(False)
        self.btn_load.setText("Yükleniyor...")
        self.lbl_status.setText("Fihrist taranıyor, lütfen bekleyin...")
        QApplication.processEvents()

        try:
            self._log(f"[*] '{slug}' bilgileri çekiliyor...")
            novel, nonce, groups = self.client.fetch_novel_info(slug)
            self.current_novel = novel
            self.storage = Storage(slug)

            self.lbl_title.setText(f"Novel: {novel.title}")
            self.lbl_author.setText(f"Yazar: {novel.author}")
            self.txt_desc.setText(novel.description or "")

            if novel.cover_url:
                c_bytes = self.client.download_image(novel.cover_url)
                if c_bytes:
                    img = QImage.fromData(c_bytes)
                    pix = QPixmap.fromImage(img).scaled(145, 205, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.lbl_cover.setPixmap(pix)

            self._log(f"[*] {len(groups)} sekme taranıyor...")
            chapters = self.client.fetch_all_chapters_list(slug, novel.novel_id, groups, nonce)
            novel.total_chapters = len(chapters)
            self.storage.save_novel_meta(novel)
            self.storage.sync_chapters(chapters)

            self.all_chapters = self.storage.get_all_chapters(only_downloaded=False)
            self._populate_table(self.all_chapters)

            stats = self.storage.get_stats()
            self.lbl_stats.setText(f"Durum: {stats['downloaded']}/{stats['total']} İndirildi (%{stats['percent']:.1f})")
            self.spin_range_to.setMaximum(len(self.all_chapters))
            self.spin_range_to.setValue(min(300, len(self.all_chapters)))

            self._log(f"[✓] {len(self.all_chapters)} bölüm başarıyla yüklendi.")
            self.lbl_status.setText(f"Hazır: {novel.title} ({len(self.all_chapters)} bölüm)")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Novel yüklenirken hata oluştu:\n{e}")
            self._log(f"[-] Hata: {e}")
            self.lbl_status.setText("Hata oluştu.")
        finally:
            self.btn_load.setEnabled(True)
            self.btn_load.setText("🔍 Fihristi Getir")

    def _populate_table(self, chapters: List[Chapter]):
        self.tbl_chapters.blockSignals(True)
        self.tbl_chapters.setRowCount(len(chapters))
        self.chapter_row_map.clear()

        for row, ch in enumerate(chapters):
            self.chapter_row_map[ch.id] = row

            item_no = QTableWidgetItem(f"Bölüm {ch.order_index}")
            item_no.setFlags(item_no.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item_no.setCheckState(Qt.CheckState.Checked)
            self.tbl_chapters.setItem(row, 0, item_no)

            item_title = QTableWidgetItem(ch.title)
            self.tbl_chapters.setItem(row, 1, item_title)

            status_text = "✓ İndi" if ch.is_downloaded else "⏳ Bekliyor"
            item_status = QTableWidgetItem(status_text)
            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if ch.is_downloaded:
                item_status.setForeground(QColor("#34d399"))
            else:
                item_status.setForeground(QColor("#94a3b8"))
            self.tbl_chapters.setItem(row, 2, item_status)

        self.tbl_chapters.blockSignals(False)
        self._update_selection_count()
        self.tbl_chapters.itemChanged.connect(self._on_table_item_changed)

    def _on_table_item_changed(self, item):
        if item.column() == 0:
            self._update_selection_count()

    def _update_selection_count(self):
        selected = 0
        total = self.tbl_chapters.rowCount()
        for row in range(total):
            item = self.tbl_chapters.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected += 1
        self.lbl_sel_count.setText(f"Seçilen: {selected} / {total} Bölüm")

    def _select_all_chapters(self):
        self.tbl_chapters.blockSignals(True)
        for row in range(self.tbl_chapters.rowCount()):
            item = self.tbl_chapters.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        self.tbl_chapters.blockSignals(False)
        self._update_selection_count()

    def _deselect_all_chapters(self):
        self.tbl_chapters.blockSignals(True)
        for row in range(self.tbl_chapters.rowCount()):
            item = self.tbl_chapters.item(row, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.tbl_chapters.blockSignals(False)
        self._update_selection_count()

    def _apply_range_selection(self):
        r_from = self.spin_range_from.value()
        r_to = self.spin_range_to.value()
        if r_from > r_to:
            r_from, r_to = r_to, r_from

        self.tbl_chapters.blockSignals(True)
        for row in range(self.tbl_chapters.rowCount()):
            item = self.tbl_chapters.item(row, 0)
            if item and row < len(self.all_chapters):
                ch_num = self.all_chapters[row].order_index
                if r_from <= ch_num <= r_to:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
        self.tbl_chapters.blockSignals(False)
        self._update_selection_count()
        self._log(f"[*] Bölüm {r_from} ile {r_to} arası seçildi.")

    def _browse_cover(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Kapak Resmi Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            self.txt_custom_cover.setText(file_path)

    def _browse_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Kaydetme Klasörü Seç", self.txt_out_dir.text())
        if dir_path:
            self.txt_out_dir.setText(dir_path)

    def _on_start_process(self):
        if not self.current_novel or not self.all_chapters:
            QMessageBox.warning(self, "Uyarı", "Önce bir novel fihristi yüklemelisiniz.")
            return

        selected_chapters = []
        for row in range(self.tbl_chapters.rowCount()):
            item = self.tbl_chapters.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected_chapters.append(self.all_chapters[row])

        if not selected_chapters:
            QMessageBox.warning(self, "Uyarı", "Lütfen indirilecek en az bir bölüm seçin.")
            return

        if not self.chk_epub.isChecked() and not self.chk_pdf.isChecked():
            QMessageBox.warning(self, "Uyarı", "Lütfen en az bir çıktı formatı seçin (EPUB veya PDF).")
            return

        options = {
            "format_epub": self.chk_epub.isChecked(),
            "format_pdf": self.chk_pdf.isChecked(),
            "do_split": self.rb_split.isChecked(),
            "split_size": self.spin_split_size.value(),
            "concurrency": self.spin_threads.value(),
            "custom_cover_path": self.txt_custom_cover.text().strip() if self.rb_custom_cover.isChecked() else None,
            "only_numbered_titles": self.rb_num_title.isChecked(),
            "output_dir": self.txt_out_dir.text().strip() or str(DOWNLOADS_DIR.resolve())
        }

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_load.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker = WorkerThread(self.client, self.storage, self.current_novel, selected_chapters, options)
        self.worker.chapter_downloaded_signal.connect(self._on_chapter_downloaded)
        self.worker.progress_signal.connect(self._on_worker_progress)
        self.worker.log_signal.connect(self._log)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.start()

    def _on_chapter_downloaded(self, ch_id: int, order_index: int, status_text: str):
        row = self.chapter_row_map.get(ch_id)
        if row is not None and row < self.tbl_chapters.rowCount():
            item = self.tbl_chapters.item(row, 2)
            if item:
                item.setText(status_text)
                item.setForeground(QColor("#34d399"))

    def _on_stop_process(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.btn_stop.setEnabled(False)
            self._log("⚠️ Durdurma isteği gönderildi, aktif işlemler tamamlanıp durduruluyor...")

    def _on_worker_progress(self, current, total, text):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
        self.lbl_status.setText(text)

    def _on_worker_finished(self, success, message):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_load.setEnabled(True)

        if self.storage:
            stats = self.storage.get_stats()
            self.lbl_stats.setText(f"Durum: {stats['downloaded']}/{stats['total']} İndirildi (%{stats['percent']:.1f})")

        if success:
            QMessageBox.information(self, "Tamamlandı", message)
            self.lbl_status.setText("İşlem başarıyla tamamlandı!")
        else:
            QMessageBox.warning(self, "Bilgi", message)
            self.lbl_status.setText("İşlem tamamlanamadı.")

def run_gui():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_gui()
