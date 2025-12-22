@echo off
setlocal EnableExtensions

REM ===============================
REM Konfig
REM ===============================
set "PROJECT_DIR=C:\Users\andre\OneDrive - NTNU\Split_TP_Calendar"
set "SCRIPT_NAME=split_tp_calendar.py"
set "LOG_FILE=%USERPROFILE%\Desktop\split_tp_log.txt"

REM Hvor lenge vi venter maks (sekunder)
set "WAIT_MAX=600"
set "WAIT_STEP=5"

echo.>> "%LOG_FILE%"
echo [%date% %time%] START >> "%LOG_FILE%"

REM ===============================
REM 1) Vent på OneDrive-prosess (med timeout)
REM ===============================
set /a elapsed=0
:WAIT_ONEDRIVE
tasklist | find /i "OneDrive.exe" >nul
if errorlevel 1 (
    if %elapsed% GEQ %WAIT_MAX% (
        echo [%date% %time%] FEIL: OneDrive.exe startet ikke innen %WAIT_MAX%s >> "%LOG_FILE%"
        exit /b 1
    )
    timeout /t %WAIT_STEP% /nobreak >nul
    set /a elapsed+=%WAIT_STEP%
    goto WAIT_ONEDRIVE
)

REM ===============================
REM 2) Vent på at prosjektmappen finnes (med timeout)
REM ===============================
set /a elapsed=0
:WAIT_FOLDER
if not exist "%PROJECT_DIR%" (
    if %elapsed% GEQ %WAIT_MAX% (
        echo [%date% %time%] FEIL: Fant ikke prosjektmappe: "%PROJECT_DIR%" >> "%LOG_FILE%"
        exit /b 2
    )
    timeout /t %WAIT_STEP% /nobreak >nul
    set /a elapsed+=%WAIT_STEP%
    goto WAIT_FOLDER
)

REM Ekstra buffer for sync
timeout /t 10 /nobreak >nul

REM ===============================
REM 3) Gå til repo-mappa
REM ===============================
cd /d "%PROJECT_DIR%" || (
    echo [%date% %time%] FEIL: Klarte ikke cd til "%PROJECT_DIR%" >> "%LOG_FILE%"
    exit /b 3
)

REM ===============================
REM 4) Finn python (venv først)
REM ===============================
set "PYTHON="
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

if not defined PYTHON (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [%date% %time%] FEIL: Fant ikke python (verken .venv eller PATH) >> "%LOG_FILE%"
        exit /b 4
    )
    set "PYTHON=python"
)

REM ===============================
REM 5) Kjør python-scriptet
REM ===============================
"%PYTHON%" "%SCRIPT_NAME%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] FEIL: Python-scriptet feilet (exitcode=%errorlevel%) >> "%LOG_FILE%"
    exit /b 5
)

REM ===============================
REM 6) Git add + commit hvis endringer
REM ===============================
where git >nul 2>&1
if errorlevel 1 (
    echo [%date% %time%] FEIL: Fant ikke git i PATH >> "%LOG_FILE%"
    exit /b 6
)

git add 00.ics 02.ics 05.ics 06.ics >> "%LOG_FILE%" 2>&1

git diff --cached --quiet
if %errorlevel%==0 (
    echo [%date% %time%] Ingen endringer å commite >> "%LOG_FILE%"
    exit /b 0
)

REM Trygg timestamp (unngår : i %time%)
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH-mm-ss'"`) do set "TS=%%i"

git commit -m "Oppdatert timeplan %TS%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] FEIL: git commit feilet (exitcode=%errorlevel%) >> "%LOG_FILE%"
    exit /b 7
)

REM ===============================
REM 7) Push til main
REM ===============================
git push origin main >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] FEIL: git push feilet (exitcode=%errorlevel%) >> "%LOG_FILE%"
    exit /b 8
)

echo [%date% %time%] OK: Oppdatert + pushet >> "%LOG_FILE%"
exit /b 0
