"""Apply this local upgrade to a clean clone of the same application, on its feature branch."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

BASE='d4b7c20bb423286dd2890f2907d82767eeb2bb59'
SOURCE=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--clone-dir',required=True);parser.add_argument('--git-executable',default='git');parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    target=Path(args.clone_dir).resolve()
    if target==SOURCE:raise SystemExit('Use a clean Git clone; preserve the upgraded local source')
    def git(*cmd):return subprocess.check_output([args.git_executable,*cmd],cwd=target,text=True).strip()
    if Path(git('rev-parse','--show-toplevel')).resolve()!=target:raise SystemExit('Target is not the Git root')
    if git('branch','--show-current')!='feature/symptosphere-2':raise SystemExit('Target must be on feature/symptosphere-2')
    if git('rev-parse','HEAD')!=BASE:raise SystemExit('Target must start at the audited baseline commit')
    if git('status','--porcelain'):raise SystemExit('Target must be clean before applying the migration')
    manifest=json.loads((SOURCE/'evaluation/changed_files.json').read_text(encoding='utf-8'))
    changes=manifest['changes']
    for record in changes:
        name=record['path'];src=(SOURCE/name).resolve();dst=(target/name).resolve()
        if not src.is_relative_to(SOURCE) or not dst.is_relative_to(target) or '.git' in Path(name).parts:raise SystemExit('Unsafe manifest path')
        if record['change']!='deleted':
            if not src.is_file():raise SystemExit(f'Missing upgrade file: {name}')
            if record.get('sha256') and hashlib.sha256(src.read_bytes()).hexdigest()!=record['sha256']:raise SystemExit(f'Upgrade integrity changed: {name}')
    print(f'Validated {len(changes)} file changes on the audited feature branch.')
    if not args.apply:print('Dry run only. Add --apply to copy the reviewed migration.');return
    for record in changes:
        src=(SOURCE/record['path']).resolve();dst=(target/record['path']).resolve()
        if record['change']=='deleted':
            if dst.is_file():dst.unlink()  # Individual guarded paths only, no recursive deletion.
        else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    shutil.copy2(SOURCE/'evaluation/changed_files.json',target/'evaluation/changed_files.json')
    print('Migration applied locally. Review git diff, run checks, then commit. Nothing was pushed.')

if __name__=='__main__':main()
