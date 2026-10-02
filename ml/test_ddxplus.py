"""One frozen official-test run. Never selects/tunes a model using test outputs."""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from .ddxplus_data import iter_records,verify_release
from .evidence_schema import EvidenceSchema
from .encoding import EvidenceEncoder
from .predictor import SymptoPredictor
from .train_ddxplus import VIEWS,make_view,y_values,interviews,write_json
from .evaluate import metrics,differential_metrics


def run(args):
    work=Path(args.work_dir);output=work/'official_test_report.json'
    if output.exists():raise ValueError('Official-test report already exists. Keep it; do not silently rerun or tune.')
    frozen=json.loads((work/'frozen_selection.json').read_text(encoding='utf-8'))
    schema=EvidenceSchema();encoder=EvidenceEncoder(schema);service=SymptoPredictor(schema=schema)
    if frozen!=service.metadata:raise ValueError('Shipped artifact differs from frozen validation selection')
    # Only model/encoding/policy code, not UI edits, is locked at selection time.
    for name in ['evidence_schema.py','encoding.py','question_engine.py','evaluate.py','train_ddxplus.py','test_ddxplus.py']:
        if hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()!=frozen['training_code_sha256'][name]:
            raise ValueError(f'Inference/evaluation code changed after freeze: {name}')
    release=verify_release(args.data_dir,schema);started=time.perf_counter();rows=[];seen={};duplicates=0
    print('Validating official test rows; inference has not started',flush=True)
    for row,tokens,groups,h in iter_records(Path(args.data_dir)/'release_test_patients.zip',schema):
        if h in seen:
            duplicates+=1
            if seen[h]!=row['PATHOLOGY']:raise ValueError('Conflicting test profile labels')
        seen[h]=row['PATHOLOGY'];row['_profile']=h;rows.append(row)
    train_profiles=set((work/'train_profiles.txt').read_text().splitlines())
    val_profiles=set((work/'validation_profiles.txt').read_text().splitlines())
    unseen_train=np.array([r['_profile'] not in train_profiles for r in rows])
    all_development_profiles=train_profiles|val_profiles
    unseen_all=np.array([r['_profile'] not in all_development_profiles for r in rows])
    print('Validated official rows',len(rows),'overlap masks prepared; starting frozen inference',flush=True)
    y=y_values(schema,rows);profiles=np.array([r['_profile'] for r in rows])
    report={'protocol_version':frozen['protocol_version'],'selected_model':frozen['selected_model'],
            'bundle_sha256':frozen['bundle_sha256'],'candidate_report_sha256':frozen['candidate_report_sha256'],
            'official_test_used_in_selection':False,'test_rows_validated':len(rows),'test_unique_profiles':len(seen),
            'test_duplicate_rows':duplicates,'invalid_rows':0,'invalid_tokens':0,
            'test_train_overlap_rows':int((~unseen_train).sum()),'test_unseen_training_rows':int(unseen_train.sum()),
            'test_unseen_training_and_validation_rows':int(unseen_all.sum()),'release':release,
            'metrics':{},'unseen_training_metrics':{},'unseen_training_and_validation_metrics':{},
            'note':'Official rows include profile repeats; bootstrap resamples profile groups. Unseen subsets are separately reported. Synthetic scores are not clinical accuracy.'}
    for view in VIEWS:
        predictions=[];known=[]
        # Identical per-row RNG progression over chunks; no whole-test dense feature allocation.
        # make_view owns a generator per call. This fixed batch protocol is disclosed, not
        # silently compared to validation masks (validation uses a single 6000-row call).
        for offset in range(0,len(rows),2048):
            x,count=make_view(schema,encoder,rows[offset:offset+2048],view,400+list(VIEWS).index(view)+offset)
            predictions.append(service.model.predict_proba(x));known.extend(count)
        p=np.vstack(predictions)
        report['metrics'][view]={**metrics(p,y,schema.classes,profiles,100),'mean_known_answers':float(np.mean(known))}
        report['unseen_training_metrics'][view]=metrics(p[unseen_train],y[unseen_train],schema.classes,profiles[unseen_train],100)
        report['unseen_training_and_validation_metrics'][view]=metrics(p[unseen_all],y[unseen_all],schema.classes,profiles[unseen_all],0)
        if view=='answers7':
            report['reference_differential']=differential_metrics(p,rows,schema.classes)
            report['subgroups']={}
            for name,predicate in [('dataset_sex_M',lambda r:r['SEX']=='M'),('dataset_sex_F',lambda r:r['SEX']=='F'),('age_under18',lambda r:r['AGE']<18),('age_65plus',lambda r:r['AGE']>=65)]:
                mask=np.array([predicate(r) for r in rows]);report['subgroups'][name]=metrics(p[mask],y[mask],schema.classes,bootstrap=0)
        print('TEST',view,'n',len(rows),'top1',report['metrics'][view]['top1'],'macro_f1',report['metrics'][view]['macro_f1'],flush=True)
        write_json(work/'official_test_progress.json',report)
    eligible=[r for r,m in zip(rows,unseen_all) if m]
    # Hash priority rather than target stratification: no pathology is used for selection.
    sample=sorted(eligible,key=lambda r:hashlib.sha256(('interview|'+r['_profile']).encode()).hexdigest())[:args.interview_size]
    report['interviews']=interviews(schema,encoder,service.model,service.bundle['frequencies'],sample)
    report['interview_sample_profiles']=len(sample);report['elapsed_seconds']=time.perf_counter()-started
    report['mask_protocol']='2048-row chunks; seed 400 + view ordinal + offset; initial complaint retained, parent-first retention, budgets count completed answers'
    write_json(output,report);print('OFFICIAL TEST COMPLETE',output,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',required=True);parser.add_argument('--work-dir',required=True)
    parser.add_argument('--interview-size',type=int,default=128);args=parser.parse_args()
    with threadpool_limits(limits=4):run(args)


if __name__=='__main__':main()
