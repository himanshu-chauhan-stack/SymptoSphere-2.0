"""Pinned acquisition, whole-file validation and profile-isolated offline sampling."""
import ast
import csv
import hashlib
import heapq
import io
import json
import math
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from .evidence_schema import EvidenceSchema, EvidenceError, empty_state, ORPHAN_PARENTS

SEED=20261002
REQUIRED_COLUMNS={'AGE','SEX','PATHOLOGY','EVIDENCES','INITIAL_EVIDENCE','DIFFERENTIAL_DIAGNOSIS'}


def profile_hash(row,tokens):
    return hashlib.sha256((str(int(row['AGE']))+'|'+row['SEX']+'|'+'|'.join(sorted(tokens))).encode()).hexdigest()


def priority(fingerprint,salt='sample'):
    return int(hashlib.sha256(f'{SEED}|{salt}|{fingerprint}'.encode()).hexdigest()[:16],16)


def verify_release(directory,schema):
    records=json.loads((schema.directory/'ddxplus_sources.json').read_text(encoding='utf-8'))
    verified=[]
    for r in records:
        if not r['file'].startswith('release_'):continue
        p=Path(directory)/r['file']
        if p.suffix=='.json':p=schema.directory/p.name
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        if sha!=r['sha256']:raise ValueError(f'Pinned data checksum mismatch: {p.name}')
        verified.append({'file':p.name,'sha256':sha,'bytes':p.stat().st_size,'url':r['url']})
    return verified


def acquire(directory,schema):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    for r in json.loads((schema.directory/'ddxplus_sources.json').read_text()):
        if not r['file'].endswith('_patients.zip'):continue
        p=directory/r['file']
        if not p.exists():
            with urllib.request.urlopen(r['url'],timeout=120) as response, p.open('wb') as out:
                while block:=response.read(1024*1024):out.write(block)
    return verify_release(directory,schema)


def iter_records(path,schema):
    with zipfile.ZipFile(path) as z:
        members=[n for n in z.namelist() if not n.endswith('/') and not n.startswith('__MACOSX/')]
        if len(members)!=1:raise ValueError('Expected exactly one dataset CSV')
        with io.TextIOWrapper(z.open(members[0]),encoding='utf-8') as f:
            reader=csv.DictReader(f)
            if set(reader.fieldnames)!=REQUIRED_COLUMNS:raise ValueError('Dataset column drift')
            for row in reader:
                age=int(row['AGE'])
                if not 0<=age<=109 or row['SEX'] not in ('M','F') or row['PATHOLOGY'] not in schema.conditions:raise ValueError('Invalid dataset target/demographics')
                tokens,groups=schema.parse_tokens(row['EVIDENCES'])
                initial=row['INITIAL_EVIDENCE']
                if initial not in tokens or initial not in schema.evidences or schema.evidences[initial]['data_type']!='B':raise ValueError('Invalid initial evidence')
                dd=ast.literal_eval(row['DIFFERENTIAL_DIAGNOSIS'])
                if not isinstance(dd,list) or not dd or any(not isinstance(a,list) or len(a)!=2 or a[0] not in schema.conditions or type(a[1]) not in (float,int) or not math.isfinite(a[1]) or not 0<=a[1]<=1 for a in dd):raise ValueError('Invalid differential')
                if len({a[0] for a in dd})!=len(dd) or abs(sum(a[1] for a in dd)-1)>1e-5:raise ValueError('Invalid differential distribution')
                row['AGE']=age
                yield row,tokens,groups,profile_hash(row,tokens)


def heap_add(heap,size,key,row):
    item=(-key,row['_profile'],row)
    if len(heap)<size:heapq.heappush(heap,item)
    elif item>heap[0]:heapq.heapreplace(heap,item)


