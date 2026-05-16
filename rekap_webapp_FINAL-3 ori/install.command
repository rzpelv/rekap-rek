#!/bin/bash
# ╔══════════════════════════════════════════════╗
# ║      REKAPIN INSTALLER v2.0 — Mac Edition    ║
# ║           by rezapelvian                     ║
# ╚══════════════════════════════════════════════╝

clear
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║      REKAPIN INSTALLER v2.0 — Mac Edition    ║"
echo "║           by rezapelvian                     ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Pindah ke folder script ini berada
cd "$(dirname "$0")"
APP_DIR="$(pwd)"

# ─── 1. Cek Python3 ────────────────────────────────────────────────────────
echo "🔍 [1/5] Mengecek Python..."
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 tidak ditemukan!"
    echo "   Membuka halaman download Python..."
    open "https://python.org/downloads"
    echo ""
    read -p "   Setelah install Python, tekan Enter untuk lanjut..."
fi
PYTHON_VER=$(python3 --version 2>&1)
echo "   ✅ $PYTHON_VER"

# ─── 2. Virtual Environment ────────────────────────────────────────────────
echo ""
echo "📦 [2/5] Membuat virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "   ✅ .venv berhasil dibuat"
else
    echo "   ✅ .venv sudah ada, skip"
fi

# ─── 3. Install Python Libraries ───────────────────────────────────────────
echo ""
echo "📥 [3/5] Menginstall library Python..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q
echo "   ✅ Semua library terinstall"

# ─── 4. Install Ollama ─────────────────────────────────────────────────────
echo ""
echo "🤖 [4/5] Mengecek Ollama (Local AI Engine)..."
if ! command -v ollama &>/dev/null; then
    echo "   📥 Menginstall Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    if [ $? -ne 0 ]; then
        echo "   ⚠️  Auto-install gagal. Coba manual:"
        echo "      brew install ollama"
        echo "      atau download dari: https://ollama.com/download"
        open "https://ollama.com/download/mac"
        echo ""
        read -p "   Setelah install Ollama, tekan Enter untuk lanjut..."
    fi
else
    echo "   ✅ Ollama sudah terinstall ($(ollama --version 2>/dev/null || echo 'versi tidak diketahui'))"
fi

# ─── 5. Download Model AI ──────────────────────────────────────────────────
echo ""
echo "🧠 [5/5] Mendownload model AI: Qwen2.5 7B"
echo "   ⚠️  Ukuran ~4.7GB — butuh waktu tergantung kecepatan internet"
echo "   ☕ Silakan ambil kopi dulu..."
echo ""

# Jalankan Ollama sementara untuk pull model
ollama serve &>/dev/null &
OLLAMA_PID=$!
sleep 3

ollama pull qwen2.5:7b

if [ $? -eq 0 ]; then
    echo "   ✅ Model AI Qwen2.5 7B siap!"
else
    echo "   ⚠️  Download model gagal. Coba jalankan manual:"
    echo "      ollama pull qwen2.5:7b"
fi

kill $OLLAMA_PID 2>/dev/null
wait $OLLAMA_PID 2>/dev/null

# ─── Selesai ───────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║           INSTALASI SELESAI! ✅              ║"
echo "║                                              ║"
echo "║  Cara menjalankan app:                       ║"
echo "║  → Double-click file: start.command          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
read -p "Tekan Enter untuk keluar..."
