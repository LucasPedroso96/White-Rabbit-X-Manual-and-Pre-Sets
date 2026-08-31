@echo off
cd /d "%~dp0.."
echo ===== Atualizando o repositorio (git pull) =====
git pull
echo.
echo ===== Rodando sweep completo: 03_TRAIL_ONLY em GBPUSD =====
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo GBPUSD --deposit 10000
echo.
echo ===== TERMINOU. Log final em sweep_03_TRAIL_ONLY_GBPUSD_master.log =====
pause
