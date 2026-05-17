"""
ai_helper.py — Multi-Provider AI untuk Rekapin
================================================
Versi 4.0 — support 2 provider:
  - Google Gemini (cloud, gratis dengan free tier yang generous)
  - Ollama (lokal, gratis, private)

Auto-detect:
  - Kalau GEMINI_API_KEY diset → pakai Gemini (cloud)
  - Kalau Ollama running       → pakai Ollama (lokal)
  - Bisa dipaksa via REKAPIN_AI_PROVIDER

Konfigurasi via environment variable:

  REKAPIN_AI_PROVIDER  = "gemini" | "ollama" | "auto" (default: auto)

  ── Gemini ──
  GEMINI_API_KEY       = API key dari https://aistudio.google.com/apikey (gratis)
  GEMINI_MODEL         = nama model (default: gemini-2.0-flash)

  ── Ollama ──
  REKAPIN_AI_MODEL     = nama model (default: qwen3:4b)
  REKAPIN_AI_URL       = endpoint Ollama (default: http://localhost:11434)
  REKAPIN_AI_TIMEOUT   = timeout dalam detik (default: 120)
"""
import os, requests, json, logging, re

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
PROVIDER_PREF = os.environ.get("REKAPIN_AI_PROVIDER", "auto").lower().strip()

# Gemini config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models"

# Ollama config
OLLAMA_URL      = os.environ.get("REKAPIN_AI_URL", "http://localhost:11434")
PREFERRED_MODEL = os.environ.get("REKAPIN_AI_MODEL", "qwen3:4b")
TIMEOUT         = int(os.environ.get("REKAPIN_AI_TIMEOUT", "120"))

# Daftar model fallback Ollama urut prioritas (kualitas vs ukuran)
FALLBACK_CHAIN = [
    "qwen3:8b", "qwen3:4b", "qwen3:1.7b",
    "llama3.3:latest", "llama3.2:3b", "llama3.1:8b",
    "qwen2.5:7b", "qwen2.5:3b",
    "gemma3:4b", "gemma2:9b",
    "phi4:latest", "mistral:latest",
    "qwen2.5:0.5b",
]

MODEL = PREFERRED_MODEL
_MODEL_CACHE = None
_PROVIDER_CACHE = None


# ── Provider detection ────────────────────────────────────────────────────────
def current_provider() -> str | None:
    """
    Tentukan provider AI yang aktif.
    Returns: "gemini" | "ollama" | None
    """
    global _PROVIDER_CACHE

    # Kalau user paksa pakai provider tertentu
    if PROVIDER_PREF == "gemini":
        return "gemini" if _gemini_ready() else None
    if PROVIDER_PREF == "ollama":
        return "ollama" if _ollama_ready() else None

    # Auto: cek Gemini dulu (cloud, lebih cepat & akurat),
    # baru fallback ke Ollama (lokal)
    if _gemini_ready():
        _PROVIDER_CACHE = "gemini"
        return "gemini"
    if _ollama_ready():
        _PROVIDER_CACHE = "ollama"
        return "ollama"
    _PROVIDER_CACHE = None
    return None


def _gemini_ready() -> bool:
    return bool(GEMINI_API_KEY)


def _ollama_ready() -> bool:
    return _ollama_current_model() is not None


