"""Offline candidate comparison. Official test inference requires frozen_selection.json."""
from __future__ import annotations
import argparse
import collections
import hashlib
import io
import json
import os
import platform
import time
import warnings
from pathlib import Path
import joblib
import numpy as np
import sklearn
from scipy import sparse
from scipy.optimize import minimize_scalar
from scipy.special import softmax
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits
from .ddxplus_data import prepare,load_records,acquire,verify_release
from .evidence_schema import EvidenceSchema,empty_state,ORPHAN_PARENTS
from .encoding import EvidenceEncoder
from .evaluate import metrics,masked_state,differential_metrics
from .question_engine import QuestionEngine,POLICY_VERSION

VIEWS={'initial':{'budget':1},'answers3':{'budget':3},'answers5':{'budget':5},
       'answers7':{'budget':7},'answers10':{'budget':10},'retention40':{'retention':.4},
       'retention80':{'retention':.8},'full':{'retention':1.0},
       'unknown_demographics7':{'budget':7,'demo_missing':1}}


def write_json(path,data):
    Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False,default=lambda x:x.item() if hasattr(x,'item') else str(x)),encoding='utf-8')


def make_view(schema,encoder,rows,view,seed=42,training=False):
    rng=np.random.default_rng(seed);x=np.empty((len(rows),len(encoder.features)),dtype=np.float32);counts=[]
    for i,row in enumerate(rows):
        full=schema.full_state(row);args=dict(VIEWS[view])
        if training:args['demo_missing']=.25
        state=masked_state(schema,full,row['INITIAL_EVIDENCE'],rng,**args)
        x[i]=encoder.encode(state);counts.append(len(state['answers']))
    return x,counts


def frequencies(schema,rows):
    counts={k:collections.Counter() for k in schema.ids};class_totals={k:collections.Counter() for k in schema.ids}
    for row in rows:
        full=schema.full_state(row)
        for k,a in full['answers'].items():
            key=json.dumps(a,sort_keys=True);counts[k][key]+=1;class_totals[k][(key,row['PATHOLOGY'])]+=1
    out={}
    for k,total in counts.items():
        limit=8 if schema.evidences[k]['data_type']=='M' else len(total)
        options=[a for a,n in sorted(total.items(),key=lambda t:(-t[1],t[0]))[:limit]]
        if len(options)<2:continue
        byclass=class_totals[k]
        denominator=np.array([sum(n for (a,c),n in byclass.items() if c==label)+len(total) for label in schema.classes],dtype=float)
        dist=np.array([[byclass[(a,label)]+1 for label in schema.classes] for a in options])/denominator
        out[k]={'answers':[json.loads(a) for a in options],'probabilities':dist.tolist(),
                'represented_training_sets':len(options),'total_training_sets':len(total),
                'residual_policy':'Unrepresented joint sets retain current entropy; no invented combination'}
    return out


def y_values(schema,rows):
    index={k:i for i,k in enumerate(schema.classes)}
    return np.array([index[r['PATHOLOGY']] for r in rows])


def evaluate_views(schema,encoder,model,rows,bootstrap=0):
    y=y_values(schema,rows);results={}
    for i,view in enumerate(VIEWS):
        x,count=make_view(schema,encoder,rows,view,400+i);p=model.predict_proba(x)
        m=metrics(p,y,schema.classes,[r['_profile'] for r in rows],bootstrap)
        m['mean_known_answers']=float(np.mean(count));results[view]=m
    return results


def interviews(schema,encoder,model,freq,rows,policies=('adaptive','random','fixed'),skip_rate=.15):
    engine=QuestionEngine(schema,encoder,model,freq);results={};labels=y_values(schema,rows)
    for policy in policies:
        rng=np.random.default_rng(782);snapshots={k:[] for k in [1,3,5,7,10]};observed={k:[] for k in snapshots};skips=[];start=time.perf_counter()
        for row in rows:
            full=schema.full_state(row);state=empty_state();state['demographics']=dict(full['demographics'])
            if rng.random()<.25:state['demographics']['age']=None
            if rng.random()<.25:state['demographics']['dataset_sex']='unknown'
            initial=row['INITIAL_EVIDENCE'];state['answers'][initial]=full['answers'][initial]
            for turn in range(1,11):
                if turn in snapshots:
                    snapshots[turn].append(model.predict_proba(encoder.encode(state)[None])[0]);observed[turn].append(len(state['answers']))
                if turn==10:break
                candidates=engine.candidates(state)
                if not candidates:continue
                if policy=='adaptive':
                    q=engine.choose(state,cap=False);k=q['id'] if q else None
                elif policy=='random':k=candidates[int(rng.integers(len(candidates)))]
                else:
                    common=['E_53','E_201','E_91','E_97','E_66','E_181','E_148','E_129','E_151','E_79']
                    k=min(candidates,key=lambda q:(common.index(q) if q in common else 100,q))
                if k is None:continue
                if k not in full['answers'] or rng.random()<skip_rate:state['skipped_questions'].append(k)
                else:state['answers'][k]=full['answers'][k]
            skips.append(len(state['skipped_questions']))
        results[policy]={'seconds':time.perf_counter()-start,'simulated_skip_rate':skip_rate,'mean_skipped':float(np.mean(skips)),
            'turn_metrics':{str(k):{**metrics(np.array(v),labels,schema.classes,[r['_profile'] for r in rows],100),
                                  'mean_completed_answers':float(np.mean(observed[k]))} for k,v in snapshots.items()},
            'note':'Turn budget includes initial complaint and skips; queried hidden answers are revealed only after policy selection'}
        print('INTERVIEW',policy,len(rows),'seconds',results[policy]['seconds'],flush=True)
    return results


