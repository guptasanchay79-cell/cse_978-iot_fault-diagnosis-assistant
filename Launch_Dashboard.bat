@echo off
title P_311: IoT Fault Diagnosis Assistant - Dashboard Launcher
echo =====================================================================
echo  P_311: Knowledge-Driven IoT Fault Diagnosis Assistant
echo  Industrial Centrifugal Pump SCADA Dashboard
echo =====================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking if Dashboard Server is already running on port 8080...
netstat -ano | findstr :8080 | findstr LISTENING >nul
if %errorlevel% equ 0 (
    echo [OK] Dashboard Server is already active on http://localhost:8080.
) else (
    echo [2/3] Starting Python Dashboard Server in background...
    if exist ".venv\Scripts\python.exe" (
        start "P_311 Dashboard Server" /B ".venv\Scripts\python.exe" dashboard\app.py
    ) else (
        start "P_311 Dashboard Server" /B python dashboard\app.py
    )
    timeout /t 2 /nobreak >nul
)

echo [3/3] Opening Dashboard in your default web browser...
start http://localhost:8080

echo.
echo =====================================================================
echo  Dashboard running at: http://localhost:8080
echo  Connected Dataset: UCI AI4I 2020 Predictive Maintenance (10,000 rows)
echo  PostgreSQL Persistence: p311_iot_diagnostics (telemetry & incidents)
echo  To close the server, close the Python process or press Ctrl+C.
echo =====================================================================
timeout /t 5 >nul
exit
