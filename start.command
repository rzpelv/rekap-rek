#!/bin/bash
# ╔══════════════════════════════════════════════╗
# ║        REKAPIN v2.0 — Start App              ║
# ║           by rezapelvian                     ║
# ╚══════════════════════════════════════════════╝

clear
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║        REKAPIN v2.0 🚀                       ║"
echo "║           by rezapelvian                     ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"
AI_MODEL="qwen2.5:0.5b"
export REKAPIN_AI_MODEL="$AI_MODEL"

# Cek .venv
if [ ! -f ".venv/bin/python" ]; then
    echo "❌ Virtual environment tidak ditemukan!"
    echo "   Jalankan install.command terlebih dahulu."
    echo ""
    read -p "Tekan Enter untuk keluar..."
    exit 1
fi

# ─── Start Ollama AI ──────────────────────────────────────────────────────
echo "🤖 Menjalankan AI Engine (Ollama + $AI_MODEL)..."
if command -v ollama &>/dev/null; then
    # Cek apakah Ollama sudah berjalan
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        echo "   ✅ AI Engine sudah aktif"
    else
        ollama serve &>/dev/null &
        OLLAMA_PID=$!
        sleep 3
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            echo "   ✅ AI Engine aktif (PID: $OLLAMA_PID)"
        else
            echo "   ⚠️  AI Engine gagal start — app tetap jalan tanpa AI"
            OLLAMA_PID=""
        fi
    fi
    if curl -s http://localhost:11434/api/tags | grep -q "\"name\":\"$AI_MODEL\""; then
        echo "   ✅ Model AI $AI_MODEL tersedia"
    else
        echo "   ⚠️  Model AI $AI_MODEL belum terinstall"
        echo "      Jalankan install.command atau: ollama pull $AI_MODEL"
    fi
else
    echo "   ⚠️  Ollama tidak ditemukan — app jalan tanpa AI"
    echo "      Install dengan: brew install ollama"
    OLLAMA_PID=""
fi

# ─── Start Flask Server ───────────────────────────────────────────────────
echo ""
echo "🌐 Menjalankan Rekapin Server..."
.venv/bin/python app.py &
FLASK_PID=$!
sleep 2

# Cek Flask berhasil jalan
if kill -0 $FLASK_PID 2>/dev/null; then
    echo "   ✅ Server aktif — http://localhost:8080"
else
    echo "   ❌ Server gagal start. Cek error di atas."
    read -p "Tekan Enter untuk keluar..."
    exit 1
fi

# ─── Buka Browser ────────────────────────────────────────────────────────
echo ""
echo "🔗 Membuka browser..."
sleep 1
open http://localhost:8080

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ Rekapin berjalan!                        ║"
echo "║     → http://localhost:8080                  ║"
echo "║                                              ║"
echo "║  Tekan Ctrl+C untuk menghentikan app         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ─── Tunggu & Cleanup saat keluar ────────────────────────────────────────
cleanup() {
    echo ""
    echo "🛑 Menghentikan server..."
    kill $FLASK_PID 2>/dev/null
    [ -n "$OLLAMA_PID" ] && kill $OLLAMA_PID 2>/dev/null
    echo "   ✅ Server dihentikan. Sampai jumpa!"
    exit 0
}
trap cleanup INT TERM

wait $FLASK_PID