def calibrate(schema,encoder,model,fit_rows,check_rows):
    views=['initial','answers3','answers5','answers7','answers10','retention40','full'];fit=[];target=[]
    for v in views:
        x,_=make_view(schema,encoder,fit_rows,v,205);fit.append(model.predict_proba(x));target.append(y_values(schema,fit_rows))
    logp=np.log(np.clip(np.vstack(fit),1e-12,1));y=np.concatenate(target)
    opt=minimize_scalar(lambda t:float(-np.mean(np.log(np.clip(softmax(logp/t,axis=1)[np.arange(len(y)),y],1e-12,1)))),bounds=(.25,5),method='bounded')
    temperature=float(opt.x);check={};passes=True
    for v in views:
        x,_=make_view(schema,encoder,check_rows,v,206);p=model.predict_proba(x);scaled=softmax(np.log(np.clip(p,1e-12,1))/temperature,axis=1);y=y_values(schema,check_rows)
        before=metrics(p,y,schema.classes,bootstrap=0);after=metrics(scaled,y,schema.classes,bootstrap=0)
        if v.startswith('answers') or v=='initial':passes &= after['brier_sum']<=before['brier_sum']+.005 and after['top_label_ece_10_equal_width']<=before['top_label_ece_10_equal_width']+.005
        check[v]={'identity':before,'temperature':after}
    return {'method_compared':'identity versus one scalar temperature; independent fit/check profiles','temperature':temperature,
            'fit_profiles':len(fit_rows),'check_profiles':len(check_rows),'gate_passed':bool(passes),'selected_display_policy':'rank_only',
            'reason':'No clinical calibration or coverage validation. UI percentages withheld even if synthetic gate passes.','check_metrics':check}


