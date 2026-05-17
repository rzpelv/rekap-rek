#!/bin/bash
# =============================================================================
#   REKAPIN — One-Click Auto Setup & Run untuk macOS / Linux
# =============================================================================
#   Script ini akan otomatis:
#   1. Cek & install Homebrew (kalau di macOS dan belum ada)
#   2. Cek & install Python (jika belum ada)
#   3. Cek & install Git (jika belum ada)
#   4. Cek & install Ollama (jika belum ada) — opsional untuk AI
#   5. Pull model AI Qwen3 (jika belum ada)
#   6. Clone/update repo dari GitHub
#   7. Buat virtual environment & install dependencies
#   8. Jalankan aplikasi & buka browser
#
#   Yang sudah terinstall akan di-bypass.
# =============================================================================

set -e

REPO_URL="https://github.com/rzpelv/rekap-rek.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR/rekap-rek"
AI_MODEL="qwen3.5:2b"
INSTALL_AI=1

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ok()   { printf "  ${GREEN}[OK]${NC} %s\n" "$1"; }
warn() { printf "  ${YELLOW}[!]${NC} %s\n" "$1"; }
err()  { printf "  ${RED}[X]${NC} %s\n" "$1"; }
info() { printf "  ${BLUE}[...]${NC} %s\n" "$1"; }

cd "$SCRIPT_DIR"

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Darwin*) OS_NAME="macOS"; PKG_MGR="brew" ;;
    Linux*)  OS_NAME="Linux"; PKG_MGR="apt"  ;;
    *)       OS_NAME="Unknown"; PKG_MGR="" ;;
esac

# Cek apakah file ini di dalam folder repo
if [ -f "$SCRIPT_DIR/app.py" ]; then
    REPO_DIR="$SCRIPT_DIR"
    echo "[INFO] Terdeteksi sudah di dalam folder repo: $REPO_DIR"
fi

clear
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "   REKAPIN — Auto Setup & Run ($OS_NAME)"
echo "   Rekap Rekening Koran PDF → Excel"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#   1. Cek package manager (Homebrew di macOS, apt di Linux)
# ─────────────────────────────────────────────────────────────────────────────
echo "[1/7] Cek package manager..."

if [ "$OS_NAME" = "macOS" ]; then
    if command -v brew >/dev/null 2>&1; then
        ok "Homebrew sudah terinstall"
    else
        warn "Homebrew belum terinstall"
        info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Tambah ke PATH session ini (Apple Silicon)
        if [ -d "/opt/homebrew/bin" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        ok "Homebrew terinstall"
    fi
elif [ "$OS_NAME" = "Linux" ]; then
    if command -v apt >/dev/null 2>&1; then
        ok "apt tersedia"
    elif command -v dnf >/dev/null 2>&1; then
        ok "dnf tersedia"
        PKG_MGR="dnf"
    else
        err "Package manager tidak dikenali. Install python3, git, ollama manual."
        PKG_MGR=""
    fi
else
    err "OS tidak dikenali ($OS)"
    exit 1
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#   2. Cek & install Python
# ─────────────────────────────────────────────────────────────────────────────
echo "[2/7] Cek Python..."
if command -v python3 >/dev/null 2>&1; then
    PYVER=$(python3 --version | awk '{print $2}')
    ok "Python $PYVER sudah terinstall"
else
    warn "Python belum terinstall"
    case "$PKG_MGR" in
        brew) info "Installing python via Homebrew..."; brew install python ;;
        apt)  info "Installing python via apt..."; sudo apt update && sudo apt install -y python3 python3-venv python3-pip ;;
        dnf)  info "Installing python via dnf..."; sudo dnf install -y python3 python3-pip ;;
        *)    err "Install Python manual dari https://python.org"; exit 1 ;;
    esac
    ok "Python terinstall"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#   3. Cek & install Git
# ─────────────────────────────────────────────────────────────────────────────
echo "[3/7] Cek Git..."
if command -v git >/dev/null 2>&1; then
    ok "Git sudah terinstall"
else
    warn "Git belum terinstall"
    case "$PKG_MGR" in
        brew) info "Installing git via Homebrew..."; brew install git ;;
        apt)  info "Installing git via apt..."; sudo apt install -y git ;;
        dnf)  info "Installing git via dnf..."; sudo dnf install -y git ;;
        *)    err "Install Git manual dari https://git-scm.com"; exit 1 ;;
    esac
    ok "Git terinstall"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#   4. Cek & install Ollama (opsional untuk fitur AI)
