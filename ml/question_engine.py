"""Training-only answer-set frequencies and approximate expected entropy reduction."""
import copy
import numpy as np

POLICY_VERSION='training-frequency-batched-ig-v1'
DEFAULT_CAP=7


def entropy(p):
    p=np.clip(p,1e-12,1)
    return -np.sum(p*np.log(p),axis=-1)


class QuestionEngine:
    def __init__(self,schema,encoder,model,frequencies):
        self.schema,self.encoder,self.model,self.frequencies=schema,encoder,model,frequencies

    def candidates(self,state):
        return [k for k in self.schema.ids if k in self.frequencies
                and state['answers'].get(k,{}).get('state','unknown')=='unknown'
                and k not in state['skipped_questions'] and self.schema.applicable(k,state['answers'])]

    def choose(self,state,probabilities=None,cap=True):
        if cap and len(state['skipped_questions'])+sum(a['state']!='unknown' and a['complete'] for a in state['answers'].values())>=DEFAULT_CAP+1:
            return None
        p=probabilities if probabilities is not None else self.model.predict_proba(self.encoder.encode(state)[None])[0]
        candidates=self.candidates(state)
        if not candidates:return None
        # Bound cost with a training-frequency information shortlist, deterministic ties.
        priority=[]
        for k in candidates:
            f=self.frequencies[k];dist=np.array(f['probabilities']);weights=dist@p
            proxy=float(entropy(weights)-np.sum(p*entropy(dist.T)))
            priority.append((-proxy,k))
        shortlist=[k for _,k in sorted(priority)[:16]]
        trials=[];groups=[]
        for k in shortlist:
            f=self.frequencies[k];weights=np.array(f['probabilities'])@p
            start=len(trials)
            for a in f['answers']:
                s=copy.deepcopy(state);s['answers'][k]=a
                trials.append(self.encoder.encode(s))
            groups.append((k,start,len(trials),weights,float(f.get('residual',0))))
        after=self.model.predict_proba(np.array(trials,dtype=np.float32))
        h=float(entropy(p));scores=[]
        for k,start,end,w,residual in groups:
            # Rare joint multi-choice sets have an explicit residual bucket; do not invent sets.
            gain=h-float(np.sum(w*entropy(after[start:end])))-max(0,1-float(w.sum()))*h
            scores.append((-gain,k))
        neg_gain,k=min(scores)
        return {'id':k,'approximate_information_gain':float(-neg_gain),
                'rationale':'This unanswered question may help distinguish the current model matches. You can skip it.',
                'policy_version':POLICY_VERSION}
