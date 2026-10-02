"""Adapted from the supplied handoff reproduction, with explicit CLI directories."""
from pathlib import Path
import sys,os,json,hashlib,time,sqlite3,warnings,platform
import argparse
parser=argparse.ArgumentParser(description='Read and reproduce the trusted original baseline; no new model selection')
parser.add_argument('--baseline-dir',required=True);parser.add_argument('--output-dir',required=True);args=parser.parse_args()
repo=Path(args.baseline_dir).resolve();sys.path.insert(0,str(repo))
import numpy as np,pandas as pd,sklearn,joblib
from sklearn.model_selection import StratifiedKFold,cross_val_score
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score,f1_score,log_loss
out=Path(args.output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
train=pd.read_csv(repo/'dataset/training_data.csv');test=pd.read_csv(repo/'dataset/test_data.csv')
rawcols=train.columns.tolist();train=train.loc[:,~train.columns.str.contains('^Unnamed')];test=test.loc[:,~test.columns.str.contains('^Unnamed')]
x=train.drop(columns='prognosis');xt=test.drop(columns='prognosis').reindex(columns=x.columns);y=train.prognosis
ts=set(map(tuple,x.to_numpy()));rs=set(map(tuple,train.to_numpy()));
data={'train_rows':len(train),'test_rows':len(test),'feature_count':x.shape[1],'labels':int(y.nunique()),'extra_raw_columns':[c for c in rawcols if c.startswith('Unnamed')],'exact_duplicate_rows_after_first':int(train.duplicated().sum()),'unique_rows':len(train.drop_duplicates()),'unique_feature_vectors':len(x.drop_duplicates()),'test_feature_vectors_seen_in_train':sum(tuple(v) in ts for v in xt.to_numpy()),'test_full_rows_seen_in_train':sum(tuple(v) in rs for v in test.to_numpy()),'missing_after_drop':int(train.isna().sum().sum()),'non_binary_features':[c for c in x if not set(x[c].unique())<={0,1}],'constant_features':[c for c in x if x[c].nunique()==1],'label_distribution':y.value_counts().sort_index().to_dict(),'unique_rows_per_label':train.drop_duplicates().prognosis.value_counts().sort_index().to_dict(),'conflicting_feature_groups':int(train.groupby(list(x.columns)).prognosis.nunique().gt(1).sum())}
cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42);overlap=[]
for a,b in cv.split(x,y):
    known=set(map(tuple,x.iloc[a].to_numpy()));overlap.append(sum(tuple(v) in known for v in x.iloc[b].to_numpy())/len(b))
data['cv_validation_feature_overlap_fraction']=overlap
(out/'legacy_data_audit.json').write_text(json.dumps(data,indent=2),encoding='utf-8');print('DATA',data['exact_duplicate_rows_after_first'],data['unique_rows'],data['test_feature_vectors_seen_in_train'],flush=True)
if hashlib.sha256((repo/'ml/models/model_bundle.joblib').read_bytes()).hexdigest()!='4101964bfc15056b700ffe7b3d776e13aa57b3c17658e02a8fb7c1fd3e650c6e':raise ValueError('Baseline artifact differs from the trusted audited original')
with warnings.catch_warnings(record=True) as ws:
    bundle=joblib.load(repo/'ml/models/model_bundle.joblib')
model=bundle['best_model'];encoder=bundle['encoder'];yt=encoder.transform(test.prognosis);pred=model.predict(xt);proba=model.predict_proba(xt)
result={'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'joblib':joblib.__version__,'bundle_class':type(model).__name__,'bundle_name':bundle['best_model_name'],'bundle_keys':list(bundle),'bundle_bytes':(repo/'ml/models/model_bundle.joblib').stat().st_size,'artifact_test_accuracy':float(accuracy_score(yt,pred)),'artifact_test_top3':float(np.mean([target in np.argsort(p)[-3:] for target,p in zip(yt,proba)])),'artifact_test_macro_f1':float(f1_score(yt,pred,average='macro')),'artifact_test_log_loss':float(log_loss(yt,proba,labels=np.arange(len(encoder.classes_)))),'load_warnings':[str(w.message) for w in ws]}
for name,df in [('raw',train),('deduplicated',train.drop_duplicates())]:
    scores=cross_val_score(SVC(probability=True,C=3.0,gamma='scale',kernel='rbf',random_state=42),df.drop(columns='prognosis'),df.prognosis,cv=cv,n_jobs=1)
    result[name+'_svm_cv_scores']=scores.tolist();print(name,'CV',scores,flush=True)
partial=[];rng=np.random.default_rng(42)
for keep in [1.0,.8,.6,.4]:
    masked=xt.to_numpy().copy();masked[(rng.random(masked.shape)>keep)&(masked==1)]=0
    p=model.predict_proba(pd.DataFrame(masked,columns=x.columns));partial.append({'positive_evidence_retention':keep,'top1_via_proba':float(np.mean(np.argmax(p,axis=1)==yt)),'top3':float(np.mean([target in np.argsort(v)[-3:] for target,v in zip(yt,p)]))})
result['legacy_partial_positive_dropout_probe']=partial
os.environ['DATABASE_PATH']=str(out/'runtime.db')
start=time.perf_counter();import app;result['app_import_ms']=(time.perf_counter()-start)*1000
client=app.app.test_client();checks=[]
for path in ['/','/predict','/about','/api/translations/en','/api/translations/hi','/api/translations/fr','/api/health','/nonexistent']:
    r=client.get(path);checks.append({'method':'GET','path':path,'status':r.status_code,'bytes':len(r.data)})
for name,params in [('valid',{'symptoms':['headache','nausea']}),('empty',{}),('unknown',{'symptoms':['invented_symptom']}),('duplicates',{'symptoms':['headache','headache']})]:
    r=client.post('/results',data=params);checks.append({'method':'POST','case':name,'status':r.status_code,'location':r.headers.get('Location'),'contains_prediction':'Prediction Output' in r.get_data(as_text=True)})
checks.append({'method':'POST','case':'json_to_form_route','status':client.post('/results',json={'symptoms':['headache']}).status_code})
result['local_smoke_checks']=checks;result['model_ready']=app.app.config['MODEL_READY']
conn=sqlite3.connect(f'file:{repo / "database/sympthosphere.db"}?mode=ro',uri=True)
result['sqlite_counts']={t:conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['disease_info','doctors','disease_doctor_map']};conn.close()
result['unknown_vs_empty_same_prediction']=app.app.config['PREDICTOR'].predict_top3(['invented_symptom'])==app.app.config['PREDICTOR'].predict_top3([])
(out/'legacy_baseline_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2),flush=True)

