# Rekapin — Rekap Rekening Koran → Excel

Upload PDF e-statement bank, otomatis diproses jadi file Excel rekap dengan:

- Rekap per bulan (debet, kredit, penjualan)
- Kategorisasi otomatis: **Penjualan** vs **Non penjualan**
- Ekstraksi nama customer dari deskripsi transaksi
- Sheet "Edit Penjualan" dengan dropdown untuk koreksi manual
- Sheet "Customer Summary" dengan formula `SUMIFS` auto-update
- **Integrasi AI (opsional)** dengan dual provider — Cloud (Gemini) atau Lokal (Ollama)

**Bank yang didukung:** BCA, BRI Giro, BRI Pinjaman, Mandiri, BNI

---

## ⚡ Cara Cepat (One-Click Auto Setup)

Tersedia script auto-installer yang akan **otomatis install semua dependency**
lalu jalankan aplikasi. Yang sudah terinstall akan di-bypass.

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

---

## Manual Install

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

## 🤖 Integrasi AI (opsional)

Aplikasi punya tombol **"Tingkatkan dengan AI"** di halaman Review yang akan
re-kategorisasi transaksi pakai LLM. Tombol hanya muncul kalau ada provider
AI yang siap.

Tersedia **2 provider** — pilih sesuai kebutuhan:

### 🌥️ Opsi A: Google Gemini (Cloud, GRATIS) ⭐ Direkomendasikan

**Plus:**
- ✅ Tidak perlu install apa-apa
- ✅ Akurasi tinggi (lebih bagus dari Ollama lokal)
- ✅ Cepat (1-3 detik per batch)
- ✅ Free tier 1.500 request/hari
- ✅ Komputer tidak berat

**Minus:**
- ❌ Butuh internet
- ❌ Data dikirim ke server Google

#### Setup

1. **Daftar gratis** di https://aistudio.google.com/apikey
2. **Buat API Key** (gratis, tidak butuh kartu kredit)
3. **Set environment variable** sebelum jalankan app:

   **Linux/Mac:**
   ```bash
   export GEMINI_API_KEY="kunci-kamu"
   python app.py
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:GEMINI_API_KEY="kunci-kamu"
   python app.py
   ```

4. Selesai — tombol AI akan otomatis muncul.

---

### 💻 Opsi B: Ollama (Lokal, GRATIS, Private)

**Plus:**
- ✅ 100% lokal, data tidak keluar dari komputer
- ✅ Bisa offline
- ✅ Tidak ada rate limit

**Minus:**
- ❌ Install ~2.5 GB
- ❌ Komputer lebih berat saat jalan
- ❌ Lebih lambat dari cloud

#### Setup

1. Install dari https://ollama.com
2. Pull model AI:
   ```bash
   ollama pull qwen3:4b
   ```
3. Pastikan Ollama running:
   ```bash
   ollama serve
   ```
4. Jalankan aplikasi seperti biasa.

#### Pilihan Model Ollama

| Model              | Ukuran  | Kualitas | Catatan                           |
|--------------------|---------|----------|-----------------------------------|
| `qwen3:8b`         | ~5 GB   | ⭐⭐⭐⭐⭐ | Terbaik untuk akurasi             |
| **`qwen3:4b`** ⭐  | ~2.5 GB | ⭐⭐⭐⭐  | **Default — balance terbaik**     |
| `qwen3:1.7b`       | ~1 GB   | ⭐⭐⭐    | Sangat ringan                     |
| `llama3.3:latest`  | ~40 GB  | ⭐⭐⭐⭐⭐ | Butuh GPU besar                   |

---

### Auto-Detect Provider

Default `REKAPIN_AI_PROVIDER=auto` artinya:
1. Kalau `GEMINI_API_KEY` diset → **pakai Gemini**
2. Kalau Ollama running → **pakai Ollama**
3. Tidak ada keduanya → tombol AI tidak muncul

Paksa pakai provider tertentu:
```bash
REKAPIN_AI_PROVIDER=gemini python app.py    # paksa Gemini
REKAPIN_AI_PROVIDER=ollama python app.py    # paksa Ollama
```

---

### Environment Variables

| Variable             | Default                    | Keterangan                              |
|----------------------|----------------------------|-----------------------------------------|
| `REKAPIN_AI_PROVIDER`| `auto`                     | `auto` / `gemini` / `ollama`            |
| `GEMINI_API_KEY`     | _(kosong)_                 | API key dari Google AI Studio           |
| `GEMINI_MODEL`       | `gemini-2.0-flash`         | Nama model Gemini                       |
| `REKAPIN_AI_MODEL`   | `qwen3:4b`                 | Nama model Ollama                       |
| `REKAPIN_AI_URL`     | `http://localhost:11434`   | Endpoint Ollama                         |
| `REKAPIN_AI_TIMEOUT` | `120`                      | Request timeout (detik)                 |

> Lihat `.env.example` untuk template lengkap.

---

## Deploy ke Railway

1. Push repo ke GitHub
2. Buka [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Pilih repo ini → Railway auto-detect Python & deploy
4. (Opsional) Tambah environment variable `GEMINI_API_KEY` di **Settings → Variables**
   untuk mengaktifkan fitur AI di production
5. Selesai

> **Catatan:** Untuk Railway, pakai **Gemini** (cloud) — bukan Ollama (lokal).
> Railway tidak punya GPU/RAM cukup untuk LLM lokal.

---

## Struktur File

```
rekap-rek/
├── app.py                       # Flask web server (routes, session)
├── rekap_rek.py                 # Parser PDF (BCA, BRI, Mandiri, BNI) + Excel builder
├── ai_helper.py                 # Multi-provider AI (Gemini + Ollama)
├── templates/
│   └── index.html               # Single-page UI
├── setup_dan_jalankan.bat       # Auto-installer Windows
├── setup_dan_jalankan.command   # Auto-installer macOS/Linux
├── .env.example                 # Template environment variables
├── requirements.txt
└── railway.json
```
