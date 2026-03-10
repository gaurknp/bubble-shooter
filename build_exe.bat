@echo off
setlocal

REM Build script for Interior Factory Software Starter
REM Output: dist\InteriorFactoryStarter.exe

where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo [INFO] PyInstaller not found. Installing...
  pip install pyinstaller
  if errorlevel 1 (
    echo [ERROR] Failed to install pyinstaller.
    exit /b 1
  )
)

pyinstaller --noconfirm --clean --onefile --windowed --name InteriorFactoryStarter interior_factory_software.py
if errorlevel 1 (
  echo [ERROR] Build failed.
  exit /b 1
)

echo.
echo [SUCCESS] EXE created:
echo   dist\InteriorFactoryStarter.exe
endlocal
