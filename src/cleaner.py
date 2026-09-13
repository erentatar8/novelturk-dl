import re
from bs4 import BeautifulSoup

def clean_chapter_html(raw_html: str, chapter_title: str = "") -> str:
    """
    WordPress REST API veya sayfadan dönen HTML içeriğini temizler:
    - Reklam kodları, scriptler, iframe'ler temizlenir.
    - Boş paragraflar temizlenir.
    - E-okuyucular için standart ve temiz <p> blokları bırakılır.
    """
    if not raw_html:
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")

    # İstenmeyen etiketleri kaldır
    for tag in soup(["script", "style", "iframe", "ins", "button", "input", "svg"]):
        tag.decompose()

    # Reklam sınıflarını içeren elemanları kaldır
    for tag in soup.find_all(attrs={"class": re.compile(r"(ad-|adsbygoogle|nt-cmt|reaction|share)", re.I)}):
        tag.decompose()

    # Çevirmen notu / dipnot varsa temiz biçimlendir
    paragraphs = []
    for p in soup.find_all(["p", "div", "h2", "h3", "h4"]):
        # Eğer p bir başka p'nin içindeyse tekrar alma
        if p.find_parent("p"):
            continue
            
        text = p.get_text(separator=" ", strip=True)
        if not text:
            continue

        # Sitenin standart reklam/duyuru kalıplarını ele
        if any(skip in text.lower() for skip in [
            "novel türk", "novelturk.com", "hata bildir", "sonraki bölüm",
            "önceki bölüm", "yorum bırak", "okuma ayarları"
        ]):
            # Tam eşleşme veya sadece reklam cümlesiyse atla
            if len(text) < 150:
                continue

        # Başlığı ilk paragrafla tekrar etmesin
        if chapter_title and text.lower() == chapter_title.lower():
            continue

        paragraphs.append(f"<p>{text}</p>")

    if not paragraphs:
        # Fallback: eğer <p> yoksa doğrudan temizlenmiş metni böl
        raw_text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        paragraphs = [f"<p>{line}</p>" for line in lines]

    return "\n".join(paragraphs)
