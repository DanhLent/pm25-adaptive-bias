@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0..\.."
pushd "%ROOT%" >nul

where vlog >nul 2>nul
if errorlevel 1 (
    echo [pm25] build: SKIP simulator not found
    popd >nul
    exit /b 1
)

where vsim >nul 2>nul
if errorlevel 1 (
    echo [pm25] build: SKIP simulator not found
    popd >nul
    exit /b 1
)

if not exist "sim\modelsim_work" mkdir "sim\modelsim_work"
pushd "sim\modelsim_work" >nul

if not exist work vlib work >nul

vlog +incdir+"%ROOT%\rtl\core" ^
    "%ROOT%\rtl\core\alert_classifier.v" ^
    "%ROOT%\rtl\core\hysteresis.v" ^
    "%ROOT%\rtl\core\bias_update.v" ^
    "%ROOT%\rtl\core\fusion.v" ^
    "%ROOT%\rtl\core\pm25_alert_core.v" ^
    "%ROOT%\tb\verilog\tb_pm25_alert_core.v" > build.log 2>&1

if errorlevel 1 (
    echo [pm25] build: FAIL
    type build.log
    popd >nul
    popd >nul
    exit /b 1
)

echo [pm25] build: PASS
echo.
echo [pm25] vector tests

set /a TOTAL=0
set /a FAILURES=0
set /a SAMPLES_TOTAL=0

for %%V in ("%ROOT%\data\test_vectors\*.csv") do if exist "%%~fV" call :run_vector "%%~fV"
for %%V in ("%ROOT%\data\test_vectors\extra\*.csv") do if exist "%%~fV" call :run_vector "%%~fV"
for %%S in (2 3 4 5 6) do call :run_alpha %%S

echo.
if "!FAILURES!"=="0" (
    echo [pm25] summary: PASS
) else (
    echo [pm25] summary: FAIL
)
echo [pm25] vectors=!TOTAL! samples=!SAMPLES_TOTAL! errors=!FAILURES!

popd >nul
popd >nul

if not "!FAILURES!"=="0" exit /b 1
exit /b 0

:run_vector
set /a TOTAL+=1
set "VECTOR=%~1"
set "STEM=%~n1"
vsim -c tb_pm25_alert_core "+VECTOR=%VECTOR%" "+VECTOR_NAME=%STEM%" -do "run -all; quit -f" > run.log 2>&1

set "N=0"
for /f "tokens=1,2,3,4,5,6 delims= " %%A in ('findstr "TB_RESULT" run.log') do (
    if "%%A"=="#" (
        set "SAMPLE_TOKEN=%%E"
    ) else (
        set "SAMPLE_TOKEN=%%D"
    )
)
if defined SAMPLE_TOKEN (
    for /f "tokens=2 delims==" %%N in ("!SAMPLE_TOKEN!") do set "N=%%N"
)
set /a SAMPLES_TOTAL+=N

if errorlevel 1 (
    set /a FAILURES+=1
    call :print_vector_line FAIL !N!
    findstr "MISMATCH TB_FATAL TB_RESULT" run.log
) else (
    call :print_vector_line PASS !N!
)
set "SAMPLE_TOKEN="
goto :eof

:run_alpha
set /a TOTAL+=1
set "SHIFT=%~1"
set "VECTOR=%ROOT%\data\test_vectors\alpha_shift\core_v1_alpha_shift_!SHIFT!.csv"
set "STEM=alpha_shift_!SHIFT!"
vsim -c -gALPHA_SHIFT=!SHIFT! tb_pm25_alert_core "+VECTOR=!VECTOR!" "+VECTOR_NAME=!STEM!" -do "run -all; quit -f" > run.log 2>&1

set "N=0"
set "SAMPLE_TOKEN="
for /f "tokens=1,2,3,4,5,6 delims= " %%A in ('findstr "TB_RESULT" run.log') do (
    if "%%A"=="#" (
        set "SAMPLE_TOKEN=%%E"
    ) else (
        set "SAMPLE_TOKEN=%%D"
    )
)
if defined SAMPLE_TOKEN (
    for /f "tokens=2 delims==" %%N in ("!SAMPLE_TOKEN!") do set "N=%%N"
)
set /a SAMPLES_TOTAL+=N

if errorlevel 1 (
    set /a FAILURES+=1
    call :print_vector_line FAIL !N!
    findstr "MISMATCH TB_FATAL TB_RESULT" run.log
) else (
    call :print_vector_line PASS !N!
)
set "SAMPLE_TOKEN="
goto :eof

:print_vector_line
set "STATUS=%~1"
set "COUNT=%~2"
set "PADDED=!STEM!                                    "
set "PADDED=!PADDED:~0,36!"
set "IDX=00!TOTAL!"
set "IDX=!IDX:~-2!"
if "%STATUS%"=="PASS" (
    echo   !IDX!    !PADDED! PASS  n=!COUNT!
) else (
    echo   !IDX!    !PADDED! FAIL  n=!COUNT!
)
goto :eof
