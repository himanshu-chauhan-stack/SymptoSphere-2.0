# Commands run and outcomes

The upgrade was made in the supplied application folder. Commands below record the substantive inspection, reproduction, implementation, training, evaluation, build, testing and delivery operations. Paths and working-directory changes are normalized into the variables below; this is not a verbatim transcript of every `rg`, `Get-Content`, directory listing or small one-off inspection. Repeated failed attempts and their corrections are disclosed below. No Git mutation, Vercel login/build/deployment or production operation ran.

```powershell
$primary='C:\Users\Himanshu Chauhan\Documents\SymptoSphere-main\SymptoSphere-main'
$task='C:\Users\Himanshu Chauhan\Documents\Codex\2026-10-02\files-mentioned-by-the-user-human'
$python="$task\work\.venv\Scripts\python.exe"
$data='C:\Users\Himanshu Chauhan\Documents\Codex\2026-10-02\files-mentioned-by-the-user-project\work\research'
$training="$task\work\ddxplus"
$node='C:\Program Files\nodejs\node.exe'
```

## Inspection, baseline and implementation

- Read/extracted every handoff ZIP entry, documents, research/evidence JSON, pinned source archives, reproduction scripts and complete DDXPlus paper text before editing code. `work/handoff_inspection.json` records entry hashes. `rg --files`, `rg --line-number`, `Get-Content`, `Get-ChildItem`, Python ZIP/JSON/text readers and SHA256 comparisons inspected source and evidence.
- `python work/inspect_inputs.py`: verified all 55 primary baseline files; created unchanged `work/baseline_source.zip`. Neither source was a Git checkout.
- Isolated Python 3.12 environment creation; `python -m pip install --no-cache-dir --disable-pip-version-check --no-input -r requirements-train.txt`: completed. The first default-cache install stalled; no-cache installation corrected it. The final requirements installation reported already satisfied. `python -m pip check`: no broken requirements.
- `python work/baseline_audit.py`: completed original SVC/Flask reproduction and raw/deduplicated/dropout audit. Baseline route/client calls also executed.
- `python work/check_dataset.py`: whole-source schema/domain/multi-choice inspection completed.
- Intermediate implementation writers `work/setup_navigation.py`, `work/adapt_atlas.py`, `work/redesign.py`, `work/frontend.py`, and `work/retire_and_notices.py` ran, alongside reviewed file patches. They created the navigation-only viewer integration, interface and inactive legacy archive. They are working files, not runtime dependencies.
- Source-hash verification rechecked all 118 supplied Atlas files unchanged; gzip geometry inspection and original license reads completed.

## Training and evaluation (working directory: $primary)

```powershell
Set-Location $primary
& $python -m ml.train_ddxplus --data-dir $data --work-dir $training --sample-size 32000 --tune-size 6000 --interview-size 128
& $python -m ml.test_ddxplus --data-dir $data --work-dir $training --interview-size 128
& $python -m ml.paired_validation_audit --work-dir $training
& $python scripts/runtime_benchmark.py
& $python scripts/reproduce_legacy.py --baseline-dir "$task\work\baseline\SymptoSphere-d4b7c20bb423286dd2890f2907d82767eeb2bb59" --output-dir "$task\work\evidence\reproduced_cli"
& $python "$task\work\finalize_reports.py"
& $python scripts/plot_evaluation.py
```

- One initial training attempt stopped when a parent-order bug in the full-retention mask was found. Both candidates were rerun with the corrected shared mask. Final training succeeded: LR 122.73s, HGB 457.31s, no fit warnings; validation selected LR (0.56502847 versus 0.50701724). Dataset preparation validated every train/validation row and isolated profiles before masking.
- Two official-test preparations stopped **before test inference**: default Windows text decoding disagreed on UTF-8 condition names; rebuilding a large profile union inside every row caused quadratic work. Explicit UTF-8 and one precomputed union corrected these. Their old/new code hashes and reasons are retained. The model/selection/calibration/mask/question policy did not change. One completed official run evaluated all 134,529 rows; no test-driven retuning or repeated official scoring followed.
- The paired final-validation audit completed with the frozen model; it corrects comparability of question-policy RNG draws without rewriting the original reports or reselecting the model.
- The separate legacy reproduction CLI completed and recovered the documented baseline scores. Runtime benchmark and all three plots came from actual completed runs.

## Anatomy build (working directory: $primary/body_explorer)

