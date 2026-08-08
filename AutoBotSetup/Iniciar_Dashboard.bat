@echo off
REM ============================================================
REM   WHITE RABBIT X - AUTOBOT DASHBOARD
REM ============================================================
REM   Inicia o painel de controle (app local, porta 8020).
REM   Nao precisa de Python instalado -- vem embutido nesta pasta.
REM   Para PARAR: feche esta janela, ou Ctrl+C.
REM ============================================================

title White Rabbit X - Autobot Dashboard
color 0B

cd /d "%~dp0"

echo.
echo ============================================================
echo   WHITE RABBIT X - AUTOBOT DASHBOARD
echo ============================================================
echo   Dashboard: http://localhost:8020
echo   Para PARAR: feche esta janela, ou Ctrl+C
echo ============================================================
echo.

if not exist "python-embed\python.exe" (
    if exist "wrx_setup.py" (
        echo [ERRO] Esta e a pasta de codigo-fonte do instalador, nao a
        echo instalacao pronta -- rodar este atalho direto daqui nunca
        echo funciona, porque o Python embutido so existe dentro do
        echo instalador empacotado.
        echo.
        echo Baixe e rode o instalador de verdade: White Rabbit X - Instalador.exe
        echo ^( https://t.me/MrRabbit_MT5 ^) -- ele cria a instalacao completa em
        echo Documents\White Rabbit X - Autobot, com o atalho certo na area
        echo de trabalho.
    ) else (
        echo [ERRO] python-embed\python.exe nao encontrado.
        echo Reinstale o White Rabbit X - Autobot.
    )
    echo.
    pause
    exit /b 1
)

if not exist "Autobot\dashboard_campanha.py" (
    if exist "wrx_setup.py" (
        echo [ERRO] Esta e a pasta de codigo-fonte do instalador, nao a
        echo instalacao pronta -- rodar este atalho direto daqui nunca
        echo funciona.
        echo.
        echo Baixe e rode o instalador de verdade: White Rabbit X - Instalador.exe
        echo ^( https://t.me/MrRabbit_MT5 ^)
    ) else (
        echo [ERRO] Autobot\dashboard_campanha.py nao encontrado.
        echo Reinstale o White Rabbit X - Autobot.
    )
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM Libera a porta 8020 se uma execucao anterior ficou pendurada
REM ------------------------------------------------------------
for /f "tokens=5" %%P in ('netstat -aon ^| findstr ":8020" ^| findstr "LISTENING"') do (
    echo Liberando processo %%P que ja usa a porta 8020...
    taskkill /PID %%P /F >nul 2>nul
)

REM ------------------------------------------------------------
REM Abre o navegador alguns segundos depois de iniciar
REM ------------------------------------------------------------
timeout /t 3 /nobreak >nul
start "" http://localhost:8020/

echo Log do dashboard (ao vivo):
echo ------------------------------------------------------------
echo.

pushd Autobot
"%~dp0python-embed\python.exe" dashboard_campanha.py --port 8020
popd

echo.
echo ============================================================
echo   DASHBOARD PARADO
echo ============================================================
pause
