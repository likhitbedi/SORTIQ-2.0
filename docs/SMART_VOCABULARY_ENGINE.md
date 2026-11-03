> **Legacy V1.3 manual classification reference.** SORTIQ 2.0 automatic mode is documented in `../README.md` and `RELEASE_READINESS.md`.

# SORTIQ Smart Vocabulary Engine — V1.3

This update adds editable subject dictionaries and a local keyword scoring engine to SORTIQ Classic.

1. Open the **Subjects** toolbar button.
2. Enter a destination folder such as `College / Marketing` and example seed phrases such as `segmentation, branding, positioning`.
3. Click **Save Subject**. Data is saved locally to `%LOCALAPPDATA%\SORTIQ\vocabulary.json` on Windows.
4. Optionally click **Find Related Terms Online** and explicitly approve a Wikipedia Search lookup. SORTIQ sends only the **subject name and seed keywords**, not files or document text. The setting (50–1000) is a cap, **not a guarantee** that enough relevant words exist.
5. Add selected source folders and click **Scan**, inspect recommendations with **Why?**, choose **Copy** (recommended), then **Organize**. Your original files are untouched until you explicitly organize.

## How it classifies

SVE searches extracted content first, filenames second and parent folders third. User-supplied seed phrases carry more weight than discovered phrases. It scores phrase matches with word boundaries, then compares the best subject with the runner-up. If it is not confident, the result is **Needs Review**. If none of your SVE vocabulary matches at all, original SORTIQ rules act as fallback. Scores and 'confidence' are heuristics, not AI probabilities. This version is **not a semantic embedding model** and does not understand every synonym or context.

## Privacy and limitations

- Entire file contents are never transmitted during classification. The only feature that accesses Wikipedia is a separate user-approved vocabulary search using subject names and seeds. Do not enter confidential seeds if you choose online lookup.
- Candidate terms discovered through Wikipedia may be off-topic. Search availability and the usefulness of results are not guaranteed; the online step has not been independently verified on Windows.
- Supported content readers include text, DOCX, PPTX, text PDFs and XLSX, subject to existing parser limits. Scanned documents require OCR not included here.
- The default is **Copy**, with an operation history and undo. Test on a backup or demo before attempting Moves.
- The original Windows EXE and Inno Setup scripts are provided; a compiled executable/installer must be produced and tested on Windows.
