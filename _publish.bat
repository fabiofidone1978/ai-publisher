@echo off
title AI Publisher Pipeline
cd /d "%~dp0"
python publish_all.py
echo.
echo Operazione conclusa.
pause