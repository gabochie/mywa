@echo off
title mywa - Contact Dashboard
cd /d "%~dp0"

echo ============================================
echo  mywa dashboard - getting your data ready...
echo ============================================
echo.

python -m mywa -i contacts "C:\Users\user\Documents\GitHub\aiw\data\databases\gadata.db" --opportunity-groups "real estate, wholesale, import, construction, logistics, farm, trading" --out real_out --serve 8123 --open

echo.
echo Dashboard closed. You can close this window.
pause
