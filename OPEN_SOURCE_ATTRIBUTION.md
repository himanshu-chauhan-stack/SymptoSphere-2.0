# Sources and attribution

## Existing primary application

SymptoSphere, https://github.com/himanshu-chauhan-stack/SymptoSphere, audited source commit `d4b7c20bb423286dd2890f2907d82767eeb2bb59`. Original creator/team credit preserved: Himanshu Chauhan, Avishhoray Raj, Nihal Kumar. No root LICENSE was supplied; this upgrade does not assign a new license to their code or assert permission for unrelated redistribution. The baseline is preserved in a rollback archive. Legacy dataset licensing/provenance is not established; it is retired from new inference and excluded from staging.

## DDXPlus

Fansi Tchango, A.; Goel, R.; Wen, Z.; Martel, J.; Ghosn, J. **DDXPlus: A New Dataset for Automatic Medical Diagnosis**, NeurIPS 2022, https://arxiv.org/abs/2205.09148. Pinned English release DOI https://doi.org/10.6084/m9.figshare.22687585.v2, CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ . Metadata supplied in the handoff is retained as source evidence. Raw ontology was copied unchanged. Derived material: encoded/sampled training views, one trained classifier, synthetic evaluation, controlled English aliases and a coarse engineering region mapping. These adaptations are not endorsed by the authors. The original proprietary generation knowledge base is not included, reconstructed or claimed open source.

## Human Atlas and geometry

Atlas reference: https://github.com/ashemag/human-atlas, source commit `1c38bf35c254a891200d3cedecfd57abebe83d8d`. Code MIT, copyright (c) 2026 ashemag; complete license preserved at `body_explorer/LICENSE` and the compiled viewer's notice. The original user-supplied Atlas folder remains untouched. Integration changes: same-origin lazy iframe, `/static/body-map/` base path, gzip-only geometry, timeout/cancellation, reduced motion, user-selection-only navigation bridge, explicit non-diagnostic labels and Vite typing. Original mesh/concept identities and gzip geometry are unchanged and independently validated.

**BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International.** License: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html (source last updated 2025-02-27), https://creativecommons.org/licenses/by/4.0/ . Source geometry/metadata: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html . Source publication: Mitsuhashi et al., *BodyParts3D: 3D structure database for anatomical concepts*, https://academic.oup.com/nar/article/37/suppl_1/D782/1000752 . The supplied Atlas's conversion/simplification/color/system adaptations and this integration are disclosed in `body_explorer/public/ATTRIBUTION.md`, copied into the built viewer. An adult male reference does not represent every body, demographic or anatomical variation.

## Software dependencies

Python runtime: Flask/Werkzeug/Jinja2/MarkupSafe/itsdangerous (Pallets, BSD family), blinker (MIT), Click (BSD), NumPy/SciPy/scikit-learn (BSD), joblib (BSD), threadpoolctl (BSD). Offline/test tools: pandas (BSD), pytest (MIT), Playwright (Apache-2.0). Installed wheels contain their own license notices; dependencies are installed from pinned requirements rather than copied into the distribution.

Viewer uses React/ReactDOM (MIT), Three.js (MIT), lucide-react (ISC), Base UI/shadcn components (MIT), class-variance-authority/clsx/tailwind-merge (MIT), Tailwind and tw-animate-css (MIT), Vite/TypeScript build tooling and lockfile dependencies. Complete installed npm package license texts are collected in `body_explorer/THIRD_PARTY_NOTICES.txt` and copied into the static viewer. Included original source/lockfile/LICENSE and generated notices preserve credits; no root relicense is implied.

## Care references and original assets

Limited independent safety criteria cite https://www.nhs.uk/symptoms/chest-pain/ (reviewed 2023-08-08) and https://www.nhs.uk/conditions/stroke/symptoms/ (reviewed 2024-09-12). Criteria are engineering adaptations, not exhaustive triage or NHS endorsement. The chest-pain page's published next-review date has elapsed; check currency and obtain clinician review before broader use. No third-party medical photographs or invented doctor personas are used. The small brand/body-outline SVGs were drawn for this implementation and are illustrative navigation assets.
