"""Faithful whole-answer ablation, including dependent child groups."""
import numpy as np


def explain_answers(schema,encoder,model,state,probabilities,indices):
    ids=[k for k,a in state['answers'].items() if a['state']!='unknown' and a['complete']]
    if not ids:return {}
    x=encoder.matrix(schema.remove_group(state,k) for k in ids)
    removed=model.predict_proba(x)
    result={}
    for i in indices:
        rows=[{'evidence_id':k,'label':schema.evidences[k]['question_en'],
               'answer':state['answers'][k], 'delta':float(probabilities[i]-removed[j,i]),
               'effect':'increased_match' if probabilities[i]>removed[j,i] else 'reduced_match',
               'removed_group':[k,*schema.children[k]]} for j,k in enumerate(ids)]
        rows=sorted(rows,key=lambda r:abs(r['delta']),reverse=True)
        positive=[r for r in rows if r['delta']>1e-6][:3]
        negative=[r for r in rows if r['delta']< -1e-6][:3]
        result[schema.classes[i]]={'supporting':positive,'contradicting':negative,
                                 'method':'Observed answer removal; model effects, not medical causes'}
    return result
