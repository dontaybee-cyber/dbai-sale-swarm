@echo off
title DBAI Audit Swarm - Mission Control
cd /d "%~dp0"

:: Activate environment once at startup to ensure paths are correct
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [ERROR] .venv not found. Please ensure the virtual environment exists.
    pause
    exit /b
)

:MENU
cls
echo =====================================================
echo   DBAI AUDIT SWARM - MISSION CONTROL
echo =====================================================
echo.
echo   [1] Run SCOUT Agent (Find Leads)
echo   [2] Run ANALYST Agent (Analyze Sites)
echo   [3] Run SNIPER Agent (Send Emails)
echo   [4] Run CLOSER Agent (Check Replies & Follow-up)
echo   [5] Run FULL ACQUISITION SEQUENCE (Scout -> Analyst -> Sniper)
echo   [6] Exit
echo.
set /p choice="Select Operation: "

if "%choice%"=="1" goto SCOUT
if "%choice%"=="2" goto ANALYST
if "%choice%"=="3" goto SNIPER
if "%choice%"=="4" goto CLOSER
if "%choice%"=="5" goto SEQUENCE
if "%choice%"=="6" exit

goto MENU

:SCOUT
cls
".venv\Scripts\python.exe" scout_agent.py
pause
goto MENU

:ANALYST
cls
".venv\Scripts\python.exe" analyst_agent.py
pause
goto MENU

:SNIPER
cls
".venv\Scripts\python.exe" sniper_agent.py
pause
goto MENU

:CLOSER
cls
".venv\Scripts\python.exe" closer_agent.py
pause
goto MENU

:SEQUENCE
cls
echo =====================================================
echo   SWARM ACTIVE - FULL ACQUISITION SEQUENCE
echo =====================================================
echo.
set /p niche="Enter Target Niche (e.g. Roofing): "
set /p location="Enter Target Location (e.g. Dallas): "
echo.
echo [1/3] Launching SCOUT...
".venv\Scripts\python.exe" scout_agent.py --niche "%niche%" --location "%location%"
echo.
echo [2/3] Launching ANALYST...
".venv\Scripts\python.exe" analyst_agent.py
echo.
echo [3/3] Launching SNIPER...
".venv\Scripts\python.exe" sniper_agent.py
echo.
echo Sequence Complete.
pause
goto MENU