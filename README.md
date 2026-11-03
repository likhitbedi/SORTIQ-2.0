# SORTIQ 2.0 Beta — AI Automatic File Organizer

**Status: functional desktop prototype, not a verified commercial product.**

## The experience

The first time a customer launches SORTIQ, an onboarding dialog asks **what work/studies/business they do**, which folders they want to organize, where organized copies should go, and explains that AI is included with the installer. Click **Save & Organize Automatically**. Next time, clicking the colorful **AI Organize** toolbar icon scans all selected folders and copies confidently classified files into appropriate subfolders automatically, with no file-by-file category selection. The app records the operation so unchanged copies can be undone.

### AI details (precise claims)

- First-run **taxonomy generation currently uses domain/keyword rules** with a generic fallback. It is not an LLM conversation engine yet.
- **Bundled offline AI:** FastEmbed/ONNX with `BAAI/bge-small-en-v1.5` is shipped with the installer. Only the Windows build runner downloads its weights and tokenizer. Customer machines need no model download or internet connection.
- If model files are missing or damaged, no files are copied, and the app asks for a reinstall rather than silently switching to keyword-only routing.
- Supported text: `.txt, .md, .csv, .pdf (extractable text), .docx, .pptx, .xlsx` plus several source-code formats. Filename/extension-based routing is different from content AI. No OCR or image/video semantic analysis yet.
- Conservative routing: ambiguous/unreadable files stay **untouched** in the original folder. Automatic mode only **copies**, never deletes or moves originals. All detected duplicates are skipped. Users can Undo the last batch of unchanged copies.

## On Windows as an installed application — no Python required for customers

The included **GitHub Actions Windows build** (`.github/workflows/build-windows.yml`) runs on a Windows runner and installs the dependencies there. If the build passes, its artifacts are:

- `SORTIQ-Windows-Portable`: ZIP containing `SORTIQ.exe` and runtime dependencies; unzip and double-click `SORTIQ.exe`.
- `SORTIQ-Windows-Installer`: `SORTIQ_2.0_Beta_Setup.exe`; double-click for the install wizard (license/privacy text, install path, desktop shortcut, uninstall support).

**These files are not precompiled in this ZIP.** Publish the extracted project as a *private* GitHub repository, go to **Actions > Build SORTIQ 2.0 for Windows > Run workflow**, and download the artifacts after a successful run. The workflow itself has not been executed or verified on a Windows runner in this environment.

## Developers with Windows and Python

1. Extract the ZIP and run `START_SORTIQ.bat`. This creates a virtual environment and downloads required libraries.
2. If you want to compile locally, run `BUILD_WINDOWS_EXE.bat` and then `BUILD_WINDOWS_INSTALLER.bat` (Inno Setup 6 is required for the installer).
3. Run `python -m pytest -q tests` in a prepared environment for logic tests.

## Privacy and security

Selected files are read locally, including subfolders. Extracted text and model vectors are saved in `%LOCALAPPDATA%\\SORTIQ` to accelerate repeat runs. Clear this through **Actions > Clear local analysis cache**. AI weights and tokenizer files are bundled at build time and never downloaded by installed SORTIQ. No document contents are uploaded. The app does not execute scanned scripts. Auto Copy is always the default even if manual Move had been selected.

**Before commercial sale:** see `docs/RELEASE_READINESS.md`. Required work includes benchmark calibration, code signing, OCR, dynamic domain taxonomy, an installer test on clean Windows computers, privacy/legal review and security testing. The existing EULA is a prototype draft, not legal advice.