def train(args):
    schema=EvidenceSchema();encoder=EvidenceEncoder(schema);out=Path(args.work_dir);out.mkdir(parents=True,exist_ok=True)
    if args.acquire:acquire(args.data_dir,schema)
    if not (out/'data_manifest.json').exists():prepare(args.data_dir,out,schema,args.sample_size)
    data=json.loads((out/'data_manifest.json').read_text())
    verify_release(args.data_dir,schema)
    for name,digest in data['partition_file_hashes'].items():
        if hashlib.sha256((out/f'{name}.jsonl').read_bytes()).hexdigest()!=digest:raise ValueError('Prepared partition integrity mismatch')
    data['orphan_parent_exceptions']['references']=ORPHAN_PARENTS
    rows=load_records(out/'train.jsonl')
    tune=load_records(out/'tune.jsonl',args.tune_size);fit=load_records(out/'calibration.jsonl',3000);check=load_records(out/'calibration_check.jsonl',3000);final=load_records(out/'final_validation.jsonl',6000)
    freq=frequencies(schema,rows);write_json(out/'frequencies.json',freq)
    train_views=['full','retention40','initial','answers5','answers10'];matrices=[]
    for i,v in enumerate(train_views):
        x,_=make_view(schema,encoder,rows,v,120+i,training=True);matrices.append(x);print('encoded train',v,flush=True)
    xtrain=np.vstack(matrices);del matrices
    ytrain=np.tile(np.array([r['PATHOLOGY'] for r in rows]),len(train_views))
    if sorted(set(ytrain))!=schema.classes:raise ValueError('Missing training classes')
    candidates={'LogisticRegression':LogisticRegression(C=1,max_iter=300,solver='lbfgs',random_state=42),
                'HistGradientBoosting':HistGradientBoostingClassifier(max_iter=35,max_leaf_nodes=15,l2_regularization=1,early_stopping=False,random_state=42)}
    report={'protocol_version':'profile-isolated-mask-v1','environment':{'python':platform.python_version(),'sklearn':sklearn.__version__,'numpy':np.__version__},
            'train_base_profiles':len(rows),'augmented_train_rows':len(ytrain),'feature_count':len(encoder.features),'train_views':train_views,
            'demographic_dropout_probability':.25,'tune_profiles':len(tune),
            'selection_rule':'Mean Macro-F1 over initial, 40% retention, and adaptive 3/5/7/10 turns; ties within .002 prefer faster one-row inference',
            'official_test_used_in_selection':False,'models':{},'data_manifest':data}
    fitted={};scores=[]
    for name,model in candidates.items():
        print('TRAIN',name,flush=True);start=time.perf_counter()
        with warnings.catch_warnings(record=True) as w:model.fit(sparse.csr_matrix(xtrain) if name=='LogisticRegression' else xtrain,ytrain)
        fitted[name]=model;rec={'fit_seconds':time.perf_counter()-start,'warnings':[str(t.message) for t in w],'parameters':model.get_params()}
        rec['validation']=evaluate_views(schema,encoder,model,tune)
        rec['interviews']=interviews(schema,encoder,model,freq,tune[:args.interview_size],policies=('adaptive',))
        a=rec['interviews']['adaptive']['turn_metrics'];score=float(np.mean([rec['validation']['initial']['macro_f1'],rec['validation']['retention40']['macro_f1'],*[a[str(k)]['macro_f1'] for k in [3,5,7,10]]]))
        lat=[]
        for _ in range(30):
            t=time.perf_counter();model.predict_proba(xtrain[:1]);lat.append((time.perf_counter()-t)*1000)
        rec['warm_one_row_ms']={'mean':float(np.mean(lat)),'p95':float(np.quantile(lat,.95)),'samples':30}
        buffer=io.BytesIO();joblib.dump(model,buffer);rec['uncompressed_model_bytes']=len(buffer.getvalue());rec['selection_score']=score
        report['models'][name]=rec;scores.append((score,name));write_json(out/'candidate_report.json',report)
        print('DONE',name,'score',score,'fit_seconds',rec['fit_seconds'],flush=True)
    best=max(scores)[0];eligible=[name for score,name in scores if best-score<=.002]
    winner=min(eligible,key=lambda name:report['models'][name]['warm_one_row_ms']['p95']);model=fitted[winner];del xtrain,ytrain
    report['selected_model']=winner;report['calibration']=calibrate(schema,encoder,model,fit,check)
    report['final_validation']=evaluate_views(schema,encoder,model,final,bootstrap=100)
    report['final_validation_interviews']=interviews(schema,encoder,model,freq,final[:max(128,args.interview_size)])
    fullx,_=make_view(schema,encoder,final,'answers7');p=model.predict_proba(fullx);report['reference_differential']=differential_metrics(p,final,schema.classes)
    report['subgroups']={};y=y_values(schema,final)
    for key,predicate in [('dataset_sex_M',lambda r:r['SEX']=='M'),('dataset_sex_F',lambda r:r['SEX']=='F'),('age_under18',lambda r:r['AGE']<18),('age_65plus',lambda r:r['AGE']>=65)]:
        mask=np.array([predicate(r) for r in final]);report['subgroups'][key]=metrics(p[mask],y[mask],schema.classes,bootstrap=0)
    directory=Path(__file__).parent/'models';directory.mkdir(exist_ok=True);joblib.dump({'model':model,'frequencies':freq},directory/'ddxplus_bundle.joblib',compress=3)
    manifest={**encoder.metadata(),'model_version':'symptosphere2-ddxplus-v1','sklearn_version':sklearn.__version__,'selected_model':winner,
              'question_policy_version':POLICY_VERSION,'calibration_policy':'rank_only','bundle_sha256':hashlib.sha256((directory/'ddxplus_bundle.joblib').read_bytes()).hexdigest(),
              'train_class_support':data['sample_class_support'],'train_base_profiles':len(rows),'selection_score':report['models'][winner]['selection_score'],
              'report_path':'evaluation/candidate_report.json','protocol_version':report['protocol_version'],'ontology_orphan_policy':ORPHAN_PARENTS,
              'evaluation':{'tune_profiles':len(tune),'final_validation_profiles':len(final)}}
    write_json(out/'candidate_report.json',report);manifest['candidate_report_sha256']=hashlib.sha256((out/'candidate_report.json').read_bytes()).hexdigest()
    manifest['training_code_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    write_json(directory/'ddxplus_manifest.json',manifest);write_json(out/'frozen_selection.json',manifest)
    print('FROZEN',winner,manifest['bundle_sha256'],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',required=True);parser.add_argument('--work-dir',required=True)
    parser.add_argument('--sample-size',type=int,default=32000);parser.add_argument('--tune-size',type=int,default=6000);parser.add_argument('--interview-size',type=int,default=128)
    parser.add_argument('--acquire',action='store_true');parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args();os.environ.setdefault('LOKY_MAX_CPU_COUNT','4')
    with threadpool_limits(limits=4):
        if args.prepare_only:prepare(args.data_dir,args.work_dir,EvidenceSchema(),args.sample_size)
        else:train(args)


if __name__=='__main__':main()