# ── Ollama helpers (lokal) ────────────────────────────────────────────────────
def _ollama_available_models() -> list[str]:
    """Ambil daftar model yang sudah ter-pull di Ollama lokal."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if r.status_code != 200:
            return []
        return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except Exception:
        return []


def _ollama_current_model() -> str | None:
    """Pilih model Ollama terbaik yang tersedia."""
    global _MODEL_CACHE, MODEL
    models = _ollama_available_models()
    if not models:
        _MODEL_CACHE = None
        return None
    if PREFERRED_MODEL in models:
        _MODEL_CACHE = PREFERRED_MODEL
    else:
        chosen = None
        for fb in FALLBACK_CHAIN:
            if fb in models:
                chosen = fb
                break
        _MODEL_CACHE = chosen or models[0]
    MODEL = _MODEL_CACHE
    return _MODEL_CACHE


# ── Public API ────────────────────────────────────────────────────────────────
def is_available() -> bool:
    """Cek apakah ada provider AI yang siap dipakai."""
    return current_provider() is not None


def current_model() -> str | None:
    """Nama model yang sedang dipakai (untuk display di UI)."""
    p = current_provider()
    if p == "gemini":
        return GEMINI_MODEL
    if p == "ollama":
        return _ollama_current_model()
    return None


def status() -> dict:
    """Status lengkap untuk endpoint /ai-status (debugging)."""
    p = current_provider()
    if p is None:
        return {
            "active": False,
            "provider": None,
            "reason": "Tidak ada AI provider yang siap. "
                      "Set GEMINI_API_KEY (cloud, gratis) atau jalankan Ollama (lokal).",
        }
    if p == "gemini":
        return {
            "active": True,
            "provider": "gemini",
            "model": GEMINI_MODEL,
            "reason": f"Google Gemini ({GEMINI_MODEL}) siap dipakai",
        }
    if p == "ollama":
        models = _ollama_available_models()
        return {
            "active": True,
            "provider": "ollama",
            "model": _ollama_current_model(),
            "preferred": PREFERRED_MODEL,
            "available_models": models,
            "url": OLLAMA_URL,
            "reason": f"Ollama lokal ({_ollama_current_model()}) siap dipakai",
        }
    return {"active": False}


# ── Schema untuk structured output ────────────────────────────────────────────
KATEGORI_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "no"      : {"type": "integer"},
                    "kategori": {"type": "string", "enum": ["Penjualan", "Non penjualan"]},
                    "customer": {"type": "string"},
                },
                "required": ["no", "kategori", "customer"],
            },
        }
    },
    "required": ["results"],
}

# Gemini pakai schema slightly different (tanpa "additionalProperties")
GEMINI_KATEGORI_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "no"      : {"type": "integer"},
                    "kategori": {"type": "string", "enum": ["Penjualan", "Non penjualan"]},
                    "customer": {"type": "string"},
                },
                "required": ["no", "kategori", "customer"],
            },
        }
    },
    "required": ["results"],
}


# ── Provider-specific request handlers ────────────────────────────────────────
def _ask_gemini(prompt: str, schema: dict | None = None) -> str | None:
    """Kirim prompt ke Google Gemini API."""
    if not GEMINI_API_KEY:
        return None

    url = f"{GEMINI_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
        },
    }
    if schema is not None:
        payload["generationConfig"]["responseMimeType"] = "application/json"
        payload["generationConfig"]["responseSchema"]   = schema

    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        candidates = data.get("candidates", [])
        if not candidates:
            log.warning(f"[AI/Gemini] Tidak ada candidates di response: {data}")
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None
        return parts[0].get("text", "").strip()
    except requests.HTTPError as e:
        try:
            err_body = e.response.json() if e.response is not None else {}
        except Exception:
            err_body = {}
        log.error(f"[AI/Gemini] HTTP error: {e} — {err_body}")
        return None
    except Exception as e:
        log.error(f"[AI/Gemini] Request gagal: {e}")
        return None


def _ask_ollama(prompt: str, schema: dict | None = None) -> str | None:
    """Kirim prompt ke Ollama lokal."""
    model = _ollama_current_model()
    if not model:
        log.error("[AI/Ollama] Tidak ada model yang terinstall")
        return None

    payload: dict = {
        "model"  : model,
        "prompt" : prompt,
        "stream" : False,
        "options": {
            "temperature": 0.1,
            "num_ctx"    : 4096,
        },
    }
    if schema is not None:
        payload["format"] = schema

    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.HTTPError as e:
        # Versi Ollama lama mungkin belum support `format`. Retry tanpa format.
        if schema is not None and e.response is not None and e.response.status_code == 400:
            log.warning("[AI/Ollama] Tidak support 'format', fallback ke prompt biasa")
            payload.pop("format", None)
            try:
                r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=TIMEOUT)
                r.raise_for_status()
                return r.json().get("response", "").strip()
            except Exception as e2:
                log.error(f"[AI/Ollama] Retry tanpa format gagal: {e2}")
                return None
        log.error(f"[AI/Ollama] HTTP error: {e}")
        return None
    except Exception as e:
        log.error(f"[AI/Ollama] Request gagal: {e}")
        return None


def _ask(prompt: str, structured: bool = False) -> str | None:
    """
    Dispatcher: pakai provider yang aktif.
    Args:
        prompt: input prompt
        structured: kalau True, minta JSON output sesuai KATEGORI_SCHEMA
    """
    p = current_provider()
    if p == "gemini":
        return _ask_gemini(prompt, GEMINI_KATEGORI_SCHEMA if structured else None)
    if p == "ollama":
        return _ask_ollama(prompt, KATEGORI_SCHEMA if structured else None)
    log.error("[AI] Tidak ada provider yang aktif")
    return None


# ── High-level functions ──────────────────────────────────────────────────────
def kategorisasi_batch(transactions: list) -> list | None:
    """
    Kategorisasi transaksi secara batch menggunakan AI.
    Input : list dict dengan key 'no', 'desc', 'kredit', 'debet'
    Output: list dict {'no', 'kategori', 'customer'} atau None jika gagal
    """
    if not transactions:
        return []

    provider = current_provider()
    if not provider:
        log.error("[AI] Tidak ada provider yang aktif untuk kategorisasi")
        return None

    # Gemini bisa handle batch lebih besar (context window jauh lebih luas)
    BATCH = 50 if provider == "gemini" else 30
    results = []

    for i in range(0, len(transactions), BATCH):
        chunk = transactions[i:i + BATCH]
        lines = "\n".join(
            f"{t['no']}. [{'+Rp' if t.get('kredit', 0) else '-Rp'}{max(t.get('kredit',0), t.get('debet',0)):,.0f}] {t['desc']}"
            for t in chunk
        )

        prompt = f"""Kamu adalah asisten akuntansi yang menganalisis transaksi rekening koran bank Indonesia.

