@echo off
cd /d "%~dp0.."
echo ===== Atualizando o repositorio (git pull) =====
git pull
echo.
echo ===== Rodando sweep completo: 07_GRID_SEPARATE em USDCHF =====
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo USDCHF --deposit 1000
echo.
echo ===== TERMINOU. Log final em sweep_07_GRID_SEPARATE_USDCHF_master.log =====
pause
