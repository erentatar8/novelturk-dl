#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config import DOWNLOADS_DIR
from src.client import NovelTurkClient
from src.storage import Storage
from src.epub_builder import EpubBuilder
from src.pdf_builder import PdfBuilder

def cmd_gui(args=None):
    from src.gui_web import run_gui
    run_gui()

def cmd_status(args):
    slug = NovelTurkClient.extract_slug(args.target)
    storage = Storage(slug)
    novel = storage.get_novel_meta()
    
    if not novel:
        print(f"[-] '{slug}' için henüz yerel bir veritabanı bulunamadı.")
        return

    stats = storage.get_stats()
    print("\n" + "="*50)
    print(f"📖 Novel: {novel.title}")
    print(f"✍️  Yazar: {novel.author}")
    print(f"📂 Slug:  {novel.slug}")
    print(f"📊 Durum: {stats['downloaded']}/{stats['total']} bölüm indirildi (%{stats['percent']:.1f})")
    print(f"⏳ Kalan: {stats['remaining']} bölüm")
    print("="*50 + "\n")

def cmd_download(args):
    client = NovelTurkClient()
    slug = client.extract_slug(args.target)
    storage = Storage(slug)

    print(f"\n[*] '{slug}' bilgileri kontrol ediliyor...")
    novel, nonce, groups = client.fetch_novel_info(slug)
    print(f"[+] Başlık: {novel.title}")
    print(f"[+] Yazar:  {novel.author}")
    print(f"[+] Bulunan Sekmeler: {len(groups)} adet ({', '.join(groups)})")

    print("[*] Bölüm listesi güncelleniyor...")
    chapters = client.fetch_all_chapters_list(slug, novel.novel_id, groups, nonce)
    novel.total_chapters = len(chapters)
    storage.save_novel_meta(novel)
    storage.sync_chapters(chapters)
    print(f"[+] Toplam {len(chapters)} bölüm tespit edildi ve veritabanına kaydedildi.")

    pending = storage.get_pending_chapters()
    if not pending:
        print("[✓] Tüm bölümler zaten daha önce indirilmiş!")
        return

    if args.limit and args.limit > 0:
        pending = pending[:args.limit]
        print(f"[*] Belirtilen limit nedeniyle ilk {args.limit} eksik bölüm indirilecek.")

    threads = getattr(args, "threads", 4) or 4
    print(f"[*] {len(pending)} bölüm {threads} paralel thread ile indirilmeye başlanıyor...")

    def download_ch(ch):
        try:
            title, content_html = client.fetch_chapter_content(ch.id)
            storage.save_chapter_content(ch.id, content_html)
            return ch.order_index, True, None
        except Exception as e:
            return ch.order_index, False, str(e)

    with tqdm(total=len(pending), desc="İndiriliyor", unit="bölüm") as pbar:
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(download_ch, ch) for ch in pending]
            for future in as_completed(futures):
                order_idx, success, err = future.result()
                if success:
                    pbar.set_postfix_str(f"Bölüm {order_idx}")
                else:
                    pbar.write(f"[-] Hata (Bölüm {order_idx}): {err}")
                pbar.update(1)

    stats = storage.get_stats()
    print(f"\n[✓] İndirme tamamlandı! ({stats['downloaded']}/{stats['total']} bölüm mevcut)")

