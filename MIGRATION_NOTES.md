# Migration and local operation

The implementation upgrades the original `C:\Users\Himanshu Chauhan\Documents\SymptoSphere-main\SymptoSphere-main` Flask/Jinja application in place. `human-atlas-main` is unchanged and supplies only anatomy reference code/data. Neither supplied folder contains `.git`, so no branch was created, no commit was invented, and nothing was pushed or deployed. A full unchanged baseline rollback ZIP is included with delivery.

## Local run (PowerShell, Python 3.12)

```powershell
Set-Location 'C:\Users\Himanshu Chauhan\Documents\SymptoSphere-main\SymptoSphere-main'
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
& .\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 . The shipped model and compiled viewer allow running without training, Node, external APIs, patient CSVs or secrets. Startup never retrains. Exact runtime sklearn 1.8.0 and the trusted bundle/manifest are required. For the already-running verified session, the app is on http://127.0.0.1:5073 and uses the isolated environment in the Codex task's `work/.venv`. Stop that local development server with Ctrl+C when no longer needed. The Flask development server is for local presentation/testing, not production serving.

## Tests and rebuilding anatomy

```powershell
& .\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements-train.txt
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\python.exe scripts/runtime_benchmark.py
Set-Location body_explorer
npm ci --ignore-scripts --no-audit --no-fund
npm run check
node scripts/validate-atlas.mjs
node scripts/validate-interactions.mjs
npm run build
Set-Location ..
```

Atlas requires Node >=22.13. The verified build used Node 24.13.1 and npm 11.8.0; all geometry is compressed. The build produces `static/body-map`. A >500kB JavaScript chunk warning remains; it is isolated behind the explicit lazy viewer action. Old browsers without WebGL/gzip decompression use text regions instead. Close removes the frame and cancels its outstanding work.

Browser regression tests use Playwright 1.62.1 and a real browser, without the user's browser profile:

```powershell
npm install --prefix tests
$env:CHROME_EXECUTABLE='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:APP_URL='http://127.0.0.1:5000'
node tests/browser_smoke.cjs
```

The installed Chrome path can be omitted if you run `npx --prefix tests playwright install chromium`. Browser screenshots and JSON go to `evaluation/browser`. The actual delivered checks used Chrome 154.0.8037.93, headed-independent temporary profiles and headless software WebGL. Manual assistive-technology review, real mobile GPU coverage and clinician review remain outstanding.

## Offline data reproduction

```powershell
& .\.venv\Scripts\python.exe train.py --data-dir data_raw --work-dir training_work --acquire --sample-size 32000 --tune-size 6000 --interview-size 128
& .\.venv\Scripts\python.exe -m ml.test_ddxplus --data-dir data_raw --work-dir training_work --interview-size 128
```

`--acquire` fetches only pinned Figshare URLs and verifies SHA256; the raw data remains outside deployment. Use a fresh work directory for a new reproduction. The official-test command refuses to overwrite its completed report and checks the frozen bundle and inference/evaluation code hashes. Do not use test results to tune future versions. On this machine data preparation/training needed several GB of memory and minutes of CPU; timings/metrics are reported rather than promised identical across hardware. The delivered manifest records reader/overlap corrections made before official inference; training choice, classifier bytes and calibration policy did not change.

To reproduce the unchanged legacy baseline, extract `SYMPTOSPHERE_BASELINE_ROLLBACK.zip` into a separate `baseline_snapshot` directory and run `python scripts/reproduce_legacy.py --baseline-dir <baseline_snapshot> --output-dir <new_audit_directory>` using the training environment. That helper verifies the exact trusted original model hash before loading it and writes a separate temporary audit database. It was run successfully against the preserved original source. The supplementary paired validation audit is `python -m ml.paired_validation_audit --work-dir training_work`; it does not select or alter the frozen classifier. After copying completed reports into `evaluation`, `python scripts/plot_evaluation.py` generates the three measured figures.

## Exact Git migration, preserving repository history

These are prepared instructions; none of these Git/network operations was executed. Create a clean clone of the same existing project and check out the audited commit on a development branch, then apply the supplied changed-file manifest. This preserves upstream history instead of creating an unrelated initial commit from a downloaded ZIP.

```powershell
Set-Location 'C:\Users\Himanshu Chauhan\Documents'
git -c core.autocrlf=false clone https://github.com/himanshu-chauhan-stack/SymptoSphere.git SymptoSphere-git
Set-Location SymptoSphere-git
git config core.autocrlf false
git switch -c feature/symptosphere-2 d4b7c20bb423286dd2890f2907d82767eeb2bb59
& 'C:\Users\Himanshu Chauhan\Documents\SymptoSphere-main\SymptoSphere-main\.venv\Scripts\python.exe' 'C:\Users\Himanshu Chauhan\Documents\SymptoSphere-main\SymptoSphere-main\scripts\apply_git_migration.py' --clone-dir 'C:\Users\Himanshu Chauhan\Documents\SymptoSphere-git'
```

The last command is a dry run. After reviewing its result, rerun it with `--apply`; it requires a clean target, exact baseline HEAD and `feature/symptosphere-2`, guards all paths and removes only explicitly retired files. It never touches `.git`, pushes or deploys. Then create the clone's Python environment, run the checks above and review:

```powershell
git status --short
git diff --stat
git diff --check
git add .
git commit -m "Upgrade SymptoSphere with validated DDXPlus evidence and lazy anatomy navigation"
```

Do not push production `main`, merge to it, or deploy/promote to production without explicit approval. If the audited commit is unavailable, stop and resolve provenance instead of inventing a base. The rollback archive restores the pre-upgrade code; use a separate directory and environment when comparing baseline behavior. New APIs intentionally reject the old symptom-list payload. No database migration or secret/session key is needed because the new educational interview is stateless.

## Staging preparation and deployment instructions

```powershell
& .\.venv\Scripts\python.exe scripts/prepare_staging.py
```

This copies the verified built assets to `public/static` and writes a local hash/size manifest. `vercel.json` retains Flask while using current Flask detection and public CDN assets, with runtime exclusions for training data, Atlas build sources, tests, legacy content and reports. Python 3.12 is pinned in `.python-version`; runtime requirements contain only inference dependencies. The selected joblib and manifest, knowledge JSON and Jinja templates must remain in the function bundle. No SQLite writes or startup retraining occur.

For an authorized preview in the correct Vercel project, use a non-production branch or `npx vercel@latest deploy` after checking the account/project link. **Do not use `--prod`, promote the preview, or change the production project without approval.** No Vercel login, build, preview deployment, Linux bundle, hosted cold start or hosted p95 was run here. Validate `/api/health`, main pages, tri-state API, no-JS POST, same-origin message bridge, static subpaths/gzip, CSP, mobile text fallback and viewer behavior on that preview before considering production.

Hosting guidance checked 2026-10-02: https://vercel.com/docs/frameworks/backend/flask and https://vercel.com/docs/functions/runtimes/python . Account-specific bundle/runtime limits and large-function opt-ins change; validate the actual preview's build logs and plan rather than treating a local source-size estimate as a deployment pass.
