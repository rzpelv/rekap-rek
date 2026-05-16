@echo off
title Rekapin — Rekap Rekening Koran
color 0A
cls

echo.
echo  ============================================
echo   Rekapin - Rekap Rekening Koran
echo  ============================================
echo.

:: ── Pindah ke folder file ini berada ─────────────────────────────────────
cd /d "%~dp0"

:: ── Cek Python ────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python tidak ditemukan!
    echo.
    echo  Install Python 3.8+ dari:
    echo  https://www.python.org/downloads/
    echo.
    echo  Pastikan centang "Add Python to PATH" saat install.
    echo.
    pause
    exit /b 1
)

:: ── Install / update dependensi ───────────────────────────────────────────
echo  [1/3] Memeriksa dependensi...
python -m pip install flask pdfplumber openpyxl gunicorn --quiet --upgrade
if errorlevel 1 (
    echo  [WARN] Gagal update dependensi, mencoba lanjut...
)
echo  [OK] Dependensi siap
echo.

:: ── Buat folder sessions jika belum ada ──────────────────────────────────
if not exist "sessions" mkdir sessions

:: ── Cari port yang tersedia ──────────────────────────────────────────────
set PORT=5000
netstat -an | find ":%PORT% " >nul 2>&1
if not errorlevel 1 (
    set PORT=5001
    netstat -an | find ":%PORT% " >nul 2>&1
    if not errorlevel 1 set PORT=5002
)

:: ── Jalankan server ───────────────────────────────────────────────────────
echo  [2/3] Menjalankan server di port %PORT%...
echo.

:: Set PORT environment variable
set PORT=%PORT%

:: Jalankan Flask di background
start /B python app.py > logs_server.txt 2>&1

:: Tunggu server siap (coba sampai 15 detik)
echo  [3/3] Menunggu server siap...
set /a TRIES=0
:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a TRIES+=1
python -c "import urllib.request; urllib.request.urlopen('http://localhost:%PORT%')" >nul 2>&1
if not errorlevel 1 goto SERVER_READY
if %TRIES% GEQ 15 goto SERVER_TIMEOUT
goto WAIT_LOOP

:SERVER_READY
echo.
echo  ============================================
echo   Server berjalan di:
echo   http://localhost:%PORT%
echo  ============================================
echo.
echo  Browser akan terbuka otomatis...
echo  Tekan Ctrl+C atau tutup jendela ini untuk berhenti.
echo.

:: Buka browser
start "" "http://localhost:%PORT%"

:: Tampilkan log live
echo  === Log Server ===
python app.py

goto END

:SERVER_TIMEOUT
echo.
echo  [ERROR] Server tidak merespons setelah 15 detik.
echo  Cek file logs_server.txt untuk detail error.
echo.
pause
exit /b 1

:END
