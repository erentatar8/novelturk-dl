<div align="center">
  <img src="assets/icon.png" width="128" height="128" alt="novelturk-dl logo" style="border-radius: 24px;" />
  <h1>novelturk-dl</h1>
  <p>NovelTürk web romanlarını e-kitap okuyucuları için EPUB ve PDF formatına dönüştüren masaüstü aracı.</p>
  <p>Desktop tool to download NovelTürk web novels and convert them into EPUB & PDF formats for e-readers.</p>
  <p>
    <a href="#türkçe">Türkçe</a> •
    <a href="#english">English</a>
  </p>
</div>

---

<a name="türkçe"></a>
## Türkçe

### İndirme (Kurulum Gerektirmeyen Hazır Sürümler)
Python ile uğraşmak istemiyorsanız, doğrudan [Releases](https://github.com/erentatar8/novelturk-dl/releases) bölümünden sisteminize uygun dosyayı indirebilirsiniz:
- **Windows:** `novelturk-dl-windows.exe` (İndirip çift tıklayarak çalıştırın)
- **macOS:** `novelturk-dl-macos.zip` (Aşağıdaki Gatekeeper notuna bakın)
- **Linux:** `novelturk-dl-linux`

> **Önemli (macOS Güvenlik & İlk Açılış Uyarısı):**
> Apple, yeni macOS sürümlerinde (Sequoia, Sonoma, Ventura) App Store dışı uygulamaları açarken Control+Tık yöntemini kısıtlamıştır. Uygulamayı ilk kez açmak için:
> 1. İndirdiğiniz `novelturk-dl.app` dosyasına çift tıklayın (hata uyarısı verip açılmayacaktır, bu normaldir).
> 2. Mac'inizde **Sistem Ayarları (System Settings) > Gizlilik ve Güvenlik (Privacy & Security)** menüsüne gidin.
> 3. En aşağı kaydırın; *"novelturk-dl engellendi"* uyarısının yanındaki **"Yine de Aç" (Open Anyway)** butonuna tıklayın ve parolanızı/Touch ID'nizi girin.
> 4. Alternatif olarak doğrudan Terminal üzerinden şu komutu çalıştırarak bu engeli anında kaldırabilirsiniz:
>    ```bash
>    xattr -cr /Applications/novelturk-dl.app
>    # veya dosya İndirilenler'deyse:
>    xattr -cr ~/Downloads/novelturk-dl.app
>    ```

---

### Özellikler
- **Web Tabanlı Modern UI:** Donanım hızlandırmalı sade ve koyu arayüz.
- **Hızlı Paralel İndirme:** Ayarlanabilir iş parçacığı (1-8 thread) ile güvenli ve hızlı indirme.
- **Yerel Önbellek (SQLite):** İndirilen bölümler yerelde saklanır, tekrarlanan istek yapılmaz.
- **E-Kitap Üretimi:**
  - **EPUB:** Kapaklı, içindekiler sayfalı, Kindle ve Kobo uyumlu.
  - **PDF:** A5 kitap formatında, Türkçe karakter destekli, tıklanabilir içindekiler bağlantılı.
- **Ciltleme:** Bölümleri istenen adette (örn: 300) ciltlere ayırma veya tek ciltte birleştirme.
- **Kapak Seçici:** Orijinal kapak veya yerel dosyalardan özel görsel seçimi.

---

### Kaynak Koddan Çalıştırma (Geliştiriciler İçin)

#### 1. Depoyu Klonlayın
```bash
git clone https://github.com/erentatar8/novelturk-dl.git
cd novelturk-dl
```

#### 2. Sanal Ortamı Kurun ve Bağımlılıkları Yükleyin

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.0-dev libgtk-3-dev
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Çalıştırma

- **Masaüstü Arayüzü (GUI):**
  - macOS: `./run.command` veya `python3 main.py gui`
  - Windows: `run.bat` veya `python main.py gui`
  - Linux: `python3 main.py gui`

- **Komut Satırı (CLI):**
  ```bash
  # 1. Noveli indirmek için:
  python main.py download reverend-insanity --threads 4

  # 2. 300'lük ciltler halinde EPUB ve PDF üretmek için:
  python main.py export reverend-insanity --split 300 --format both

  # 3. İndirme durumunu sorgulamak için:
  python main.py status reverend-insanity
  ```

---

### Yasal Uyarı
Bu yazılım yalnızca kişisel kullanım, eğitim ve çevrimdışı arşivleme amacıyla geliştirilmiştir. Bu depo hiçbir telifli roman metni veya veritabanı barındırmaz.

---

<a name="english"></a>
## English

### Prebuilt Binaries (No Python Required)
If you prefer not to install Python, download the standalone executables from [Releases](https://github.com/erentatar8/novelturk-dl/releases):
- **Windows:** `novelturk-dl-windows.exe`
- **macOS:** `novelturk-dl-macos.zip` (See Gatekeeper note below)
- **Linux:** `novelturk-dl-linux`

> **Note on macOS Security & First Launch:**
> In modern macOS versions (Sequoia, Sonoma, Ventura), Apple no longer allows bypassing unsigned apps via Control+Click alone. To open the application for the first time:
> 1. Double-click `novelturk-dl.app` once (it will show a security dialog and refuse to open; this is expected).
> 2. Open **System Settings > Privacy & Security**.
> 3. Scroll down to the **Security** section and click **"Open Anyway"** next to the `novelturk-dl` blocked notice, then enter your password/Touch ID.
> 4. Alternatively, remove the quarantine attribute directly via Terminal:
>    ```bash
>    xattr -cr /Applications/novelturk-dl.app
>    # or if in Downloads:
>    xattr -cr ~/Downloads/novelturk-dl.app
>    ```

---

### Key Features
- **Modern WebKit Desktop UI:** Fast and clean dark theme interface.
- **Parallel Downloader:** Thread-safe multithreaded download engine (1 to 8 workers).
- **Local SQLite Cache:** Chapters are stored locally to prevent redundant network requests.
- **E-Book Compilation:**
  - **EPUB:** Kindle, Kobo, and Apple Books compatible with cover and interactive table of contents.
  - **PDF:** A5 layout with embedded TrueType font and clickable internal links.
- **Volume Splitting:** Split large novels into volumes (e.g. 300 chapters per book).
- **Custom Cover:** Use site cover or upload custom image directly from the main view.

---

### Running from Source

#### 1. Clone the repository
```bash
git clone https://github.com/erentatar8/novelturk-dl.git
cd novelturk-dl
```

#### 2. Virtual Environment & Dependencies

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install -y libwebkit2gtk-4.0-dev libgtk-3-dev
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Launching

- **Desktop GUI:**
  - macOS: `./run.command` or `python3 main.py gui`
  - Windows: `run.bat` or `python main.py gui`
  - Linux: `python3 main.py gui`

- **CLI Usage:**
  ```bash
  # Download novel
  python main.py download reverend-insanity --threads 4

  # Export to EPUB & PDF in 300-chapter volumes
  python main.py export reverend-insanity --split 300 --format both

  # Check status
  python main.py status reverend-insanity
  ```

---

### Disclaimer
This software is provided for educational, personal, and offline archiving purposes only. This repository does not host any copyrighted novel content or database files.
