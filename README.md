# SymptoSphere 2.0

Interactive educational symptom intelligence with an optional 3D body explorer. This is an upgrade of the existing Flask/Jinja application. It ranks possible matches within 49 synthetic DDXPlus conditions; it is not a diagnosis or clinical risk estimator.

The app supports explicit Present / Absent / Unknown answers, typed categorical and completed multi-choice questions, unknown demographics, adaptive follow-ups and confirmed local English phrase suggestions. Unselected symptoms stay unknown. Ranked results explain actual answer-removal model effects and give general care navigation with uncertainty. Independent, limited sourced urgent prompts precede the model. Unsupported/unsure, empty, negative-only and history-only states do not force a match. No prescription panel, fictional doctor persona or booking/payment promise is presented.

The supplied Human Atlas is integrated as a lazy static React/Three iframe. Opening or selecting anatomy filters questions without adding symptoms. Text regions remain usable without WebGL. Geometry/code license notices are retained. The primary app remains Flask, not a new anatomy application.

## Run locally

Python **3.12**, with exact runtime dependencies and the shipped model/manifest:

```powershell
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
& .\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 . No startup training, data download, API key, database or Node build is required for the shipped application. The model loader fails safely on incompatible/missing artifacts; independent safety responses still work.

## Validate and reproduce

```powershell
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-train.txt
& .\.venv\Scripts\python.exe -m pytest -q
```

The candidate comparison selected **LogisticRegression** on the predeclared sparse-evidence validation score, ahead of HistGradientBoosting. One classifier performs inference; no ensemble is claimed. Scores, counts, intervals, reliability, per-class support, policy comparisons and known methodological limits are in [EVALUATION_REPORT.md](EVALUATION_REPORT.md). The independent calibration gate failed, and UI percentages are withheld.

See [MIGRATION_NOTES.md](MIGRATION_NOTES.md) for exact local commands, browser tests, anatomy rebuild, offline DDXPlus reproduction, safe Git migration and staging instructions. No Git metadata was supplied; no push or deployment was performed. Production main/Vercel promotion requires explicit approval.

## Implementation records

- [Implementation log](IMPLEMENTATION_LOG.md)
- [Dataset card](DATASET_CARD.md)
- [Model card](MODEL_CARD.md)
- [Architecture](docs/IMPLEMENTATION_ARCHITECTURE.md)
- [Open-source attribution](OPEN_SOURCE_ATTRIBUTION.md)
- [Measured evaluation reports](evaluation/)

Hindi covers interface labels; evidence/options/guidance remain English pending review. Controlled extraction is narrow and requires confirmation. Clinical review, real-patient/India validation, exhaustive triage, condition-specific specialty summaries and hosted deployment verification remain outside the completed prototype.

Original SymptoSphere creator/team credit: Himanshu Chauhan, Avishhoray Raj, Nihal Kumar. DDXPlus: Fansi Tchango et al., CC BY 4.0. Human Atlas code: MIT, © 2026 ashemag. BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International. Complete source/adaptation details are in the attribution document. No new root license is assigned to the original application.
