# SORTIQ 2.0 — Product / Safety Review

**Status:** Working beta prototype. Not market-ready or accuracy-certified.

## Current automation

- First-run description of the customer's occupation, projects and typical documents
- Choose authorized source folders, destination and local AI download consent
- Generate a domain-focused initial taxonomy (rule-based profile interpretation)
- One-click AI Organize: read supported documents, perform local semantic + keyword scoring, route strong matches, copy to subject folders, report uncertain files
- Cache unchanged document excerpts and embeddings locally, support repeat runs
- Duplicate-safe copy, operation log and Undo, never delete originals during automatic mode
- File types recognized by extension are explicitly described as such, not as visual/audio understanding

## Known limitations / loopholes and remediation priority

| Priority | Gap | Mitigation in this beta | Required before selling |
| --- | --- | --- | --- |
| P0 | Wrong auto-filing / misclassification | Conservative threshold + margin; untouched uncertain files; copy only | Label 300-1,000 diverse customer files; measure precision/recall per category; tune thresholds; human audits |
| P0 | Windows EXE and installer not verified | GitHub Windows CI builds a portable app + setup wizard and runs packaged smoke test | Build on Windows, install/uninstall on clean Win10/11 VMs, test model download and libraries |
| P0 | Scanned PDFs, old Office formats, OCR, images | Leave unreadable docs in review; image/video routing uses extension only | Add secure OCR and format handling, benchmark sample quality |
| P0 | Sensitive documents cached unencrypted | Cache is local per-user, clear-cache action, no cloud text uploads | Threat model, optional no-cache mode, encryption policies and strict access/retention controls |
| P0 | Cancel/rollback during massive interrupted batches | Per-file hashes, exclusive create, crash-recoverable log, per-batch undo | Full disk, power interruption, locked files, OneDrive sync and 10k-file stress tests |
| P0 | Model supply chain | Explicit opt-in, public small model with permissive license | Pin artifact revisions/hashes, dependency SBOM, antivirus and binary scan |
| P1 | Taxonomy for unseen professions | Generic subject from self-description + built-in categories | Conversational LLM-assisted taxonomy plus category review at setup; domain expansion |
| P1 | Long/mixed-topic documents | Multi-position text excerpts and multiple semantic chunks | Multi-label hierarchy and human-validated segmentation of long documents |
| P1 | OCR and language coverage | Language and format limitations disclosed | Test multilingual model and locale-specific tokenization |
| P1 | Repeated rescans / slow CPUs | SQLite cache of unchanged text + embeddings | Benchmarks on low-end Windows laptops, progress/cancel, batch embeddings |
| P1 | Automatic file monitoring | Not enabled | Opt-in background watcher with throttling, debounce, and clear pause controls |
| P1 | Product reliability | Unit tests, packaging smoke test, local demo | Structured error logs, signed installer, update channel, crash monitoring with consent |
| P1 | Commercial legal matters | Draft EULA and privacy disclosure | Lawyer-reviewed EULA, privacy notice, license attributions, trademark review, code-signing |

## Accuracy release gates (proposal — NOT achieved)

- Baseline actual dataset: collect owner-consented representative files from at least 3 user types.
- Each file has independently assigned ground-truth label; include ambiguous, out-of-scope, mixed-topic and unreadable files.
- Measure auto-routing precision by final folder, coverage (fraction auto-filed), per-class recall, false routes, and time spent.
- Never interpret the internal relevance score as a calibrated probability.
- Suggested commercial gate: >=98% precision **among automatically routed files**, >=75% coverage in supported text-document test groups, zero overwrites, successful Undo in every clean unchanged-file scenario, and a <2% processing-failure rate in the tested environment. These are proposed targets, not validated results.
- No launch until validation benchmarks and Windows compatibility/security tests are actually passed.

## Architecture and threat boundary

Input: user-selected directories only. Offline parsers extract local text, bounded by size and character limits. Embeddings are computed on device, with model retrieval gated by consent. Classification produces a category, reason, and Ready/Review status. Only Ready files enter verified copy operations; unresolved files remain untouched. A SQLite operation log provides recoverability.

Never permit document contents to issue executable instructions or direct filesystem tools; treat all document text as untrusted data. If an LLM is later added, it must output validated folder labels into an allowlist and have NO direct write/delete tool permission.
