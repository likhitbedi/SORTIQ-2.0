# Getting SORTIQ 2.0 as a Windows `.exe` (no Python on the customer's computer)

This ZIP is the actual SOURCE PROJECT, not a precompiled Windows installer. The compiled Windows artifact needs to be generated on a Windows computer or Windows CI runner, and the build result needs validation.

## GitHub Actions route (only GitHub account + browser/VS Code needed)

1. Extract `SORTIQ_2.0_AI_Auto_Organizer_Build_Kit.zip`.
2. Open the folder in VS Code. The hidden `.github/workflows/build-windows.yml` must be included in the repository.
3. Publish the folder to a **private** GitHub repository, with a commit on the `main` branch.
4. Open the GitHub repository > **Actions** > **Build SORTIQ 2.0 for Windows** > **Run workflow**.
5. On a successful run, download `SORTIQ-Windows-Installer` (normal setup wizard) or `SORTIQ-Windows-Portable` (contains `SORTIQ.exe` plus its DLLs).
6. The setup program should be called `SORTIQ_2.0_Beta_Setup.exe`. Double-click it and follow the wizard. The installed app does NOT require Python.
7. The first launch asks what the customer does and whether they consent to downloading a local AI model. It needs internet for the optional first-time model download.

The workflow includes unit tests and a packaged CLI smoke test, but still requires real interactive testing on Windows 10/11 before a public release. CI failures may require changes to dependencies or PyInstaller hooks. This build has not yet been executed through Windows CI by the assistant.

## Development route (if Python is installed on Windows)

`START_SORTIQ.bat` launches the source code. `BUILD_WINDOWS_EXE.bat` creates a Windows executable folder; `BUILD_WINDOWS_INSTALLER.bat` creates the installation wizard if Inno Setup 6 is installed.

## Commercial release warning

A beta installer is not market-ready. Code signing, legal/privacy reviews, antivirus/security assessment, supported-format tests, model licensing notices, and measured classification accuracy are still needed. See `docs/RELEASE_READINESS.md`.
