@echo off
REM ====================================================================
REM AI PUBLISHER - PUBLISH & UPLOAD ONLY
REM ====================================================================
REM Sequenza:
REM 1. publish_all.py    -> Genera ainews.json + aiprompts.json
REM 2. upload_via_php.py -> Upload su www.fabiofidone.it/data/
REM ====================================================================

setlocal enabledelayexpansion

title AI Publisher - Publish & Upload

color 0B

echo.
echo ====================================================================
echo   AI PUBLISHER - PUBLISH & UPLOAD ONLY
echo ====================================================================
echo.

cd /d "%~dp0"

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python non trovato!
    pause
    exit /b 1
)

echo [OK] Python trovato
echo.

REM ====================================================================
REM STEP 1: Genera JSON
REM ====================================================================

echo [1/2] Generazione JSON (ainews.json + aiprompts.json)
echo ====================================================================
echo.

python publish_all.py

if errorlevel 1 (
    echo.
    echo [ERROR] publish_all.py fallito!
    color 0C
    pause
    exit /b 1
)

echo.
echo [OK] JSON generati in data/
echo.

REM ====================================================================
REM STEP 2: Upload su Aruba
REM ====================================================================

echo [2/2] Upload file su Aruba (www.fabiofidone.it/data/)
echo ====================================================================
echo.

python upload_via_php.py

if errorlevel 1 (
    echo.
    echo [ERROR] upload_via_php.py fallito!
    color 0C
    pause
    exit /b 1
)

echo.
echo [OK] File caricati su Aruba
echo.

REM ====================================================================
REM COMPLETATO
REM ====================================================================

echo ====================================================================
echo   OPERAZIONE COMPLETATA CON SUCCESSO!
echo ====================================================================
echo.

echo Riepilogo:
echo   [OK] ainews.json generato
echo   [OK] aiprompts.json generato
echo   [OK] news_*.json generato
echo   [OK] File caricati su Aruba
echo.

color 0A

pause
exit /b 0