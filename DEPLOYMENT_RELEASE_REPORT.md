# SymptoSphere 2.0 Deployment Release Report

Date: 2026-10-02

## New GitHub

- Repository: `SymptoSphere-2.0`
- URL: https://github.com/himanshu-chauhan-stack/SymptoSphere-2.0
- Visibility: Public
- Initial release commit: `18eca8a2eb4785668148f6a27960fabe20008ca6`
- The repository contains the active application, inference artifact, compiled Atlas assets, tests, documentation, and evaluation evidence. The inactive `legacy/` source snapshot is excluded.

## New Vercel

- Project: `symptosphere-2-0`
- Scope: `drmonsares-projects`
- Production URL: https://symptosphere-2-0.vercel.app/
- Deployment URL: https://symptosphere-2-0-gfmne9s1c-drmonsares-projects.vercel.app
- Inspect URL: https://vercel.com/drmonsares-projects/symptosphere-2-0/CzjEYQX91k2dkruKtkPc6kWPFhWu
- Build status: Ready
- The first CLI deployment became the project's initial production deployment automatically. No `--prod` promotion was used.
- Vercel GitHub auto-linking was not completed because the Vercel account did not have repository admin/write integration permission. The deployment was created from the authenticated CLI instead.
- Vercel SSO deployment protection was disabled for this new project after deployment; the production URL was then verified anonymously with HTTP 200 responses.

## Verification

- Local Python suite: 36 tests passed under Python 3.14.3. The documented Python 3.12 interpreter was unavailable locally.
- Hosted build: Vercel used Python 3.12 from `.python-version`; dependency installation, staging, and deployment completed successfully.
- Atlas: TypeScript check, geometry validation, interaction validation, and Vite build passed. The existing optional viewer chunk-size warning remains.
- Hosted API: `/api/health` returned `ready: true` with model `LogisticRegression`.
- Hosted API: empty evidence returned `insufficient_information` from `/api/next-question`.
- Hosted API: a confirmed cough state returned three ranked conditions from `/api/predict`, with no probability fields.
- Local staging: 29 static files copied and hashed by `scripts/prepare_staging.py`.

## Runtime

- Python: 3.12 hosted by Vercel; Python 3.14.3 used for the local compatibility run.
- Model: `ml/models/ddxplus_bundle.joblib` with `ml/models/ddxplus_manifest.json`.
- Selected model: Logistic Regression.
- Required application environment variables: none. The app is stateless and does not require API keys, a database, startup training, or external services.

## Legacy preservation

- Legacy GitHub repository `https://github.com/himanshu-chauhan-stack/SymptoSphere` was not modified.
- Legacy Vercel deployment `https://symptosphere.vercel.app/` was not modified.
- The new repository and Vercel project use separate names and URLs.

## Known limitations

- This is an educational synthetic DDXPlus demonstration, not clinical validation, diagnosis, or risk estimation.
- The calibration display gate failed, so UI probability percentages remain hidden.
- The new project is publicly browsable after disabling its initial SSO deployment protection; no protection setting was changed on the legacy project.
- No clinician review, real-patient/India validation, exhaustive triage review, or broad mobile GPU/accessibility certification was performed.
- The optional Atlas viewer retains a large JavaScript chunk warning and downloads roughly 33 MB of compressed geometry when opened.
