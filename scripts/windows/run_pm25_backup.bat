@echo off
setlocal EnableExtensions

rem Manual compatibility wrapper. Scheduled backup belongs to the unified task.
for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "BACKUP_ROOT=G:\My Drive\PM25_Backup"

if not exist "%PYTHON_EXE%" (
  echo Missing Python environment: %PYTHON_EXE%
  exit /b 1
)

"%PYTHON_EXE%" "%PROJECT_ROOT%\tools\backup\backup_pm25_data.py" --dest "%BACKUP_ROOT%" %*
exit /b %ERRORLEVEL%
