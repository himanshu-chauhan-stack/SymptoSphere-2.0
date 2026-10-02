"""Reproducible synthetic metrics; never interpreted as clinical performance."""
import copy
import numpy as np
from sklearn.metrics import accuracy_score,f1_score,log_loss,confusion_matrix,recall_score
from .evidence_schema import empty_state


def masked_state(schema,full,initial,rng,retention=None,budget=None,demo_missing=0):
    state=empty_state();state['demographics']=dict(full['demographics'])
    if rng.random()<demo_missing:state['demographics']['age']=None
    if rng.random()<demo_missing:state['demographics']['dataset_sex']='unknown'
    state['answers'][initial]=full['answers'][initial]
    if retention is not None:
        ids=[k for k in full['answers'] if rng.random()<retention]
        # Reveal retained parents before retained dependants, independent of JSON order.
        # Full retention must exactly equal the canonical complete profile.
        ids.sort(key=lambda k:(k in schema.parents,k))
    else:
        ids=list(full['answers']);rng.shuffle(ids)
    for k in ids:
        if budget is not None and len(state['answers'])>=budget:break
        if schema.applicable(k,state['answers']):state['answers'][k]=full['answers'][k]
    # All descendants share their parents' applicability and observed knownness.
    for k in list(state['answers']):
        if not schema.applicable(k,state['answers']):state['answers'].pop(k)
    return state


def metrics(p,y,labels,profiles=None,bootstrap=100):
    y=np.asarray(y);prediction=p.argmax(1);n=len(y);top3=np.argsort(-p,axis=1,kind='stable')[:,:3]
    correctness=prediction==y;hits=(top3==y[:,None]).any(axis=1);conf=p.max(axis=1);bins=np.minimum((conf*10).astype(int),9)
    reliability=[];ece=0
    for b in range(10):
        m=bins==b
        if m.any():
            a=float(correctness[m].mean());c=float(conf[m].mean());count=int(m.sum());ece+=count/n*abs(a-c)
            reliability.append({'bin':b,'count':count,'accuracy':a,'mean_confidence':c})
    supports=np.bincount(y,minlength=len(labels));recall=recall_score(y,prediction,labels=np.arange(len(labels)),average=None,zero_division=0)
    result={'n':n,'top1':float(correctness.mean()),'top3':float(hits.mean()),
            'macro_f1':float(f1_score(y,prediction,labels=np.arange(len(labels)),average='macro',zero_division=0)),
            'weighted_f1':float(f1_score(y,prediction,labels=np.arange(len(labels)),average='weighted',zero_division=0)),
            'log_loss':float(log_loss(y,p,labels=np.arange(len(labels)))),
            'brier_sum':float(np.mean(np.sum(p*p,axis=1)-2*p[np.arange(n),y]+1)),
            'top_label_ece_10_equal_width':float(ece),'reliability_bins':reliability,
            'per_class':{k:{'support':int(s),'recall':float(r),'insufficient_support':int(s)<30} for k,s,r in zip(labels,supports,recall)},
            'confusion_matrix':confusion_matrix(y,prediction,labels=np.arange(len(labels))).tolist()}
    if bootstrap:
        # Resample entire observed-profile groups, not independent augmented rows.
        _,groups=np.unique(profiles if profiles is not None else np.arange(n),return_inverse=True)
        order=np.argsort(groups,kind='stable')
        members=np.split(order,np.flatnonzero(np.diff(groups[order]))+1)
        rng=np.random.default_rng(20261002);draws=[]
        for _ in range(bootstrap):
            ix=np.concatenate([members[i] for i in rng.integers(0,len(members),len(members))])
            draws.append([correctness[ix].mean(),hits[ix].mean(),f1_score(y[ix],prediction[ix],labels=np.arange(len(labels)),average='macro',zero_division=0)])
        ci=np.quantile(draws,[.025,.975],axis=0)
        result['profile_bootstrap_95ci']={k:ci[:,j].tolist() for j,k in enumerate(['top1','top3','macro_f1'])}
        result['bootstrap_replicates']=bootstrap
    return result


def differential_metrics(p,rows,labels):
    import ast
    ranks=np.argsort(-p,axis=1,kind='stable')[:,:3];overlap=[];mass=[];ndcg=[]
    for pred,row in zip(ranks,rows):
        reference={k:float(v) for k,v in ast.literal_eval(row['DIFFERENTIAL_DIAGNOSIS'])}
        predicted=[labels[i] for i in pred]
        overlap.append(len(set(predicted)&set(reference))/3)
        mass.append(sum(reference.get(k,0) for k in predicted))
        dcg=sum(reference.get(k,0)/np.log2(i+2) for i,k in enumerate(predicted))
        ideal=sum(v/np.log2(i+2) for i,v in enumerate(sorted(reference.values(),reverse=True)[:3]))
        ndcg.append(dcg/ideal if ideal else 0)
    return {'top3_reference_precision':float(np.mean(overlap)),'reference_mass_in_top3':float(np.mean(mass)),
            'ndcg3_reference_scores':float(np.mean(ndcg)), 'note':'Synthetic differential is a secondary reference, not patient risk or the pathology training target'}
