# SymptoSphere 2.0 — completed local implementation

The supplied SymptoSphere application was upgraded in place, preserving Flask/Jinja, its local entry point and page routes. The supplied human-atlas source remains unchanged and is used only for lazy anatomy navigation. There is one selected Logistic Regression classifier at inference; there is no ensemble. No source folder was a Git checkout, so a branch/commit was not invented. Nothing was pushed or deployed.

## Delivered behavior

- Pinned, hashed DDXPlus pipeline with whole-file schema validation, profile deduplication/isolation, typed encoding, missing-evidence augmentation and independent missing demographics. LR and HistGradientBoosting were actually fitted and compared on predeclared validation views; LR won 0.56502847 to 0.50701724.
- Present / Absent / Unknown binary answers, valid categorical zero, explicitly completed multi-choice, dependency invalidation and Unknown demographic values. Unasked answers stay unknown. Partial multi-choice does not contribute until complete.
- Adaptive optional follow-ups, explicit skip and editable state. Narrow English text suggestions require user confirmation, valid ontology IDs and exact supporting spans; text does not directly trigger diagnosis.
- Ranked three possible conditions with actual model-effect explanations, supporting answered evidence, scope/uncertainty and educational care navigation. Independent limited emergency rules work even when the model cannot load. Fictional doctor personas and prescription-style content were retired; unreviewed condition-specific specialty content falls back to generic primary-care navigation.
- Modern responsive UI, basic Hindi interface labels, print/no-JavaScript fallback and optional 3D viewer. Anatomy selection changes navigation only, preserves interview answers, and never becomes a classifier input. Viewer source/geometry and dependency attribution are supplied.

## Measured results

Official frozen evaluation used all 134,529 synthetic test rows, with overlap-controlled subsets, per-class support/confusion, probability scoring, bootstrap intervals, subgroup slices and simulated question-policy comparisons. These are dataset results, not clinical accuracy or patient risk. Random-answer budget views below differ from adaptive-interview rollouts, which are separately reported.

| Official evidence view | Mean known answers | Top-1 | Top-3 | Macro-F1 |
|---|---:|---:|---:|---:|
| Initial evidence | 1.00 | 37.29% | 60.95% | 0.3597 |
| Seven-answer view | 7.00 | 44.86% | 68.44% | 0.4392 |
| Complete released record | 215.03 | 99.72% | 100.00% | 0.9966 |

The complete-record result uses about 215 known answers per case; it is not the expected performance of a short interview. Temperature calibration failed the independent sparse display gate, so no probability percentages are displayed. The legacy 100% result was reproduced but had 41/42 test-profile overlap and only 304 unique training profiles.

Final checks: **36 Python tests passed**, **14 actual Chrome browser scenarios passed**, zero page exceptions; dependency, Python/JavaScript syntax, TypeScript, Vite, geometry and interaction checks passed. All 118 supplied Atlas source files were rehashed unchanged. Local fresh import/model load was 1,771.96ms, warm prediction p95 9.83ms and next-question p95 9.37ms (30 requests each), working set about 145.29MiB. These are local measurements with OS file cache not cleared. Screenshots in `evaluation/browser` are actual captures.

## Review files and delivery

- `SYMPTOSPHERE_2_IMPLEMENTATION.zip`: the upgraded original application, selected artifact, compiled anatomy viewer, viewer source, tests, docs and evidence. Dependencies/caches and the generated public mirror are excluded; the mirror is reproducible from shipped static assets.
- `SYMPTOSPHERE_BASELINE_ROLLBACK.zip`: all 55 unchanged original files for baseline reproduction/rollback.
- [CHANGED_FILES.md](CHANGED_FILES.md): every added/modified/deleted source, asset and evidence file, plus all generated staging files. [evaluation/changed_files.json](evaluation/changed_files.json) has per-file hashes for guarded Git migration.
- [COMMANDS_RUN.md](COMMANDS_RUN.md): commands actually run, results and disclosed failed attempts/corrections.
- [EVALUATION_REPORT.md](EVALUATION_REPORT.md): actual candidate, official, overlap-controlled and paired interview results; raw reports and figures are in `evaluation`.
- [MIGRATION_NOTES.md](MIGRATION_NOTES.md): exact local run, reproduction, feature-branch migration and non-production staging instructions. The clean-clone migration helper and hosted deployment have not been exercised here.
- [DATASET_CARD.md](DATASET_CARD.md), [MODEL_CARD.md](MODEL_CARD.md), [OPEN_SOURCE_ATTRIBUTION.md](OPEN_SOURCE_ATTRIBUTION.md), [IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md), [docs/IMPLEMENTATION_ARCHITECTURE.md](docs/IMPLEMENTATION_ARCHITECTURE.md).
- `DELIVERY_MANIFEST.json`: delivery hashes, archive CRC/entry-hash verification and exclusions. Raw DDXPlus patient releases are not in the package; the pinned acquisition/reproduction pipeline supplies them when requested.

## Exact local run

```powershell
Set-Location 'C:\Users\Himanshu Chauhan\Documents\SymptoSphere-main\SymptoSphere-main'
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
& .\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 . The verified session already running at http://127.0.0.1:5073 uses the isolated Codex `work/.venv`. No training, Node, external API, patient CSV or secrets are needed for a local run with shipped assets. For a separately extracted ZIP, run the commands in that extracted application directory.

For local staging, run `python scripts/prepare_staging.py`. The Vercel configuration is supplied with modern Flask/public static handling; account linking, hosted/Linux build and preview behavior are unverified. After authorization for the correct project, a non-production preview may use `npx vercel@latest deploy`; never add `--prod` or promote/merge to production without explicit approval. Use the checks listed in the migration document before any production consideration.

## Known limits

This is an educational synthetic-data demonstration with 49 conditions and limited urgent rules. There has been no clinician review, real-patient/India validation or clinical safety evaluation. The five ontology-parent exceptions, symptom/body mapping and educational care content require review. Narrow text extraction supports a small English alias list; Hindi is interface-only and clinical evidence remains English. Condition-specific specialty content is not yet approved, so generic primary care is used. Calibration failed; sparse interview accuracy is limited; small 128-profile policy simulations have broad uncertainty and rare-class limitations. Independent unknown values cannot recover information never provided. The optional viewer has roughly 33MB compressed geometry and a large JavaScript chunk warning; actual mobile GPU, manual screen-reader and broader browser coverage remain outstanding. Git migration, Vercel preview and hosted performance are unverified. Required open-source notices are preserved, including BodyParts3D CC BY attribution and Atlas MIT; the original app has no root license, so no new license was assigned to it.
