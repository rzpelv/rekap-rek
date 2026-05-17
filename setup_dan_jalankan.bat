@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title Rekapin - Auto Setup ^& Run

REM =============================================================================
REM   REKAPIN — One-Click Auto Setup ^& Run untuk Windows
REM =============================================================================
REM   File ini akan otomatis:
REM   1. Cek & install Python (jika belum ada)
REM   2. Cek & install Git (jika belum ada)
REM   3. Cek & install Ollama (jika belum ada) — opsional untuk AI
REM   4. Pull model AI Qwen3 (jika belum ada)
REM   5. Clone/update repo dari GitHub
REM   6. Buat virtual environment & install dependencies
REM   7. Jalankan aplikasi & buka browser
REM
REM   Yang sudah terinstall akan di-bypass.
REM =============================================================================

echo.
echo ═══════════════════════════════════════════════════════════════════
echo    REKAPIN — Auto Setup ^& Run
echo    Rekap Rekening Koran PDF -^> Excel
echo ═══════════════════════════════════════════════════════════════════
echo.

set "REPO_URL=https://github.com/rzpelv/rekap-rek.git"
set "REPO_DIR=%~dp0rekap-rek"
set "AI_MODEL=qwen3.5:2b"
set "INSTALL_AI=1"

REM Cek apakah file ini dijalankan dari dalam folder repo
if exist "%~dp0app.py" (
    set "REPO_DIR=%~dp0"
    echo [INFO] Terdeteksi sudah di dalam folder repo: %REPO_DIR%
)

REM ─────────────────────────────────────────────────────────────────────────────
REM   1. Cek winget (Windows Package Manager)
REM ─────────────────────────────────────────────────────────────────────────────
echo [1/7] Cek Windows Package Manager (winget)...
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] winget tidak ditemukan.
    echo   Winget biasanya sudah ada di Windows 10 1809+ dan Windows 11.
    echo   Update Windows atau install "App Installer" dari Microsoft Store.
    echo.
    echo   Tetap lanjut tanpa auto-install? Kamu harus install Python, Git
    echo   ^(opsional: Ollama^) secara manual.
    echo.
    pause
    set "NO_WINGET=1"
) else (
    echo   [OK] winget tersedia
    set "NO_WINGET=0"
)
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM   2. Cek & install Python
REM ─────────────────────────────────────────────────────────────────────────────
echo [2/7] Cek Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
    echo   [OK] Python !PYVER! sudah terinstall
) else (
    echo   [!] Python belum terinstall
    if "!NO_WINGET!"=="1" (
        echo   [X] Tidak bisa auto-install. Download dari https://python.org
        echo       Saat install, CENTANG "Add Python to PATH"
        pause
        exit /b 1
    )
    echo   [...] Installing Python 3.12 via winget...
    winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo   [X] Gagal install Python. Coba install manual dari python.org
        pause
        exit /b 1
    )
    echo   [OK] Python terinstall
    echo   [!] PENTING: Tutup CMD ini dan jalankan ulang setup_dan_jalankan.bat
    echo       supaya PATH ter-refresh.
    pause
    exit /b 0
)
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM   3. Cek & install Git
REM ─────────────────────────────────────────────────────────────────────────────
echo [3/7] Cek Git...
git --version >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Git sudah terinstall
) else (
    echo   [!] Git belum terinstall
    if "!NO_WINGET!"=="1" (
        echo   [X] Tidak bisa auto-install. Download dari https://git-scm.com
        pause
        exit /b 1
    )
    echo   [...] Installing Git via winget...
    winget install -e --id Git.Git --silent --accept-source-agreements --accept-package-agreements
    if !errorlevel! neq 0 (
        echo   [X] Gagal install Git
        pause
        exit /b 1
    )
    echo   [OK] Git terinstall
    echo   [!] PENTING: Tutup CMD ini dan jalankan ulang setup_dan_jalankan.bat
    pause
    exit /b 0
)
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM   4. Cek & install Ollama (opsional untuk fitur AI)
REM ─────────────────────────────────────────────────────────────────────────────
echo [4/7] Cek Ollama ^(opsional, untuk fitur AI^)...
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Ollama sudah terinstall
) else (
    echo   [?] Ollama belum terinstall
    echo.
    echo   Ollama dipakai untuk fitur "Tingkatkan dengan AI" ^(kategorisasi
    echo   transaksi otomatis pakai LLM lokal — gratis ^& private^).
    echo.
    set /p "INSTALL_AI_INPUT=  Install Ollama sekarang? (y/n, default y): "
    if "!INSTALL_AI_INPUT!"=="" set "INSTALL_AI_INPUT=y"
    if /i "!INSTALL_AI_INPUT!"=="y" (
        if "!NO_WINGET!"=="1" (
            echo   [!] Download Ollama dari https://ollama.com lalu install manual
            set "INSTALL_AI=0"
        ) else (
            echo   [...] Installing Ollama via winget...
            winget install -e --id Ollama.Ollama --silent --accept-source-agreements --accept-package-agreements
            if !errorlevel! neq 0 (
                echo   [!] Gagal install Ollama. Skip fitur AI.
                set "INSTALL_AI=0"
            ) else (
                echo   [OK] Ollama terinstall
                echo   [!] Ollama butuh restart shell untuk PATH update.
                echo       Tunggu 5 detik...
                timeout /t 5 /nobreak >nul
            )
        )
    ) else (
        set "INSTALL_AI=0"
        echo   [SKIP] Tanpa AI — aplikasi tetap jalan dengan kategorisasi keyword.
    )
)
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM   5. Pull model AI (kalau Ollama ada)
REM ─────────────────────────────────────────────────────────────────────────────
if "!INSTALL_AI!"=="1" (
    echo [5/7] Cek model AI %AI_MODEL%...
    where ollama >nul 2>&1
    if !errorlevel! equ 0 (
        REM Pastikan Ollama service running
        tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul
        if !errorlevel! neq 0 (
            echo   [...] Starting Ollama service di background...
            start "" /b ollama serve >nul 2>&1
            timeout /t 3 /nobreak >nul
        )

        ollama list 2>nul | findstr /b "%AI_MODEL%" >nul
        if !errorlevel! equ 0 (
            echo   [OK] Model %AI_MODEL% sudah ter-pull
        ) else (
            echo   [...] Pulling model %AI_MODEL% ^(~1.3 GB, sekali saja^)...
            echo         Ini bisa makan waktu 3-10 menit tergantung koneksi.
            ollama pull %AI_MODEL%
            if !errorlevel! neq 0 (
                echo   [!] Gagal pull model. Aplikasi tetap jalan tanpa AI.
            ) else (
                echo   [OK] Model %AI_MODEL% siap dipakai
            )
        )
    ) else (
        echo   [SKIP] Ollama belum tersedia di PATH session ini.
        echo          Tutup ^& jalankan ulang batch ini setelah Ollama terinstall.
    )
) else (
    echo [5/7] Skip pull model AI ^(Ollama tidak diinstall^)
)
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM   6. Clone atau update repo
REM ─────────────────────────────────────────────────────────────────────────────
echo [6/7] Sync repo dari GitHub...
if exist "%REPO_DIR%\.git" (
    echo   [OK] Repo sudah ada, pull update terbaru...
    pushd "%REPO_DIR%"
    git pull origin main
    popd
) else if exist "%REPO_DIR%\app.py" (
    echo   [OK] Folder app sudah ada ^(non-git^), skip clone
) else (
    echo   [...] Cloning repo dari %REPO_URL% ...
    git clone "%REPO_URL%" "%REPO_DIR%"
    if !errorlevel! neq 0 (
        echo   [X] Gagal clone repo
        pause
        exit /b 1
    )
)
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM   7. Setup venv & install dependencies
REM ─────────────────────────────────────────────────────────────────────────────
echo [7/7] Setup virtual environment ^& install dependencies...
pushd "%REPO_DIR%"