# ─────────────────────────────────────────────────────────────────────────────
echo "[4/7] Cek Ollama (opsional, untuk fitur AI)..."
if command -v ollama >/dev/null 2>&1; then
    ok "Ollama sudah terinstall"
else
    warn "Ollama belum terinstall"
    echo ""
    echo "  Ollama dipakai untuk fitur 'Tingkatkan dengan AI' (kategorisasi"
    echo "  transaksi otomatis pakai LLM lokal — gratis & private)."
    echo ""
    read -p "  Install Ollama sekarang? (y/n, default y): " INSTALL_AI_INPUT
    INSTALL_AI_INPUT=${INSTALL_AI_INPUT:-y}
    if [[ "$INSTALL_AI_INPUT" =~ ^[Yy]$ ]]; then
        case "$PKG_MGR" in
            brew)
                info "Installing Ollama via Homebrew..."
                brew install ollama
                ;;
            apt|dnf)
                info "Installing Ollama via official installer..."
                curl -fsSL https://ollama.com/install.sh | sh
                ;;
            *)
                warn "Download Ollama dari https://ollama.com lalu install manual"
                INSTALL_AI=0
                ;;
        esac
        if command -v ollama >/dev/null 2>&1; then
            ok "Ollama terinstall"
        else
            warn "Gagal install Ollama. Skip fitur AI."
            INSTALL_AI=0
        fi
    else
        INSTALL_AI=0
        echo "  [SKIP] Tanpa AI — aplikasi tetap jalan dengan kategorisasi keyword."
    fi
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#   5. Pastikan Ollama service running & pull model
# ─────────────────────────────────────────────────────────────────────────────
if [ "$INSTALL_AI" = "1" ] && command -v ollama >/dev/null 2>&1; then
    echo "[5/7] Cek model AI $AI_MODEL..."

    # Pastikan Ollama service running di background
    if ! pgrep -x "ollama" >/dev/null 2>&1; then
        info "Starting Ollama service di background..."
        nohup ollama serve >/tmp/ollama.log 2>&1 &
        sleep 3
    fi

    if ollama list 2>/dev/null | awk 'NR>1 {print $1}' | grep -q "^${AI_MODEL}$"; then
        ok "Model $AI_MODEL sudah ter-pull"
    else
        info "Pulling model $AI_MODEL (~1.3 GB, sekali saja)..."
        echo "        Bisa makan waktu 3-10 menit tergantung koneksi."
        ollama pull "$AI_MODEL" || warn "Gagal pull model. Aplikasi tetap jalan tanpa AI."
        ok "Model $AI_MODEL siap dipakai"
    fi
else
    echo "[5/7] Skip pull model AI (Ollama tidak diinstall)"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#   6. Clone atau update repo
# ─────────────────────────────────────────────────────────────────────────────
echo "[6/7] Sync repo dari GitHub..."
if [ -d "$REPO_DIR/.git" ]; then
    ok "Repo sudah ada, pull update terbaru..."
    (cd "$REPO_DIR" && git pull origin main)
elif [ -f "$REPO_DIR/app.py" ]; then
    ok "Folder app sudah ada (non-git), skip clone"
else
    info "Cloning repo dari $REPO_URL..."
    git clone "$REPO_URL" "$REPO_DIR"
fi
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#   7. Setup venv & install dependencies
# ─────────────────────────────────────────────────────────────────────────────
echo "[7/7] Setup virtual environment & install dependencies..."
cd "$REPO_DIR"

if [ -f "venv/bin/activate" ]; then
    ok "Virtual env sudah ada"
else
    info "Membuat virtual environment..."
    python3 -m venv venv
fi

# shellcheck source=/dev/null
source venv/bin/activate
info "Install/update dependencies..."
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
ok "Dependencies siap"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#   8. Jalankan aplikasi & buka browser
# ─────────────────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════════"
echo "   Setup selesai! Menjalankan aplikasi..."
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "   URL: http://localhost:8181"
echo ""
echo "   - Browser akan terbuka otomatis dalam 3 detik"
echo "   - Tekan Control+C (bukan Cmd+C) untuk stop server"
echo ""

# Buka browser setelah 3 detik (background)
(
    sleep 3
    if [ "$OS_NAME" = "macOS" ]; then
        open http://localhost:8181
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open http://localhost:8181
    fi
) &

# Jalankan Flask app (foreground)
python app.py

echo ""
echo "Aplikasi telah dihentikan."
