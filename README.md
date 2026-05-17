# Rekapin — Rekap Rekening Koran → Excel

Upload PDF e-statement bank, otomatis diproses jadi file Excel rekap dengan:

- Rekap per bulan (debet, kredit, penjualan)
- Kategorisasi otomatis: **Penjualan** vs **Non penjualan**
- Ekstraksi nama customer dari deskripsi transaksi
- Sheet "Edit Penjualan" dengan dropdown untuk koreksi manual
- Sheet "Customer Summary" dengan formula `SUMIFS` auto-update
- **Integrasi AI (opsional)** untuk kategorisasi & ekstraksi customer yang lebih akurat

**Bank yang didukung:** BCA, BRI Giro, BRI Pinjaman, Mandiri, BNI

---

## Jalankan Lokal

```bash
git clone https://github.com/rzpelv/rekap-rek.git
cd rekap-rek
pip install -r requirements.txt
python app.py
```

Buka **http://localhost:5000**

---

## Integrasi AI (opsional)

Aplikasi punya tombol "Tingkatkan dengan AI" di halaman Review yang akan
mengirim transaksi ke LLM untuk re-kategorisasi yang lebih akurat. Tombol
hanya muncul kalau API key sudah dikonfigurasi.

### Setup

Set environment variable berikut sebelum menjalankan app:

| Variable        | Wajib | Default                          | Keterangan                                  |
|-----------------|-------|----------------------------------|---------------------------------------------|
| `AI_API_KEY`    | Ya    | —                                | API key dari provider LLM                   |
| `AI_BASE_URL`   | Tidak | `https://api.openai.com/v1`      | Endpoint OpenAI-compatible                  |
| `AI_MODEL`      | Tidak | `gpt-4o-mini`                    | Nama model                                  |
| `AI_BATCH_SIZE` | Tidak | `25`                             | Jumlah transaksi per request                |
| `AI_TIMEOUT`    | Tidak | `60`                             | Timeout request (detik)                     |

### Provider yang didukung

Karena kompatibel OpenAI API, bisa pakai provider apa saja:

**OpenAI** (GPT)
```bash
export AI_API_KEY="sk-..."
# AI_BASE_URL & AI_MODEL pakai default
```

**OpenRouter** (akses multi-model: Claude, Gemini, Llama, dll)
```bash
export AI_API_KEY="sk-or-..."
export AI_BASE_URL="https://openrouter.ai/api/v1"
export AI_MODEL="anthropic/claude-3.5-haiku"
```

**Groq** (cepat & murah)
```bash
export AI_API_KEY="gsk_..."
export AI_BASE_URL="https://api.groq.com/openai/v1"
export AI_MODEL="llama-3.3-70b-versatile"
```

**Google Gemini** (via OpenAI-compat endpoint)
```bash
export AI_API_KEY="..."
export AI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"
export AI_MODEL="gemini-2.0-flash"
```

### Lokal (`.env`-style)

```bash
AI_API_KEY="sk-..." python app.py
```

### Tanpa AI

Kalau `AI_API_KEY` tidak diset, tombol AI tidak muncul dan aplikasi tetap
berfungsi normal dengan kategorisasi berbasis keyword.

---

## Deploy ke Railway

1. Push repo ke GitHub
2. Buka [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Pilih repo ini → Railway auto-detect Python & deploy
4. (Opsional) Tambah environment variable `AI_API_KEY` di Railway dashboard
   → Settings → Variables, untuk mengaktifkan fitur AI
5. Selesai

---

## Struktur File

```
rekap-rek/
├── app.py              # Flask web server (routes, session)
├── rekap_rek.py        # Parser PDF (BCA, BRI, Mandiri, BNI) + Excel builder
├── ai_helper.py        # Integrasi LLM (OpenAI-compat) untuk re-kategorisasi
├── templates/
│   └── index.html      # Single-page UI
├── requirements.txt
└── railway.json
```