```powershell
Set-Location "$primary\body_explorer"
npm ci --cache "$task\work\npm-cache" --ignore-scripts --no-audit --no-fund
npm run check
& $node scripts/validate-atlas.mjs
& $node scripts/validate-interactions.mjs
npm run build
```

Installed 565 packages. Final TypeScript check, geometry validation, interaction validation and Vite build passed. Geometry: 2,234 meshes, 3,432 concepts, 2,288,268 triangles, 15 compressed chunks. Earlier TypeScript/environment/manifest typing defects were corrected. The >500kB optional viewer JavaScript chunk warning remains. The copied viewer source retains license texts for installed dependencies; node_modules is excluded from delivery.

## Application and browser checks (working directory: $primary)

```powershell
Set-Location $primary
& $python -m pip check
& $python -m compileall -q app.py ml knowledge scripts
& $node --check static/js/symptoms.js
& $node --check static/js/lang.js
& $python -m pytest -q --junitxml=evaluation/pytest.xml
$env:PORT='5073'
& $python -u app.py
# In another shell, with the verified server running:
$env:PLAYWRIGHT_MODULE='C:\Users\Himanshu Chauhan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules\playwright'
$env:CHROME_EXECUTABLE='C:\Program Files\Google\Chrome\Application\chrome.exe'
$env:APP_URL='http://127.0.0.1:5073'
& $node tests/browser_smoke.cjs
```

- Completed final browser run: **14 scenarios passed, zero page exceptions**, Chrome 154.0.8037.93, real software WebGL rendering and navigation, responsive mobile emulation, keyboard/reduced-motion and no-JS form coverage. Captures in `evaluation/browser` are actual screenshots. Default bundled Chromium was unavailable; installed Chrome was used with an isolated temporary profile. Intermediate viewer probes (`work/viewer_check.cjs`, `work/nojs_probe.cjs`) also ran to investigate real issues.
- Initial browser failures exposed Unknown-skip handling, incomplete multi-choice follow-up completion, no-referrer same-origin form Origin:null handling, and stale-response rejection; all were corrected and covered. Fixtures were corrected for the released E_56 categorical evidence and lowercase heart source name. A final template edit was initially checked against a stale Flask template cache; restarting the server yielded all 14 passes. These failures are not claimed as passes.
- Earlier pytest runs completed 36 passes. Final delivery rerun initially hit restricted access to existing Windows pytest temp/cache directories (34 passed, two fixture errors); a subsequent wrong working-directory attempt failed import before collecting tests. Final corrected command below ran from the primary project and passed **36 tests in 0.76s**:

```powershell
Set-Location $primary
& $python -m pytest -q -p no:cacheprovider --basetemp "$task\work\pytest-delivery-final-20261002" --junitxml=evaluation/pytest.xml
```

JUnit and browser JSON reports retain the final results; intermediate default-temp failure XML remains in the working evidence, not disguised as a successful final run. JavaScript syntax was rechecked after the last visible notice change and passed. No test uses a substitute successful model for the actual-artifact ready check.

## Local staging and delivery

```powershell
Set-Location $primary
& $python scripts/prepare_staging.py
Set-Location $task
& $python work/prepare_delivery.py
& $python work/verify_delivery_runtime.py
```

Staging preparation copied 29 files / 36,439,227 bytes into local `public/static`, verified against source hashes. An initial use of a workspace-relative Python path while in the primary folder failed to find the executable; the absolute interpreter path corrected it. Initial delivery-helper checks corrected a Windows path string literal and resolved the recorded frozen ML basenames beneath `ml` before completing the package. Delivery preparation checks final test reports, frozen model/candidate/code hashes, staging hashes, and CRC plus SHA256 for every packaged entry; it creates the full changed-file inventory, application ZIP, unchanged baseline rollback ZIP, documentation, evaluation mirror and delivery manifest. The isolated extracted-package runtime check passed real model readiness, five GET routes, three ranked conditions without probabilities and next-question HTTP 200, using the installed environment and no original raw datasets/build dependencies. It performs no publishing. Archive verification details are in `outputs/DELIVERY_MANIFEST.json` and runtime details in `outputs/DELIVERY_RUNTIME_CHECK.json`.

Exact commands for a future local environment, Git migration, offline reproduction and staging preview are in `MIGRATION_NOTES.md`. Git migration and any Vercel preview remain unexecuted instructions.
