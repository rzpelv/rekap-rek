#!/bin/bash
# Rekapin — Rekap Rekening Koran
# Klik dua kali file ini untuk menjalankan di Mac

# ── Warna terminal ────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

clear
echo ""
echo -e "${BOLD}${BLUE} ============================================${NC}"
echo -e "${BOLD}${BLUE}   Rekapin - Rekap Rekening Koran${NC}"
echo -e "${BOLD}${BLUE} ============================================${NC}"
echo ""

# ── Pindah ke folder file ini berada ─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Cek Python (python3 atau python) ─────────────────────────────────────
echo -e "${CYAN} [1/3] Memeriksa Python...${NC}"

if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo -e "${RED} [ERROR] Python tidak ditemukan!${NC}"
    echo ""
    echo " Install Python 3.8+ dari:"
    echo " https://www.python.org/downloads/"
    echo ""
    echo " Atau via Homebrew:"
    echo "   brew install python3"
    echo ""
    read -p " Tekan Enter untuk keluar..." dummy
    exit 1
fi

PY_VER=$($PY --version 2>&1)
echo -e "${GREEN} [OK] ${PY_VER}${NC}"
echo ""

# ── Install / update dependensi ──────────────────────────────────────────
echo -e "${CYAN} [2/3] Memeriksa dependensi...${NC}"
$PY -m pip install flask pdfplumber openpyxl gunicorn --quiet --upgrade 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW} [WARN] Gagal update dependensi, mencoba lanjut...${NC}"
fi
echo -e "${GREEN} [OK] Dependensi siap${NC}"
echo ""

# ── Buat folder sessions ──────────────────────────────────────────────────
mkdir -p sessions

# ── Cari port yang tersedia ───────────────────────────────────────────────
PORT=5000
while lsof -i :$PORT &>/dev/null 2>&1; do
    PORT=$((PORT+1))
done

# ── Jalankan server ───────────────────────────────────────────────────────
echo -e "${CYAN} [3/3] Menjalankan server di port $PORT...${NC}"
export PORT=$PORT

# Jalankan Flask di background
$PY app.py > logs_server.txt 2>&1 &
SERVER_PID=$!

# Tunggu server siap (max 15 detik)
TRIES=0
while [ $TRIES -lt 15 ]; do
    sleep 1
    TRIES=$((TRIES+1))
    $PY -c "import urllib.request; urllib.request.urlopen('http://localhost:$PORT')" &>/dev/null
    if [ $? -eq 0 ]; then
        break
    fi
done

# Cek apakah berhasil
$PY -c "import urllib.request; urllib.request.urlopen('http://localhost:$PORT')" &>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED} [ERROR] Server tidak merespons.${NC}"
    echo " Cek file logs_server.txt untuk detail."
    read -p " Tekan Enter untuk keluar..." dummy
    exit 1
fi

echo ""
echo -e "${BOLD}${GREEN} ============================================${NC}"
echo -e "${BOLD}${GREEN}   Server berjalan di:${NC}"
echo -e "${BOLD}${CYAN}   http://localhost:$PORT${NC}"
echo -e "${BOLD}${GREEN} ============================================${NC}"
echo ""
echo " Browser akan terbuka otomatis..."
echo " Tutup jendela ini untuk menghentikan server."
echo ""

# Buka browser di Mac
open "http://localhost:$PORT"

# Tangani Ctrl+C
trap "echo ''; echo ' Server dihentikan.'; kill $SERVER_PID 2>/dev/null; exit 0" INT TERM

# Tampilkan log live
echo " === Log Server ==="
wait $SERVER_PID
