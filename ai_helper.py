"""
AI Helper untuk Rekapin
=======================
Modul ini menyediakan integrasi dengan LLM (OpenAI-compatible API) untuk:

1. Auto-kategorisasi transaksi (Penjualan / Non penjualan) yang lebih cerdas
   dari keyword matching.
2. Ekstraksi nama customer dari deskripsi transaksi yang rumit.

Konfigurasi via environment variable:
- AI_API_KEY       : API key untuk provider LLM (wajib)
- AI_BASE_URL      : Endpoint API (default: https://api.openai.com/v1)
                     Bisa diisi OpenRouter, Groq, Gemini-compat, dll.
- AI_MODEL         : Nama model (default: gpt-4o-mini)
- AI_BATCH_SIZE    : Berapa transaksi per request (default: 25)
- AI_TIMEOUT       : Request timeout dalam detik (default: 60)

Jika AI_API_KEY tidak diset, fungsi `is_ai_available()` return False
dan caller harus fallback ke logic non-AI.
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional

log = logging.getLogger(__name__)


# ── Konfigurasi ────────────────────────────────────────────────────────────
def _get_config() -> Dict[str, Any]:
    return {
        "api_key":   os.environ.get("AI_API_KEY", "").strip(),
        "base_url":  os.environ.get("AI_BASE_URL", "https://api.openai.com/v1").strip(),
        "model":     os.environ.get("AI_MODEL", "gpt-4o-mini").strip(),
        "batch_size": int(os.environ.get("AI_BATCH_SIZE", "25")),
        "timeout":   int(os.environ.get("AI_TIMEOUT", "60")),
    }


def is_ai_available() -> bool:
    """Cek apakah AI integration dikonfigurasi (ada API key)."""
    return bool(_get_config()["api_key"])


def _get_client():
    """
    Buat OpenAI client. Lazy-load supaya import tidak crash kalau
    library `openai` belum ter-install.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "Library 'openai' belum ter-install. "
            "Tambahkan 'openai>=1.0' ke requirements.txt"
        )

    cfg = _get_config()
    if not cfg["api_key"]:
        raise RuntimeError(
            "AI_API_KEY belum diset di environment variable."
        )

    return OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        timeout=cfg["timeout"],
    ), cfg


# ── Prompt Engineering ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """Kamu adalah asisten akuntansi yang membantu mengkategorikan transaksi rekening koran perusahaan dagang Indonesia.

ATURAN KATEGORISASI:
- "Penjualan"      = transaksi KREDIT (uang masuk) yang berasal dari customer / pembeli yang membayar barang/jasa.
- "Non penjualan"  = semua selain penjualan, contoh:
  * Bunga bank, jasa giro, pajak (PPh), biaya admin
  * Transfer internal antar rekening sendiri
  * Pencairan kredit / KMK / KPR / pinjaman
  * Pembayaran pokok pinjaman, pembebanan bunga
  * Refund, koreksi, reversal
  * Setoran tunai oleh pemilik
  * Semua transaksi DEBET (uang keluar)

NAMA CUSTOMER:
- Ekstrak nama PIHAK PEMBAYAR (customer) dari deskripsi transaksi.
- Untuk "Non penjualan": nama customer = "" (string kosong).
- Bersihkan nama dari kode rekening, kode referensi, dan teks sistem.
- Format: Title Case (contoh: "Toko Maju Jaya", "Cv Sumber Rejeki", "PT Lion Superindo").
- Jika nama tidak jelas, isi deskriptif singkat (contoh: "Setoran Tunai", "Transfer Antar Bank").

OUTPUT: Hanya JSON array, satu objek per transaksi, urut sama dengan input. Tidak ada teks lain."""


USER_PROMPT_TEMPLATE = """Nama rekening (perusahaan ini): {company}

Berikut transaksi-transaksi rekening koran. Untuk SETIAP transaksi, balas dengan objek:
{{"i": <index>, "kategori": "Penjualan" | "Non penjualan", "customer": "<nama atau kosong>"}}

Transaksi:
{transactions}

