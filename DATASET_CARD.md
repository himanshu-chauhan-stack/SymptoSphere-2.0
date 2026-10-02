# DDXPlus dataset card

Pinned source: DDXPlus Dataset (English), Figshare article **22687585, version 2**, DOI https://doi.org/10.6084/m9.figshare.22687585.v2. Authors: Arsene Fansi Tchango, Rishab Goel, Zhi Wen, Julien Martel, Joumana Ghosn. Dataset license: CC BY 4.0. Raw ontology and approved release hashes are in `knowledge/ddxplus_sources.json`; no patient CSVs ship in the application.

## Intended use and limits

Educational, synthetic, closed-set condition ranking and research on structured partial evidence. The 49-condition scope chiefly concerns cough, sore throat and breathing presentations. The source used a proprietary knowledge base, North American demographic assumptions and modified generation priors. These scores cannot measure clinical diagnosis performance, real prevalence, clinical risk, general symptom coverage or performance in India. The synthetic differential is secondary evaluation reference data, never a feature or question oracle. No real-patient data was added.

## Canonical evidence

223 evidences: 208 binary, 10 categorical and 5 multi-choice; 110 symptoms and 113 antecedents. Binary Present/Absent/Unknown have distinct known masks. Categorical numeric zero is a valid known value. Multi-choice selection contributes only after explicit complete-answer confirmation; synthetic default answers are known only in complete source records. User-unasked questions remain unknown. Dependent children require their existing binary parent to be Present. Five missing parent references are recorded explicitly in `ml/evidence_schema.py`; these self-contained binary history questions are independent engineering exceptions, without clinician review.

The paper's five-option multi-choice limit does not describe every released row: the whole training scan detected larger valid sets. The parser accepts unique, non-default-combining values from the pinned domain and reports the observed maxima. It does not silently discard these rows or invent values. Every CSV column, target, demographic, literal token, initial complaint and differential distribution is validated with `ast.literal_eval` and allowlists, never `eval`.

## Splits and sampling

The training release has 1,025,602 rows and 995,779 unique observed profiles, with 29,823 repeated profiles. Validation has 132,448 rows. Removing every profile in the full training release excludes 4,471 validation rows; deduplication leaves 127,829 retained validation profiles. Their deterministic partitions are 51,074 tuning, 25,784 calibration-fit, 25,231 calibration-check and 25,740 final-validation profiles. All variants remain with their base profile.

Profile identity is SHA256(age | dataset sex | sorted raw evidence tokens), excluding pathology, initial evidence and differential target. It detects repeated observed synthetic cases, not repeated real people. Training uses a SHA-priority uniform 32,000-profile sample plus **296 disclosed rare-class supplements**, total 32,296. Five partial views produce 161,480 augmented training examples. Supplemental sampling changes synthetic class priors slightly; it does not establish rare-condition reliability. Age and sex each independently drop out with probability 0.25 during training.

Selection uses 6,000 tune profiles and 128 actual synthetic adaptive interviews; calibration uses separate 3,000 fit / 3,000 check profiles. Final validation uses 6,000 isolated profiles. Official test inference occurs only after model, encoding, calibration display policy and question policy freeze; the full test and unseen-training subsets are reported separately in `EVALUATION_REPORT.md` and `evaluation/official_test_report.json`. Evaluation retains natural validation/test class proportions. Macro-F1 always includes all 49 labels, including zero-support labels; per-class support below 30 is flagged.

The precise hashes, support counts, validation results, duplicate counts, seeds and file-integrity checks are in `evaluation/data_manifest.json`. This card describes the pipeline, not clinical approval.

Completed official audit/evaluation: 134,529 test rows, 134,259 unique profiles, 270 duplicates; 4,901 rows overlap full training profiles. Unseen-training test subset: 129,628 rows; unseen-training-and-validation subset: 129,259. All training/validation/test source rows passed the pinned contract. Released E_54 multi-choice sets reach seven valid options; 6,367 training groups exceed five. These observations supersede a literal implementation of the paper's five-option cap, with the domain/completion checks preserved.
