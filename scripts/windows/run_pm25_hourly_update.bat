@echo off
setlocal EnableExtensions

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Missing Python environment: %PYTHON_EXE%
  exit /b 1
)

if "%PURPLEAIR_API_KEY%"=="" (
  echo PURPLEAIR_API_KEY is not set in the task account environment.
  exit /b 2
)

"%PYTHON_EXE%" "%PROJECT_ROOT%\tools\data_collection\run_unified_pipeline.py" %*
exit /b %ERRORLEVEL%
