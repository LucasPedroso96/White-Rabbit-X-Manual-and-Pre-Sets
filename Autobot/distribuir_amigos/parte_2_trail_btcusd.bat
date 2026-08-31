@echo off
cd /d "%~dp0.."
echo ===== Atualizando o repositorio (git pull) =====
git pull
echo.
echo ===== Rodando sweep completo: 03_TRAIL_ONLY em BTCUSD =====
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo BTCUSD --deposit 2500
echo.
echo ===== TERMINOU. Log final em sweep_03_TRAIL_ONLY_BTCUSD_master.log =====
pause
