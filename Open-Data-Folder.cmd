@echo off
rem Prints the folder holding the journal and measurements.
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
call "%~dp0_find-python.cmd" || (pause & exit /b 1)
set "PYTHONPATH=%~dp0src"
%PY% -m centauri_calibrator where %*
echo.
pause
endlocal
