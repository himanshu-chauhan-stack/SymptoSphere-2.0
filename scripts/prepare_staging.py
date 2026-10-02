"""Prepare public static files locally; performs no deployment or account operation."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'static'
TARGET=ROOT/'public'/'static'

def main():
    if not (SOURCE/'body-map/index.html').exists():raise SystemExit('Build body_explorer first: npm ci; npm run check; npm run build')
    if not (ROOT/'ml/models/ddxplus_manifest.json').exists():raise SystemExit('Shipped model manifest is missing')
    shutil.copytree(SOURCE,TARGET,dirs_exist_ok=True)
    files=[p for p in TARGET.rglob('*') if p.is_file()]
    report={'operation':'local staging asset preparation only','files':len(files),'bytes':sum(p.stat().st_size for p in files),
            'static_files':{str(p.relative_to(TARGET)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    (ROOT/'evaluation').mkdir(exist_ok=True)
    (ROOT/'evaluation/staging_assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='static_files'}))

if __name__=='__main__':main()
