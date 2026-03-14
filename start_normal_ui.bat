@echo off
setlocal
set "ROOT_DIR=%~dp0"

if not exist "%ROOT_DIR%system\run_studio.bat" (
  echo [ERROR] No se encontro "%ROOT_DIR%system\run_studio.bat"
  exit /b 1
)

if /i "%UNLZ_DRY_RUN%"=="1" (
  echo [DRY-RUN] Ejecutaria: "%ROOT_DIR%system\run_studio.bat"
  endlocal & exit /b 0
)

pushd "%ROOT_DIR%system" >nul
call "run_studio.bat"
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul

endlocal & exit /b %EXIT_CODE%
