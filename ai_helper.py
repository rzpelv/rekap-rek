"""
ai_helper.py — Integrasi Ollama (Local AI) untuk Rekapin
==========================================================
Versi 3.0 — pakai model Ollama 2026 + Structured Outputs.

Default model: qwen3:4b (Qwen3 — multilingual yang bagus untuk Bahasa Indonesia,
ringan untuk dijalankan di CPU/GPU consumer).

Fallback chain (kalau preferred model tidak ada):
  qwen3:8b > qwen3:4b > qwen3:1.7b > llama3.3:latest > llama3.2:3b > llama3.1:8b
  > qwen2.5:7b > qwen2.5:3b > gemma3:4b > gemma2:9b > phi4:latest > mistral:latest
  > qwen2.5:0.5b > model lain yang ada

Override via env var:
  REKAPIN_AI_MODEL   = nama model spesifik (mis. "llama3.3:70b")
  REKAPIN_AI_URL     = endpoint Ollama (default http://localhost:11434)
  REKAPIN_AI_TIMEOUT = timeout dalam detik (default 120)
"""
import os, requests, json, logging, re

log = logging.getLogger(__name__)

OLLAMA_URL      = os.environ.get("REKAPIN_AI_URL", "http://localhost:11434")
PREFERRED_MODEL = os.environ.get("REKAPIN_AI_MODEL", "qwen3:4b")
TIMEOUT         = int(os.environ.get("REKAPIN_AI_TIMEOUT", "120"))

# Daftar model fallback urut prioritas (kualitas vs ukuran).
# Diutamakan model 2025-2026 dengan dukungan instruksi & JSON yang baik.
FALLBACK_CHAIN = [
    "qwen3:8b",
    "qwen3:4b",
    "qwen3:1.7b",
    "llama3.3:latest",
    "llama3.2:3b",
    "llama3.1:8b",
    "qwen2.5:7b",
    "qwen2.5:3b",
    "gemma3:4b",
    "gemma2:9b",
    "phi4:latest",
    "mistral:latest",
    "qwen2.5:0.5b",
]

MODEL = PREFERRED_MODEL
_MODEL_CACHE = None


def _available_models() -> list[str]:
    """Ambil daftar model yang sudah ter-pull di Ollama lokal."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if r.status_code != 200:
            return []
        return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except Exception:
        return []


def current_model() -> str | None:
    """
    Pilih model terbaik yang tersedia.
    Urutan: PREFERRED_MODEL → FALLBACK_CHAIN → model pertama yang terinstall.
    """
    global _MODEL_CACHE, MODEL
    models = _available_models()
    if not models:
        _MODEL_CACHE = None
        return None

    # 1. Preferred model exact match
    if PREFERRED_MODEL in models:
        _MODEL_CACHE = PREFERRED_MODEL
    else:
        # 2. Fallback chain (cari model 2026 yang ada)
        chosen = None
        for fb in FALLBACK_CHAIN:
            if fb in models:
                chosen = fb
                break
        # 3. Last resort: model pertama yang ada
        _MODEL_CACHE = chosen or models[0]

    MODEL = _MODEL_CACHE
    return _MODEL_CACHE


def is_available() -> bool:
    """Cek apakah Ollama running dan minimal satu model siap."""
    return current_model() is not None


def status() -> dict:
    """Status lengkap untuk endpoint /ai-status (debugging)."""
    models = _available_models()
    if not models:
        return {
            "active": False,
            "reason": "Ollama tidak terdeteksi. Jalankan 'ollama serve' dan pull model.",
            "url": OLLAMA_URL,
        }
    chosen = current_model()
    return {
        "active": True,
        "model": chosen,
        "preferred": PREFERRED_MODEL,
        "available_models": models,
        "url": OLLAMA_URL,
    }


def _ask(prompt: str, format_schema: dict | None = None) -> str | None:
    """
    Kirim prompt ke Ollama, kembalikan teks response.

    Args:
        prompt: input prompt
        format_schema: JSON schema untuk Ollama Structured Outputs.
                       Bila None, response berupa teks bebas.
    """
    model = current_model()
    if not model:
        log.error("[AI] Tidak ada model Ollama yang terinstall")
        return None

    payload: dict = {
        "model"  : model,
        "prompt" : prompt,
        "stream" : False,
        "options": {
            "temperature": 0.1,   # rendah = lebih deterministik untuk klasifikasi
            "num_ctx"    : 4096,  # context window cukup untuk batch transaksi
        },
    }
    if format_schema is not None:
        payload["format"] = format_schema

    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except requests.HTTPError as e:
        # Versi Ollama lama mungkin belum support `format`. Retry tanpa format.
        if format_schema is not None and e.response is not None and e.response.status_code == 400:
            log.warning("[AI] Ollama tidak support 'format', fallback ke prompt biasa")
            payload.pop("format", None)
            try:
                r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=TIMEOUT)
                r.raise_for_status()
                return r.json().get("response", "").strip()
            except Exception as e2:
                log.error(f"[AI] Retry tanpa format gagal: {e2}")
                return None
        log.error(f"[AI] HTTP error: {e}")
        return None
    except Exception as e:
        log.error(f"[AI] Request gagal: {e}")
        return None


# JSON schema untuk Ollama Structured Outputs.
# Ollama menjamin response sesuai schema ini, jadi tidak perlu regex parsing.
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


def kategorisasi_batch(transactions: list) -> list | None:
    """
    Kategorisasi transaksi secara batch menggunakan AI.
    Input : list dict dengan key 'no', 'desc', 'kredit', 'debet'
    Output: list dict {'no', 'kategori', 'customer'} atau None jika gagal
    """
    if not transactions:
        return []

    # Batch lebih kecil untuk akurasi lebih tinggi & masuk context window
    BATCH = 30
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

        resp = _ask(prompt, format_schema=KATEGORI_SCHEMA)
        if not resp:
            log.warning(f"[AI] Batch {i // BATCH + 1} gagal, skip")
            continue

        batch_result = _parse_batch_response(resp)
        if batch_result:
            results.extend(batch_result)
            log.info(f"[AI] Batch {i // BATCH + 1}: {len(batch_result)} transaksi dikategorikan (model: {MODEL})")
        else:
            log.warning(f"[AI] Tidak ada hasil valid dari batch {i // BATCH + 1}")

    return results if results else None


def _parse_batch_response(resp: str) -> list:
    """
    Parse response dari Ollama. Mendukung 2 format:
    1. Structured output: {"results": [...]}
    2. Plain JSON array: [...] (untuk versi Ollama lama tanpa format support)
    """
    if not resp:
        return []

    # Strip markdown code fence kalau ada
    resp = resp.strip()
    resp = re.sub(r"^```(?:json)?\s*", "", resp)
    resp = re.sub(r"\s*```$", "", resp)

    # Coba parse seluruh response sebagai JSON
    try:
        obj = json.loads(resp)
        if isinstance(obj, dict) and "results" in obj:
            return obj["results"]
        if isinstance(obj, list):
            return obj
    except json.JSONDecodeError:
        pass

    # Fallback: cari array atau object di dalam response
    # Coba cari object dengan "results" dulu
    m = re.search(r"\{.*\"results\".*\}", resp, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group())
            if isinstance(obj, dict) and "results" in obj:
                return obj["results"]
        except json.JSONDecodeError:
            pass

    # Lalu cari plain array
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

    # Top 3 customer
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

    return _ask(prompt)
