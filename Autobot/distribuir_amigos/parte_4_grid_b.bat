@echo off
cd /d "%~dp0.."
echo ===== Atualizando o repositorio (git pull) =====
git pull
echo.
echo ===== 07_GRID_SEPARATE -- outros 5 ativos liquidos/laterais, um de cada vez =====
echo (1/5) NZDUSD
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo NZDUSD --deposit 1000
echo (2/5) EURGBP
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo EURGBP --deposit 1000
echo (3/5) AUDCHF
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo AUDCHF --deposit 1000
echo (4/5) AUDCAD
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo AUDCAD --deposit 1000
echo (5/5) CADCHF
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo CADCHF --deposit 1000
echo.
echo ===== TERMINOU OS 5. Logs: sweep_07_GRID_SEPARATE_<ATIVO>_master.log de cada um =====
pause