def prepare(directory,out,schema,sample_size=32000,min_support=128):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    release=verify_release(directory,schema)
    train_profiles={};sample=[];per_class={k:[] for k in schema.classes};counts=Counter();rows=0;multi_max=Counter();multi_over5=0
    for row,tokens,groups,h in iter_records(Path(directory)/'release_train_patients.zip',schema):
        rows+=1;counts[row['PATHOLOGY']]+=1
        for key,values in groups.items():
            if schema.evidences[key]['data_type']=='M':
                multi_max[key]=max(multi_max[key],len(values));multi_over5+=len(values)>5
        if h in train_profiles:
            if train_profiles[h]!=row['PATHOLOGY']:raise ValueError('Conflicting profile labels')
            continue
        train_profiles[h]=row['PATHOLOGY'];row['_profile']=h
        k=priority(h);heap_add(sample,sample_size,k,row);heap_add(per_class[row['PATHOLOGY']],min_support,k,row)
        if rows%100000==0:print('validated train',rows,flush=True)
    selected={r['_profile']:r for _,_,r in sample}
    base_support=Counter(r['PATHOLOGY'] for r in selected.values())
    supplements={}
    for label,heap in per_class.items():
        if base_support[label]<min_support:
            supplements[label]=0
            for _,_,r in heap:
                if r['_profile'] not in selected:selected[r['_profile']]=r;supplements[label]+=1
    train=sorted(selected.values(),key=lambda r:priority(r['_profile']))
    pools={k:[] for k in ['tune','calibration','calibration_check','final_validation']}
    val_profiles={};val_counts=Counter();overlap=0;val_rows=0
    for row,tokens,groups,h in iter_records(Path(directory)/'release_validate_patients.zip',schema):
        val_rows+=1;val_counts[row['PATHOLOGY']]+=1
        if h in train_profiles:overlap+=1;continue
        if h in val_profiles:
            if val_profiles[h]!=row['PATHOLOGY']:raise ValueError('Conflicting validation profile')
            continue
        val_profiles[h]=row['PATHOLOGY'];row['_profile']=h
        bucket=priority(h,'partition')%10
        partition='tune' if bucket<4 else 'calibration' if bucket<6 else 'calibration_check' if bucket<8 else 'final_validation'
        pools[partition].append(row)
    manifest={'protocol_version':'profile-isolated-mask-v1','release':release,'seed':SEED,
              'train_rows_validated':rows,'train_unique_profiles':len(train_profiles),'train_duplicates':rows-len(train_profiles),
              'train_class_counts':dict(counts),'train_base_sample':len(train),'uniform_sample_requested':sample_size,
              'rare_training_supplements':supplements,'sample_class_support':dict(Counter(r['PATHOLOGY'] for r in train)),
              'validation_rows_validated':val_rows,'validation_train_overlap_excluded':overlap,
              'validation_unique_retained':len(val_profiles),'validation_class_counts':dict(val_counts),
              'invalid_rows':0,'invalid_tokens':0,'duplicate_token_rows':0,
              'multi_choice_max_values':dict(multi_max),'multi_choice_groups_above_paper_five_limit':multi_over5,
              'partitions':{k:{'profiles':len(v),'support':dict(Counter(r['PATHOLOGY'] for r in v))} for k,v in pools.items()},
              'train_partition_overlap':{k:0 for k in pools},'official_test_inference_used':False,
              'orphan_parent_exceptions':{'references':ORPHAN_PARENTS, 'policy':'Five missing parents explicitly treated as independent self-contained binary history questions; engineering review, no clinician review'},
              'profile_definition':'SHA256 age|dataset sex|sorted raw evidence tokens; excludes pathology, differential and initial evidence'}
    for k,records in {'train':train,**pools}.items():
        records=sorted(records,key=lambda r:priority(r['_profile']))
        with (out/f'{k}.jsonl').open('w',encoding='utf-8') as f:
            for r in records:f.write(json.dumps(r,ensure_ascii=False)+'\n')
        manifest.setdefault('partition_file_hashes',{})[k]=hashlib.sha256((out/f'{k}.jsonl').read_bytes()).hexdigest()
    (out/'train_profiles.txt').write_text('\n'.join(sorted(train_profiles)),encoding='utf-8')
    (out/'validation_profiles.txt').write_text('\n'.join(sorted(val_profiles)),encoding='utf-8')
    (out/'data_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('PREPARED',len(train),manifest['partitions'],flush=True)
    return manifest


def load_records(path,limit=None):
    records=[]
    with Path(path).open(encoding='utf-8') as f:
        for i,line in enumerate(f):
            if limit is not None and i>=limit:break
            records.append(json.loads(line))
    return records
