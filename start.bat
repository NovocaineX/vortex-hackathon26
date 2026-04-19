@echo off
TITLE Forensica AI Launcher

echo [1/3] Starting Forensica AI Backend in the background...
:: Start backend minimized in its specific folder
start /MIN "Forensica Backend" cmd /c "cd backend && python main.py"

echo [2/3] Starting Forensica AI Frontend on port 3000...
:: Start frontend minimized
start /MIN "Forensica Frontend" cmd /c "python -m http.server 3000"

echo [3/3] Launching web browser...
:: Wait 2 seconds for the servers to fully spin up
timeout /t 2 /nobreak >nul

:: Automatically open the default browser to the localhost port
start http://localhost:3000

cls
echo =======================================================
echo               FORENSICA AI IS RUNNING
echo =======================================================
echo.
echo The web browser has been opened to the Forensica AI interface.
echo (http://localhost:3000)
echo.
echo The FastAPI backend is running completely behind the scenes.
echo.
echo NOTE: To stop the application entirely, close the two small 
echo minimized windows (Forensica Backend and Forensica Frontend)
echo from your taskbar!
echo.
echo Press any key to safely close this launcher window...
pause >nul
