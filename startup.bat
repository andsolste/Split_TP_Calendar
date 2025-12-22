setlocal

REM 1) Gå til repo-mappa
cd /d "C:\Users\andre\OneDrive - NTNU\Split_TP_Calendar"

REM 2) Kjør python-scriptet (bruk full sti hvis python ikke finnes i PATH)
python "split_tp_calendar.py" >> "%USERPROFILE%\Desktop\split_tp_log.txt" 2>&1

REM 3) Legg til bare .ics-filene (tilpass hvis du har andre filnavn)
git add 00.ics 02.ics 05.ics 06.ics >> "%USERPROFILE%\Desktop\split_tp_log.txt" 2>&1

REM 4) Sjekk om det faktisk er noe å commite
git diff --cached --quiet
if %errorlevel%==0 (
    echo %date% %time% - Ingen endringer >> "%USERPROFILE%\Desktop\split_tp_log.txt"
    goto :EOF
)

REM 5) Commit med timestamp
git commit -m "Oppdatert timeplan %date% %time%" >> "%USERPROFILE%\Desktop\split_tp_log.txt" 2>&1

REM 6) Push til main
git push origin main >> "%USERPROFILE%\Desktop\split_tp_log.txt" 2>&1

endlocal
