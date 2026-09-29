@echo off
title DepthWizard Full Stack Launcher
echo =======================================================
echo Starting DepthWizard Full Model Stack...
echo =======================================================

set "BASE_DIR=%~dp0"

echo [1/3] Starting FastAPI Model Backend (Port 8000)...
start "DepthWizard Model Backend" cmd /k "cd /d "%BASE_DIR%backend" && python -m uvicorn app:app --host 127.0.0.1 --port 8000"

echo [2/3] Starting 3D Model Viewer (Port 5174)...
start "DepthWizard 3D Viewer" cmd /k "cd /d "%BASE_DIR%3d_viewer" && npx vite --port 5174 --host 127.0.0.1"

echo [3/3] Starting DepthWizard UI (Port 8080)...
start "DepthWizard UI" cmd /k "cd /d "%BASE_DIR%frontend" && npm run dev -- --port 8080 --host 127.0.0.1"

echo.
echo Waiting for servers to initialize...
ping -n 5 127.0.0.1 >nul

echo Opening DepthWizard in your browser...
start http://localhost:8080/

echo =======================================================
echo All DepthWizard services are now active!
echo  - Web Application: http://localhost:8080/
echo  - 3D Viewer:       http://127.0.0.1:5174/
echo  - Model Backend:   http://127.0.0.1:8000/
echo =======================================================
pause
