@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  set "PYTHON=py -3"
) else (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python is not installed. Install Python 3.11 or newer from python.org and rerun.
    echo Tick 'Add Python to PATH' during installation.
    pause
    exit /b 1
  )
  set "PYTHON=python"
)
if not exist ".venv\Scripts\python.exe" (
  echo Initializing local SORTIQ environment...
  %PYTHON% -m venv ".venv"
  if errorlevel 1 (
    echo Could not create Python environment.
    pause
    exit /b 1
  )
)
if not exist ".venv\sortiq_2_ready.flag" (
  echo Installing document readers and local AI runtime. Internet required for first setup only.
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt -r requirements-ai.txt
  if errorlevel 1 (
    echo Document readers did not install. SORTIQ can still scan filenames.
    echo To retry later, delete .venv\sortiq_2_ready.flag
  ) else (
    echo Installed>".venv\sortiq_2_ready.flag"
  )
)
echo Starting SORTIQ...
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
  echo SORTIQ closed with an error. Please copy any traceback when reporting an issue.
  pause
)
endlocal