Balas dengan JSON array saja, tanpa penjelasan, tanpa markdown."""


# ── Core Function ──────────────────────────────────────────────────────────
def _format_transaction(idx: int, tx: Dict[str, Any]) -> str:
    """Format satu transaksi untuk dimasukkan ke prompt."""
    debet  = tx.get("debet", 0) or 0
    kredit = tx.get("kredit", 0) or 0
    direction = "KREDIT" if kredit > 0 else ("DEBET" if debet > 0 else "—")
    amount = kredit if kredit > 0 else debet
    desc = (tx.get("desc") or "").strip()
    # Truncate desc supaya prompt tidak terlalu panjang
    if len(desc) > 250:
        desc = desc[:247] + "..."
    return f'{idx}. [{direction} Rp{amount:,.0f}] {desc}'


def _parse_response(content: str, expected_count: int) -> List[Dict[str, Any]]:
    """Parse JSON response dari LLM, robust terhadap markdown wrapping."""
    if not content:
        return []

    # Buang markdown code fence kalau ada
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    # Coba parse JSON langsung
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Coba ekstrak array dari text
        m = re.search(r"\[.*\]", content, re.DOTALL)
        if not m:
            log.warning("AI response bukan JSON valid: %r", content[:200])
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            log.warning("AI response tidak bisa di-parse: %s", e)
            return []

    if not isinstance(data, list):
        log.warning("AI response bukan array: %r", type(data))
        return []

    return data


def categorize_batch(
    transactions: List[Dict[str, Any]],
    company_name: str,
) -> List[Dict[str, Any]]:
    """
    Re-kategorisasi sekumpulan transaksi via LLM.

    Args:
        transactions: list of dict, setiap dict harus punya: desc, debet, kredit
        company_name: nama perusahaan (untuk konteks LLM)

    Returns:
        list of dict dengan keys: kategori, customer
        Urutannya 1:1 dengan input. Kalau LLM gagal merespon untuk satu item,
        item tersebut akan kosong (kategori="", customer="").
    """
    if not transactions:
        return []

    client, cfg = _get_client()

    results: List[Dict[str, Any]] = [{"kategori": "", "customer": ""} for _ in transactions]
    batch_size = cfg["batch_size"]

    for batch_start in range(0, len(transactions), batch_size):
        batch = transactions[batch_start:batch_start + batch_size]

        tx_lines = "\n".join(
            _format_transaction(batch_start + i, tx)
            for i, tx in enumerate(batch)
        )
        user_prompt = USER_PROMPT_TEMPLATE.format(
            company=company_name or "(tidak diketahui)",
            transactions=tx_lines,
        )

        log.info(
            "AI batch %d-%d (%d txs)",
            batch_start, batch_start + len(batch) - 1, len(batch),
        )

        try:
            resp = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"} if "gpt" in cfg["model"].lower() else None,
            )
            content = resp.choices[0].message.content or ""
        except TypeError:
            # response_format tidak didukung oleh provider ini (mis. Groq lama)
            resp = client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.1,
            )
            content = resp.choices[0].message.content or ""
        except Exception as e:
            log.error("AI batch gagal: %s", e)
            continue

        # Beberapa model balas dengan {"data": [...]} atau {"results": [...]} kalau pakai json_object mode
        parsed_raw = content.strip()
        try:
            obj = json.loads(parsed_raw)
            if isinstance(obj, dict):
                # Ambil array di dalamnya
                for v in obj.values():
                    if isinstance(v, list):
                        parsed = v
                        break
                else:
                    parsed = []
            elif isinstance(obj, list):
                parsed = obj
            else:
                parsed = []
        except json.JSONDecodeError:
            parsed = _parse_response(parsed_raw, len(batch))

        # Map hasil berdasarkan field "i" (index global)
        for item in parsed:
            if not isinstance(item, dict):
                continue
            idx = item.get("i")
            if not isinstance(idx, int) or idx < 0 or idx >= len(transactions):
                continue
            kat = (item.get("kategori") or "").strip()
            cust = (item.get("customer") or "").strip()
            # Normalisasi
            if kat.lower() in ("penjualan", "sales"):
                kat = "Penjualan"
            elif kat.lower() in ("non penjualan", "non-penjualan", "non sales", "bukan penjualan"):
                kat = "Non penjualan"
            else:
                kat = ""
            if kat == "Non penjualan":
                cust = ""
            results[idx] = {"kategori": kat, "customer": cust}

    return results


def enrich_transactions(
    transactions: List[Dict[str, Any]],
    company_name: str,
    fallback_keep: bool = True,
) -> Dict[str, Any]:
    """
    Wrapper level-tinggi: terima list transaksi, panggil AI, kembalikan
    list transaksi yang sudah di-update dengan kategori & customer dari AI.

    Args:
        transactions: list transaksi (akan di-update in-place)
        company_name: nama rekening / perusahaan
        fallback_keep: kalau AI tidak return hasil untuk suatu transaksi,
                       pertahankan kategori/customer yang sudah ada.

    Returns:
        dict {
          "updated_count": int,    jumlah transaksi yang berubah kategorinya
          "total":         int,    total transaksi
          "errors":        list,   list pesan error (kalau ada)
        }
    """
    if not transactions:
        return {"updated_count": 0, "total": 0, "errors": []}

    errors: List[str] = []
    updated = 0

    try:
        ai_results = categorize_batch(transactions, company_name)
    except Exception as e:
        log.exception("AI enrich gagal total")
        return {"updated_count": 0, "total": len(transactions), "errors": [str(e)]}

    for tx, ai in zip(transactions, ai_results):
        new_kat  = ai.get("kategori", "")
        new_cust = ai.get("customer", "")

        if new_kat in ("Penjualan", "Non penjualan"):
            old_kat = tx.get("kategori", "")
            if old_kat != new_kat:
                updated += 1
            tx["kategori"] = new_kat
            # Untuk Penjualan, AI mungkin kasih customer name. Override.
            if new_kat == "Penjualan":
                if new_cust:
                    tx["customer"] = new_cust
                elif not fallback_keep:
                    tx["customer"] = ""
            else:
                tx["customer"] = ""
        else:
            # AI tidak berhasil — biarkan apa adanya kalau fallback_keep
            if not fallback_keep:
                errors.append(f"Tx idx unknown: AI tidak merespon kategori")

    return {
        "updated_count": updated,
        "total":         len(transactions),
        "errors":        errors,
    }
