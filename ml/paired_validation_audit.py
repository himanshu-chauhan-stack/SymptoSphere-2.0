"""Supplementary paired validation rollouts. Does not change or select the frozen model."""
import argparse
import hashlib
import json
import time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from .evidence_schema import empty_state
from .ddxplus_data import load_records
from .predictor import SymptoPredictor
from .evaluate import metrics
from .train_ddxplus import write_json,y_values

def run(work):
    service=SymptoPredictor();schema=service.schema;encoder=service.encoder
    rows=load_records(Path(work)/'final_validation.jsonl',128);labels=y_values(schema,rows);results={}
    common=['E_53','E_201','E_91','E_97','E_66','E_181','E_148','E_129','E_151','E_79']
    for policy in ['adaptive','random','fixed']:
        snapshots={k:[] for k in [1,3,5,7,10]};counts={k:[] for k in snapshots};skips=[];start=time.perf_counter()
        for row in rows:
            seed=int(hashlib.sha256(('paired-validation|'+row['_profile']).encode()).hexdigest()[:16],16)
            context_rng=np.random.default_rng(seed);choice_rng=np.random.default_rng(seed+1)
            full=schema.full_state(row);state=empty_state();state['demographics']=dict(full['demographics'])
            if context_rng.random()<.25:state['demographics']['age']=None
            if context_rng.random()<.25:state['demographics']['dataset_sex']='unknown'
            skip_uniforms=context_rng.random(9)  # Identical per-profile/turn across policies.
            state['answers'][row['INITIAL_EVIDENCE']]=full['answers'][row['INITIAL_EVIDENCE']]
            for turn in range(1,11):
                if turn in snapshots:snapshots[turn].append(service.probabilities(state));counts[turn].append(len(state['answers']))
                if turn==10:break
                candidates=service.questions.candidates(state)
                if not candidates:continue
                if policy=='adaptive':
                    q=service.questions.choose(state,cap=False);key=q['id'] if q else None
                elif policy=='random':key=candidates[int(choice_rng.integers(len(candidates)))]
                else:key=min(candidates,key=lambda k:(common.index(k) if k in common else 100,k))
                if key is None:continue
                if key not in full['answers'] or skip_uniforms[turn-1]<.15:state['skipped_questions'].append(key)
                else:state['answers'][key]=full['answers'][key]
            skips.append(len(state['skipped_questions']))
        results[policy]={'mean_skipped':float(np.mean(skips)),'seconds':time.perf_counter()-start,
            'turn_metrics':{str(k):{**metrics(np.array(p),labels,schema.classes,[r['_profile'] for r in rows],100),
                                    'mean_completed_answers':float(np.mean(counts[k]))} for k,p in snapshots.items()}}
    for field in ['top1','top3','macro_f1']:
        assert len({results[p]['turn_metrics']['1'][field] for p in results})==1
    report={'n':len(rows),'partition':'first 128 final-validation profiles; same profiles as frozen audit',
            'bundle_sha256':service.metadata['bundle_sha256'],'used_in_model_selection':False,
            'reason':'Frozen random baseline consumed the shared RNG for choices, changing subsequent demographic draws. This supplementary validation audit separates choice RNG and pairs demographics/skip uniforms. Original metrics are retained and disclosed.',
            'skip_probability':.15,'independent_demographic_missing_probability':.25,'policies':results}
    write_json(Path(work)/'paired_validation_interviews.json',report);print('PAIRED VALIDATION COMPLETE',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work-dir',required=True);args=parser.parse_args()
    with threadpool_limits(limits=4):run(args.work_dir)
