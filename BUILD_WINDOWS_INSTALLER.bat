@echo off
setlocal
cd /d "%~dp0"
echo =====================================================================
echo SORTIQ 2.0 Beta - Windows Installer Builder
 echo =====================================================================
 echo Stage 1 of 2: Build portable app files.
call BUILD_WINDOWS_EXE.bat
if errorlevel 1 goto :fail
 echo Stage 2 of 2: Build setup wizard with Inno Setup 6.
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo.
  echo Inno Setup 6 not found. Install the free official Inno Setup 6 compiler
  echo from https://jrsoftware.org/isinfo.php and re-run this script.
  echo Your unpacked Windows app is already at dist\SORTIQ\SORTIQ.exe
  pause
  exit /b 2
)
"%ISCC%" "installer\SORTIQ_Setup.iss"
if errorlevel 1 goto :fail
echo.
echo READY: installer\Output\SORTIQ_2.0_Beta_Setup.exe
pause
exit /b 0
:fail
echo Installer build failed. Verify Python, dependencies, and Inno Setup 6.
pause
exit /b 1
