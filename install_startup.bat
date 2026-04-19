@echo off
TITLE Install Forensica AI Startup Service
echo Adding Forensica AI to Windows Startup...
set "startup_folder=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "vbs_source=%~dp0run_hidden.vbs"

if not exist "%vbs_source%" (
    echo Error: run_hidden.vbs not found.
    pause
    exit /b 1
)

copy /Y "%vbs_source%" "%startup_folder%\ForensicaAI.vbs" >nul
echo.
echo Success! Forensica AI will now automatically run silently in the background every time you boot your PC.
echo.
echo To start it right now without rebooting, we will execute it once.
cscript //nologo "%vbs_source%"
echo Services started:
echo - Backend API on http://localhost:8000
echo - Frontend UI on http://localhost:3000
echo.
pause
