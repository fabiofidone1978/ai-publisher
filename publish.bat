@echo off
REM ====================================================================
REM SUPER MASTER PIPELINE - AI PUBLISHER + LINKEDIN + PROMOFINDER
REM ====================================================================

setlocal enabledelayexpansion

title CONSOLE AUTOMAZIONE - FABIO FIDONE
color 0B

REM --- CONFIGURAZIONE PERCORSI ---
set "PATH_AI=D:\Documents and Settings\fabio-fidone\My Documents\ai-publisher"
set "PATH_PROMO=D:\Documents and Settings\fabio-fidone\My Documents\www.promofinder.it\newsletter"

echo.
echo ====================================================================
echo   AVVIO WORKFLOW TOTALE: AI + PROMO
echo ====================================================================
echo.

REM ====================================================================
REM SEZIONE 1: AI PUBLISHER (Lavoro in %PATH_AI%)
REM ====================================================================
cd /d "%PATH_AI%"

echo [1/5] GENERAZIONE JSON (publish_all.py)
echo --------------------------------------------------------------------
python publish_all.py
if errorlevel 1 goto :error

echo.
echo [2/5] UPLOAD ARUBA (upload_via_php.py)
echo --------------------------------------------------------------------
python upload_via_php.py
REM Non blocchiamo per l'upload, come richiesto

echo.
echo [3/5] NEWSLETTER AI (pipeline.py)
echo --------------------------------------------------------------------
python pipeline.py
if errorlevel 1 goto :error

echo.
echo [4/5] PUBBLICAZIONE LINKEDIN (linkedin_publisher.py)
echo --------------------------------------------------------------------
python linkedin_publisher.py
if errorlevel 1 (
    echo [!] LinkedIn ha restituito un avviso, ma procedo...
)

echo.
echo ====================================================================
echo   FASE AI COMPLETATA - PASSO A PROMOFINDER
echo ====================================================================
echo.

REM ====================================================================
REM SEZIONE 2: PROMOFINDER (Lavoro in %PATH_PROMO%)
REM ====================================================================
cd /d "%PATH_PROMO%"

echo [5/5] NEWSLETTER PROMO (Pipeline.py)
echo --------------------------------------------------------------------
python Pipeline.py

if errorlevel 1 (
    goto :error
)

REM ====================================================================
REM CONCLUSIONE OPERAZIONI
REM ====================================================================
:success
color 0A
echo.
echo ====================================================================
echo   TUTTO OK! - Pipeline eseguita con successo.
echo ====================================================================
echo   Data: %date% Ora: %time%
echo.
pause
exit /b 0

:error
color 0C
echo.
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
echo   ERRORE RILEVATO: Controlla i log qui sopra prima di chiudere.
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
echo.
pause
exit /b 1