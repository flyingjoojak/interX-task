@echo off
echo Starting InterX MVP...

REM Start backend
start "InterX Backend" cmd /k "cd /d C:\Users\main\Downloads\interX\backend && python -m uvicorn main:app --host 0.0.0.0 --port 8102 --reload"

REM Start frontend
start "InterX Frontend" cmd /k "cd /d C:\Users\main\Downloads\interX\frontend && npm run dev -- --port 3102"

echo.
echo Backend:  http://localhost:8102
echo Frontend: http://localhost:3102
echo API Docs: http://localhost:8102/docs
echo.
echo Both servers are running. Close each window to stop its server.
