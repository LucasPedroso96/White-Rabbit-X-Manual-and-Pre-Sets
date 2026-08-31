@echo off
cd /d "%~dp0.."
echo ===== Atualizando o repositorio (git pull) =====
git pull
echo.
echo ===== 07_GRID_SEPARATE -- 5 ativos liquidos/laterais (lista original do Lucas) =====
echo (1/5) EURUSD
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo EURUSD --deposit 1000
echo (2/5) GBPUSD
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo GBPUSD --deposit 1000
echo (3/5) USDJPY
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo USDJPY --deposit 1000
echo (4/5) USDCHF
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo USDCHF --deposit 1000
echo (5/5) AUDUSD
python sweep_formulas.py --sistema 07_GRID_SEPARATE --simbolo AUDUSD --deposit 1000
echo.
echo ===== TERMINOU OS 5. Logs: sweep_07_GRID_SEPARATE_<ATIVO>_master.log de cada um =====
pause