def cmd_export(args):
    slug = NovelTurkClient.extract_slug(args.target)
    storage = Storage(slug)
    novel = storage.get_novel_meta()

    if not novel:
        print(f"[-] '{slug}' için yerel veritabanı bulunamadı. Önce indirme yapmalısınız.")
        return

    downloaded = storage.get_all_chapters(only_downloaded=True)
    if not downloaded:
        print("[-] İndirilmiş hiçbir bölüm bulunamadı.")
        return

    print(f"\n[*] '{novel.title}' için dosyalar derleniyor ({len(downloaded)} bölüm hazır)...")

    client = NovelTurkClient()
    cover_bytes = None
    if args.cover:
        try:
            with open(args.cover, "rb") as f:
                cover_bytes = f.read()
            print(f"[+] Özel kapak yüklendi: {args.cover}")
        except Exception as e:
            print(f"[-] Özel kapak okunamadı: {e}")

    if not cover_bytes and novel.cover_url:
        print("[*] Kapak görseli siteden indiriliyor...")
        cover_bytes = client.download_image(novel.cover_url)

    base_out = Path(args.output) if args.output else DOWNLOADS_DIR / slug
    epub_dir = base_out / "epub"
    pdf_dir = base_out / "pdf"

    split_size = args.split
    only_num = args.only_numbers
    make_epub = args.format in ["epub", "both"]
    make_pdf = args.format in ["pdf", "both"]

    if make_epub:
        epub_dir.mkdir(parents=True, exist_ok=True)
    if make_pdf:
        pdf_dir.mkdir(parents=True, exist_ok=True)

    epub_builder = EpubBuilder(novel, cover_bytes) if make_epub else None
    pdf_builder = PdfBuilder(novel, cover_bytes) if make_pdf else None

    groups = []
    if split_size and split_size > 0 and len(downloaded) > split_size:
        total_vols = (len(downloaded) + split_size - 1) // split_size
        print(f"[*] {len(downloaded)} bölüm {split_size}'er bölümlük {total_vols} cilde bölünüyor...")
        for vol_idx in range(total_vols):
            start = vol_idx * split_size
            end = min(start + split_size, len(downloaded))
            vol_chapters = downloaded[start:end]
            vol_num = vol_idx + 1
            vol_title = f"Cilt {vol_num:02d} (Bölüm {vol_chapters[0].order_index}-{vol_chapters[-1].order_index})"
            groups.append((vol_chapters, vol_title, f"-cilt-{vol_num:02d}"))
    else:
        groups.append((downloaded, None, "-tam"))

    for vol_chaps, vol_title, suffix in groups:
        base_name = f"{slug}{suffix}"
        if make_epub:
            epub_path = epub_dir / f"{base_name}.epub"
            print(f"  -> EPUB: epub/{epub_path.name}...")
            epub_builder.build(vol_chaps, epub_path, volume_title=vol_title, only_numbered_titles=only_num)
        if make_pdf:
            pdf_path = pdf_dir / f"{base_name}.pdf"
            print(f"  -> PDF:  pdf/{pdf_path.name}...")
            pdf_builder.build(vol_chaps, pdf_path, volume_title=vol_title, only_numbered_titles=only_num)

    print(f"\n[✓] Tüm dosyalar başarıyla oluşturuldu!")
    if make_epub:
        print(f"📁 EPUB Klasörü: {epub_dir.resolve()}")
    if make_pdf:
        print(f"📁 PDF Klasörü:  {pdf_dir.resolve()}")

def main():
    if len(sys.argv) == 1:
        cmd_gui()
        return

    parser = argparse.ArgumentParser(
        description="NovelTürk İndirici ve E-Kitap (EPUB & PDF) Oluşturucu",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command")

    p_gui = subparsers.add_parser("gui", help="Grafiksel arayüzü (HakuNeko modu) açar")
    p_gui.set_defaults(func=cmd_gui)

    p_down = subparsers.add_parser("download", help="Noveli veya eksik bölümleri indirir")
    p_down.add_argument("target", help="Novel URL'si veya slug adı")
    p_down.add_argument("--limit", type=int, default=0, help="Sadece ilk N bölümü indir")
    p_down.add_argument("--threads", "-t", type=int, default=4, help="Paralel indirme iş parçacığı sayısı (varsayılan: 4)")
    p_down.set_defaults(func=cmd_download)

    p_exp = subparsers.add_parser("export", help="İndirilmiş bölümlerden EPUB/PDF üretir")
    p_exp.add_argument("target", help="Novel slug adı")
    p_exp.add_argument("--split", type=int, default=0, help="Cilt başına bölüm sayısı (örn: 300)")
    p_exp.add_argument("--format", choices=["epub", "pdf", "both"], default="both", help="Çıktı formatı")
    p_exp.add_argument("--only-numbers", action="store_true", help="Bölüm başlığı yerine sadece numara yaz")
    p_exp.add_argument("--cover", type=str, default=None, help="Özel kapak resmi yolu")
    p_exp.add_argument("--output", "-o", type=str, default=None, help="Çıktı klasörü")
    p_exp.set_defaults(func=cmd_export)

    p_stat = subparsers.add_parser("status", help="İndirme durumunu ve istatistikleri gösterir")
    p_stat.add_argument("target", help="Novel slug adı")
    p_stat.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        cmd_gui()

if __name__ == "__main__":
    main()
