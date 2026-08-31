@echo off
cd /d "%~dp0.."
echo ===== Atualizando o repositorio (git pull) =====
git pull
echo.
echo ===== 03_TRAIL_ONLY -- outros 5 ativos de tendencia, um de cada vez =====
echo (1/5) CADJPY
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo CADJPY --deposit 10000
echo (2/5) NZDJPY
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo NZDJPY --deposit 10000
echo (3/5) GBPCAD
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo GBPCAD --deposit 10000
echo (4/5) GBPCHF
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo GBPCHF --deposit 10000
echo (5/5) EURNZD
python sweep_formulas.py --sistema 03_TRAIL_ONLY --simbolo EURNZD --deposit 10000
echo.
echo ===== TERMINOU OS 5. Logs: sweep_03_TRAIL_ONLY_<ATIVO>_master.log de cada um =====
pause