Tugas:
1. Tentukan kategori untuk setiap transaksi:
   - "Penjualan"     = uang MASUK (kredit/+Rp) dari customer atas penjualan barang/jasa
   - "Non penjualan" = transfer pribadi, setoran tunai pemilik, bunga bank, biaya admin/pajak,
                       pembayaran hutang/cicilan, refund, top-up e-wallet, dll
2. Untuk setiap "Penjualan", ekstrak nama customer dari deskripsi:
   - Nama biasanya setelah kata: DARI, FROM, TRF DR, TRANSFER DARI, SETORAN
   - Abaikan kode rekening, nomor referensi, kode bank
   - Bersihkan: hilangkan "PT", "CV", "TBK" jika tidak menjadikan nama ambigu
3. Untuk "Non penjualan", customer = "" (kosong)

Transaksi:
{lines}

Balas dengan JSON yang sesuai schema. Jangan tambahkan teks/penjelasan lain."""

        resp = _ask(prompt, structured=True)
        if not resp:
            log.warning(f"[AI] Batch {i // BATCH + 1} gagal, skip")
            continue

        batch_result = _parse_batch_response(resp)
        if batch_result:
            results.extend(batch_result)
            log.info(f"[AI/{provider}] Batch {i // BATCH + 1}: {len(batch_result)} transaksi dikategorikan")
        else:
            log.warning(f"[AI/{provider}] Tidak ada hasil valid dari batch {i // BATCH + 1}")

    return results if results else None


def _parse_batch_response(resp: str) -> list:
    """
    Parse response. Mendukung 3 format:
    1. {"results": [...]}              ← structured output (Gemini & Ollama)
    2. [...]                            ← plain JSON array
    3. ```json\n{...}\n``` markdown    ← model lama yang wrap dengan markdown
    """
    if not resp:
        return []

    resp = resp.strip()
    resp = re.sub(r"^```(?:json)?\s*", "", resp)
    resp = re.sub(r"\s*```$", "", resp)

    try:
        obj = json.loads(resp)
        if isinstance(obj, dict) and "results" in obj:
            return obj["results"]
        if isinstance(obj, list):
            return obj
    except json.JSONDecodeError:
        pass

    m = re.search(r"\{.*\"results\".*\}", resp, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group())
            if isinstance(obj, dict) and "results" in obj:
                return obj["results"]
        except json.JSONDecodeError:
            pass

    m = re.search(r"\[.*\]", resp, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group())
            if isinstance(obj, list):
                return obj
        except json.JSONDecodeError:
            pass

    return []


def generate_summary(meta: dict, transactions: list) -> str | None:
    """
    Generate ringkasan laporan keuangan dalam Bahasa Indonesia.
    """
    penj   = [t for t in transactions if t.get('kategori') == 'Penjualan']
    total_p = sum(t.get('kredit', 0) for t in penj)
    total_k = sum(t.get('kredit', 0) for t in transactions)
    total_d = sum(t.get('debet', 0) for t in transactions)

    by_cust = {}
    for t in penj:
        c = t.get('customer') or 'Tidak diketahui'
        by_cust[c] = by_cust.get(c, 0) + t.get('kredit', 0)
    top3 = sorted(by_cust.items(), key=lambda x: x[1], reverse=True)[:3]
    top3_str = ", ".join(f"{n} (Rp {v/1e6:.1f}jt)" for n, v in top3)

    prompt = f"""Buatkan ringkasan laporan keuangan singkat (3-4 kalimat) dalam Bahasa Indonesia yang profesional namun mudah dipahami.

Data:
- Nama perusahaan : {meta.get('companyName', '-')}
- Periode         : {meta.get('period', '-')}
- Bank            : {meta.get('bank', '-')}
- Total kredit    : Rp {total_k/1e6:.2f} juta
- Total debet     : Rp {total_d/1e6:.2f} juta
- Total penjualan : Rp {total_p/1e6:.2f} juta ({len(penj)} transaksi)
- Top 3 customer  : {top3_str or '-'}
- Saldo akhir     : Rp {meta.get('closing',0)/1e6:.2f} juta

Tulis ringkasan:"""

    return _ask(prompt, structured=False)