if exist "venv\Scripts\activate.bat" (
    echo   [OK] Virtual env sudah ada
) else (
    echo   [...] Membuat virtual environment...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo   [X] Gagal membuat venv
        popd
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat
echo   [...] Install/update dependencies...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if !errorlevel! neq 0 (
    echo   [X] Gagal install dependencies
    popd
    pause
    exit /b 1
)
echo   [OK] Dependencies siap
echo.

REM ─────────────────────────────────────────────────────────────────────────────
REM   8. Pastikan Ollama service running (kalau diinstall)
REM ─────────────────────────────────────────────────────────────────────────────
if "!INSTALL_AI!"=="1" (
    where ollama >nul 2>&1
    if !errorlevel! equ 0 (
        tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul
        if !errorlevel! neq 0 (
            echo [INFO] Starting Ollama service...
            start "" /b ollama serve >nul 2>&1
            timeout /t 2 /nobreak >nul
        )
    )
)

REM ─────────────────────────────────────────────────────────────────────────────
REM   9. Jalankan aplikasi & buka browser
REM ─────────────────────────────────────────────────────────────────────────────
echo ═══════════════════════════════════════════════════════════════════
echo    Setup selesai! Menjalankan aplikasi...
echo ═══════════════════════════════════════════════════════════════════
echo.
echo   URL: http://localhost:8181
echo.
echo   - Browser akan terbuka otomatis dalam 3 detik
echo   - Tekan Ctrl+C di window ini untuk stop server
echo.

REM Buka browser setelah 3 detik (di background)
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8181"

REM Jalankan Flask app (foreground, blocking)
python app.py

REM Setelah app dimatikan
popd
echo.
echo Aplikasi telah dihentikan.
pause
