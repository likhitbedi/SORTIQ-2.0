@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Install Python 3.11 or newer from https://python.org
    pause
    exit /b 1
  )
  set "PYTHON=python"
)
if not exist ".venv\Scripts\python.exe" (
  %PYTHON% -m venv .venv
  if errorlevel 1 goto :fail
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-ai.txt pyinstaller
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --onedir --name SORTIQ --icon "assets\icons\sortiq.ico" --add-data "assets;assets" --add-data "docs;docs" --collect-submodules pypdf --collect-submodules pptx --collect-submodules docx --collect-submodules openpyxl --collect-all fastembed --collect-all onnxruntime --collect-all tokenizers --collect-all huggingface_hub main.py
if errorlevel 1 goto :fail
echo.
echo SUCCESS: dist\SORTIQ\SORTIQ.exe
echo To build a real installation wizard, run BUILD_WINDOWS_INSTALLER.bat next.
exit /b 0
:fail
echo EXE packaging failed. Python version remains runnable using START_SORTIQ.bat.
exit /b 1
