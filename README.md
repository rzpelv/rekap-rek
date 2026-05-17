# Rekapin — Rekap Rekening Koran → Excel

Upload PDF e-statement bank, otomatis diproses jadi file Excel rekap dengan:

- Rekap per bulan (debet, kredit, penjualan)
- Kategorisasi otomatis: **Penjualan** vs **Non penjualan**
- Ekstraksi nama customer dari deskripsi transaksi
- Sheet "Edit Penjualan" dengan dropdown untuk koreksi manual
- Sheet "Customer Summary" dengan formula `SUMIFS` auto-update
- **Integrasi AI lokal via Ollama (opsional)** untuk kategorisasi & ekstraksi customer yang lebih akurat

**Bank yang didukung:** BCA, BRI Giro, BRI Pinjaman, Mandiri, BNI

---

## ⚡ Cara Cepat (One-Click Auto Setup)

Tersedia script auto-installer yang akan **otomatis install semua dependency**
(Python, Git, Ollama, model AI) lalu jalankan aplikasi. Yang sudah terinstall
akan di-bypass.

### Windows

1. Download/clone repo ini
2. **Double-click `setup_dan_jalankan.bat`**
3. Tunggu instalasi otomatis (Python, Git, Ollama via winget)
4. Browser akan terbuka otomatis ke `http://localhost:8080`

### macOS / Linux

1. Download/clone repo ini
2. Buka Terminal di folder repo, lalu:
   ```bash
   chmod +x setup_dan_jalankan.command
   ./setup_dan_jalankan.command
   ```
   _Atau di macOS: klik kanan file `.command` → "Open"_
3. Tunggu instalasi otomatis (Homebrew, Python, Git, Ollama)
4. Browser akan terbuka otomatis ke `http://localhost:8080`

> **Catatan:** Script akan tanya sebelum install Ollama (~2.5 GB untuk model AI).
> Boleh skip kalau tidak butuh fitur AI — aplikasi tetap jalan dengan
> kategorisasi keyword.

---

## Manual Install

Kalau lebih suka kontrol manual:

```bash
git clone https://github.com/rzpelv/rekap-rek.git
cd rekap-rek
python -m venv venv
source venv/bin/activate           # Linux/Mac
# venv\Scripts\activate            # Windows
pip install -r requirements.txt
python app.py
```

Buka **http://localhost:8080**

---

## Integrasi AI (opsional, lokal & gratis)

Aplikasi punya tombol **"Tingkatkan dengan AI"** di halaman Review yang akan
re-kategorisasi transaksi pakai LLM lokal via [Ollama](https://ollama.com).
Tombol hanya muncul kalau Ollama terdeteksi running.

### Setup

1. **Install Ollama**
   Download dari https://ollama.com → install.

2. **Pull model AI** (rekomendasi: Qwen3 4B — multilingual, ringan)

   ```bash
   ollama pull qwen3:4b
   ```

3. **Pastikan Ollama jalan** (biasanya auto-start setelah install)

   ```bash
   ollama serve
   ```

4. **Jalankan aplikasi** seperti biasa — tombol AI muncul otomatis.

### Pilihan Model (urut kualitas → ukuran)

| Model              | Ukuran | Kualitas | Catatan                           |
|--------------------|--------|----------|-----------------------------------|
| `qwen3:8b`         | ~5 GB  | ⭐⭐⭐⭐⭐ | Terbaik untuk akurasi             |
| **`qwen3:4b`** ⭐  | ~2.5 GB| ⭐⭐⭐⭐  | **Default — balance terbaik**     |
| `qwen3:1.7b`       | ~1 GB  | ⭐⭐⭐    | Sangat ringan, masih akurat       |
| `llama3.3:latest`  | ~40 GB | ⭐⭐⭐⭐⭐ | Butuh GPU besar (state-of-the-art)|
| `llama3.2:3b`      | ~2 GB  | ⭐⭐⭐    | Alternatif Meta                   |
| `gemma3:4b`        | ~3 GB  | ⭐⭐⭐⭐  | Alternatif Google                 |

Aplikasi punya **auto-fallback chain** — kalau model preferred tidak ada,
otomatis pilih model lain yang ter-pull.

### Override Model

Pakai model spesifik:

```bash
REKAPIN_AI_MODEL="llama3.3:latest" python app.py
```

Atau Ollama di host lain:

```bash
REKAPIN_AI_URL="http://192.168.1.10:11434" python app.py
```

### Environment Variables

| Variable             | Default                    | Keterangan                         |
|----------------------|----------------------------|------------------------------------|
| `REKAPIN_AI_MODEL`   | `qwen3:4b`                 | Nama model Ollama                  |
| `REKAPIN_AI_URL`     | `http://localhost:11434`   | Endpoint Ollama                    |
| `REKAPIN_AI_TIMEOUT` | `120`                      | Request timeout (detik)            |

### Tanpa Ollama

Kalau Ollama tidak running, tombol AI tidak muncul dan aplikasi tetap
berfungsi normal dengan kategorisasi berbasis keyword.

---

## Deploy ke Railway

1. Push repo ke GitHub
2. Buka [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Pilih repo ini → Railway auto-detect Python & deploy
4. Selesai

> **Catatan:** Railway tidak punya Ollama, jadi fitur AI hanya berfungsi saat
> dijalankan lokal. Untuk pakai AI di server, gunakan VPS dengan Ollama
> terinstall dan set `REKAPIN_AI_URL` ke endpoint-nya.

---

## Struktur File

```
rekap-rek/
├── app.py                       # Flask web server (routes, session)
├── rekap_rek.py                 # Parser PDF (BCA, BRI, Mandiri, BNI) + Excel builder
├── ai_helper.py                 # Integrasi Ollama dengan Structured Outputs
├── templates/
│   └── index.html               # Single-page UI
├── setup_dan_jalankan.bat       # Auto-installer Windows
├── setup_dan_jalankan.command   # Auto-installer macOS/Linux
├── requirements.txt
└── railway.json
```
