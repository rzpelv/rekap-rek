"""
ai_helper.py — Integrasi Ollama (Local AI) untuk Rekapin
Model: Qwen2.5:7b | by rezapelvian v2.0
"""
import os, requests, json, logging, re

log = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
PREFERRED_MODEL = os.environ.get("REKAPIN_AI_MODEL", "qwen2.5:0.5b")
MODEL      = PREFERRED_MODEL
TIMEOUT    = 90  # detik
_MODEL_CACHE = None


def _available_models() -> list[str]:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        if r.status_code != 200:
            return []
        return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except Exception:
        return []


def current_model() -> str | None:
    """Pilih model yang tersedia di Ollama."""
    global _MODEL_CACHE, MODEL
    models = _available_models()
    if not models:
        _MODEL_CACHE = None
        return None
    if PREFERRED_MODEL in models:
        _MODEL_CACHE = PREFERRED_MODEL
    elif MODEL in models:
        _MODEL_CACHE = MODEL
    else:
        _MODEL_CACHE = models[0]
    MODEL = _MODEL_CACHE
    return _MODEL_CACHE


def is_available() -> bool:
    """Cek apakah Ollama dan minimal satu model AI siap dipakai."""
    return current_model() is not None


def _ask(prompt: str) -> str | None:
    """Kirim prompt ke Ollama, kembalikan teks response."""
    model = current_model()
    if not model:
        log.error("[AI] Tidak ada model Ollama terinstall")
        return None
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        log.error(f"[AI] Request gagal: {e}")
        return None


def kategorisasi_batch(transactions: list) -> list | None:
    """
    Kategorisasi transaksi secara batch menggunakan AI.
    Input : list dict dengan key 'no', 'desc', 'kredit', 'debet'
    Output: list dict {'no', 'kategori', 'customer'} atau None jika gagal
    """
    if not transactions:
        return []

    # Proses per 40 transaksi agar tidak melebihi context window
    BATCH = 40
    results = []

    for i in range(0, len(transactions), BATCH):
        chunk = transactions[i:i + BATCH]
        lines = "\n".join(
            f"{t['no']}. [{'+Rp' if t.get('kredit',0) else '-Rp'}] {t['desc']}"
            for t in chunk
        )

        prompt = f"""Kamu adalah asisten akuntansi yang menganalisis transaksi rekening koran bank Indonesia.

Tugasmu:
1. Tentukan kategori: "Penjualan" atau "Non penjualan"
   - "Penjualan" = uang MASUK (kredit) dari penjualan barang/jasa ke customer
   - "Non penjualan" = transfer biasa, setoran tunai, bunga, biaya admin, pembayaran hutang, dll
2. Jika "Penjualan", ekstrak nama customer dari deskripsi transaksi.
   - Nama customer biasanya setelah kata: DARI, FROM, TRF, TRANSFER, SETORAN
   - Abaikan kode rekening atau nomor referensi

Format output HANYA JSON array seperti ini (tanpa penjelasan lain):
[{{"no":1,"kategori":"Penjualan","customer":"Nama Customer"}},{{"no":2,"kategori":"Non penjualan","customer":""}}]

Transaksi:
{lines}

Output JSON:"""

        resp = _ask(prompt)
        if not resp:
            log.warning(f"[AI] Batch {i//BATCH+1} gagal, skip")
            continue

        # Ekstrak JSON dari response
        try:
            m = re.search(r'\[.*?\]', resp, re.DOTALL)
            if m:
                batch_result = json.loads(m.group())
                results.extend(batch_result)
                log.info(f"[AI] Batch {i//BATCH+1}: {len(batch_result)} transaksi dikategorikan")
            else:
                log.warning(f"[AI] Tidak ada JSON ditemukan di response batch {i//BATCH+1}")
        except json.JSONDecodeError as e:
            log.error(f"[AI] JSON parse error batch {i//BATCH+1}: {e}")

    return results if results else None


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
