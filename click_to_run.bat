@echo off
setlocal
cd /d "C:\Users\andre\OneDrive - NTNU\Split_TP_Calendar"

python "split_tp_calendar.py" >> "%USERPROFILE%\Desktop\split_tp_log.txt" 2>&1

git add 00.ics 02.ics 05.ics 06.ics >> "%USERPROFILE%\Desktop\split_tp_log.txt" 2>&1

git diff --cached --quiet
if %errorlevel%==0 (
  echo %date% %time% - Ingen endringer >> "%USERPROFILE%\Desktop\split_tp_log.txt"
  goto :EOF
)

git commit -m "Oppdater timeplan %date% %time%" >> "%USERPROFILE%\Desktop\split_tp_log.txt" 2>&1

REM Push til samme branch som du er på (main/master)
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
git push origin %BRANCH% >> "%USERPROFILE%\Desktop\split_tp_log.txt" 2>&1

endlocal
