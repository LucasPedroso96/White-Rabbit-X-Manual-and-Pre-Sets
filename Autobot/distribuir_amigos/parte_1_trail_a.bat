@echo off
cd /d "%~dp0.."
echo ===== Atualizando o repositorio (git pull) =====
git pull
echo.
echo ===== 03_TRAIL_ONLY -- 5 ativos de tendencia, um de cada vez =====
echo (1/5) GBPJPY
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo GBPJPY --deposit 10000
echo (2/5) GBPAUD
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo GBPAUD --deposit 10000
echo (3/5) EURAUD
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo EURAUD --deposit 10000
echo (4/5) AUDJPY
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo AUDJPY --deposit 10000
echo (5/5) GBPNZD
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo GBPNZD --deposit 10000
echo.
echo ===== TERMINOU OS 5. Logs: sweep_03_TRAIL_ONLY_<ATIVO>_master.log de cada um =====
pause
