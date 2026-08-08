@echo off
REM ============================================================
REM   WHITE RABBIT X - AUTOBOT DASHBOARD
REM ============================================================
REM   Starts the control panel (local app, port 8020).
REM   No need for Python installed -- it's embedded in this folder.
REM   To STOP: close this window, or Ctrl+C.
REM ============================================================

title White Rabbit X - Autobot Dashboard
color 0B

cd /d "%~dp0"

echo.
echo ============================================================
echo   WHITE RABBIT X - AUTOBOT DASHBOARD
echo ============================================================
echo   Dashboard: http://localhost:8020
echo   To STOP: close this window, or Ctrl+C
echo ============================================================
echo.

if not exist "python-embed\python.exe" (
    if exist "Install_AutoBot_and_Sets.py" (
        echo [ERROR] This is the installer's source-code folder, not the
        echo ready-made install -- running this shortcut straight from here
        echo never works, because the embedded Python only exists inside
        echo the packaged installer.
        echo.
        echo Download and run the real installer: White Rabbit X - Instalador.exe
        echo ^( https://t.me/MrRabbit_MT5 ^) -- it creates the full install at
        echo Documents\White Rabbit X - Autobot, with the correct desktop
        echo shortcut.
    ) else (
        echo [ERROR] python-embed\python.exe not found.
        echo Reinstall White Rabbit X - Autobot.
    )
    echo.
    pause
    exit /b 1
)

if not exist "Autobot\dashboard_campanha.py" (
    if exist "Install_AutoBot_and_Sets.py" (
        echo [ERROR] This is the installer's source-code folder, not the
        echo ready-made install -- running this shortcut straight from here
        echo never works.
        echo.
        echo Download and run the real installer: White Rabbit X - Instalador.exe
        echo ^( https://t.me/MrRabbit_MT5 ^)
    ) else (
        echo [ERROR] Autobot\dashboard_campanha.py not found.
        echo Reinstall White Rabbit X - Autobot.
    )
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM Frees port 8020 if a previous run was left hanging
REM ------------------------------------------------------------
for /f "tokens=5" %%P in ('netstat -aon ^| findstr ":8020" ^| findstr "LISTENING"') do (
    echo Freeing process %%P that's already using port 8020...
    taskkill /PID %%P /F >nul 2>nul
)

REM ------------------------------------------------------------
REM Opens the browser a few seconds after starting
REM ------------------------------------------------------------
timeout /t 3 /nobreak >nul
start "" http://localhost:8020/

echo Dashboard log (live):
echo ------------------------------------------------------------
echo.

pushd Autobot
"%~dp0python-embed\python.exe" dashboard_campanha.py --port 8020
popd

echo.
echo ============================================================
echo   DASHBOARD STOPPED
echo ============================================================
pause
