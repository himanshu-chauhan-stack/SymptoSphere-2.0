# SymptoSphere 2 model card

One selected scikit-learn classifier performs inference. This application does **not** ensemble models. The legacy system's active classifier was a single SVC; its reported high accuracy came from an unsuitable repeated-profile dataset. The replacement is selected by real, isolated validation, not popularity.

Completed selection: **LogisticRegression**, model version `symptosphere2-ddxplus-v1`, sparse validation score **0.56502847**, versus HGB **0.50701724**. On the complete 134,529-row official synthetic test: initial-only Top-1/Top-3/Macro-F1 = **0.3729 / 0.6095 / 0.3597**; seven randomly observed answers = **0.4486 / 0.6844 / 0.4392**. The independent scalar-temperature gate failed (temperature 0.93881215); raw classifier ranks remain the shipped policy, with no UI percentages. The full report retains unseen-profile metrics and uncertainty intervals.

## Inputs, training and selection

The shared encoder has 1,200 ordered features: allowed evidence values, one known mask per question, age/109 plus age-known, and M/F sex values plus sex-known. No label, differential, full hidden record, raw free text, anatomy ID, anatomy sex or user identifier enters inference. Missing demographics remain unknown. The source ontology/class/feature ordering, sklearn version, policy version and artifact SHA256 are checked before loading the trusted shipped bundle. There is no startup training or legacy fallback. Never accept uploaded joblib/pickle files; hash checking assumes the manifest is trusted alongside the artifact.

Candidates: LogisticRegression C=1, lbfgs, max_iter=300; HistGradientBoostingClassifier 35 iterations, 15 leaves, L2=1, early stopping disabled. Seed 42, four-thread fitting context. Five augmented training views: full, 40% retention, initial complaint, five answers and ten answers; independent 25% age/sex dropout. Full retention reveals retained parents before children, so it equals canonical full evidence regardless of ontology order.

Predeclared selection score: mean all-label Macro-F1 on initial-only and 40%-retention tuning views plus actual adaptive 3/5/7/10-turn tuning interviews. Within 0.002, choose lower measured warm one-row p95 latency. The final artifact name, score, parameters, warnings, timings and candidate comparison are recorded in `ml/models/ddxplus_manifest.json`, `evaluation/candidate_report.json` and `EVALUATION_REPORT.md`. The test set never breaks ties.

## Probability and uncertainty policy

Compare identity with one scalar temperature on independent calibration fit/check partitions across sparse and richer views. The sparse Brier/ECE gate allows at most 0.005 degradation per evaluated sparse view. **The UI always withholds percentages**, even if this synthetic gate passes: clinical calibration, coverage and clinical utility have not been validated. UI output is three ranked possible conditions with limited-information wording. Empty, unknown-only, absent-only, history-only and self-declared unsupported/unsure scope receive no forced condition match. The scope check is an ontology safeguard, not a validated out-of-distribution detector.

## Questions and explanations

Follow-ups use training-only class-conditional answer-set frequencies and approximate expected model entropy reduction. Sixteen candidates are shortlisted; hypothetical valid answers are batched through the selected classifier. Multi-choice uses observed joint sets with explicit residual mass, never invented combinations. Skips remain unknown and do not repeat. Parent applicability is enforced. The default UI offers seven follow-up prompts, with explicit optional continuation. Synthetic rollouts compare adaptive, fixed and random questions with disclosed skips and demographic missingness. No RL/LLM question policy was introduced.

Explanation removes one whole observed answer group, including dependants, and recalculates the actual classifier. Positive/negative differences support the displayed model effect; they are not causal medical explanations, validated clinical evidence or calibrated risk. Strict local English phrase matching returns exact source spans and canonical IDs for user confirmation. It has limited context/negation handling, never directly writes evidence, and invokes no external language model.

## Use limits

Educational research prototype only, 49 synthetic conditions and selected complaint scope. No real-patient validation, India validation, clinical uncertainty guarantee, comprehensive emergency assessment or independent clinician review. General primary-care navigation is the safe fallback; condition-specific specialty/content summaries are deferred because they lack reviewed sources. No medications, prescriptions, fictional doctors, booking, payment or doctor photos are presented. Hindi covers interface labels; evidence questions/options/guidance remain English pending human review. Rare classes with limited evaluation support cannot support strong reliability claims. Optional adult male reference anatomy is navigation only, independent of model features and entered demographics.
