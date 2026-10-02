"""Controlled local phrase matching. Suggestions require explicit user confirmation."""
import re
from .evidence_schema import EvidenceError

ALIASES={
    'E_201':['cough','coughing'], 'E_91':['fever','feverish'], 'E_97':['sore throat'],
    'E_66':['shortness of breath','difficulty breathing','breathless'],
    'E_148':['nausea','nauseous'], 'E_94':['chills','shivers'],
    'E_181':['runny nose','nasal congestion','blocked nose'], 'E_214':['wheezing','wheeze'],
    'E_51':['diarrhea','diarrhoea'], 'E_155':['palpitations','racing heart'],
    'E_14':['chest pain at rest'], 'E_89':['fatigue','non-restful sleep'],
    'E_144':['muscle aches','muscle pain'], 'E_211':['repeated vomiting'],
    'E_129':['skin rash','rash'], 'E_151':['swelling']
}


def extract_suggestions(text,schema):
    if type(text) is not str or len(text)>2000:raise EvidenceError('invalid_text','text','Enter at most 2,000 characters')
    found={};ambiguous=[]
    for clause in re.finditer(r'[^.!?;\n]+',text):
        content=clause.group();lower=content.lower()
        # Subjects other than the speaker, hypothetical/history/double-negative language remain unconfirmed.
        uncertain=bool(re.search(r'\b(maybe|perhaps|might|not sure|unsure|if|used to|history of|not without|not no|mother|father|friend|child|daughter|son|he|she|they)\b',lower))
        for k,phrases in ALIASES.items():
            if k not in schema.evidences or schema.evidences[k]['data_type']!='B':continue
            for phrase in phrases:
                for m in re.finditer(r'\b'+re.escape(phrase)+r'\b',lower):
                    before=lower[:m.start()]
                    # Scope a negator to the local clause; 'but' starts a new polarity segment.
                    before=before.split(' but ')[-1]
                    neg=bool(re.search(r'\b(no|not|without|deny|denies|don\W?t|do not)\b',before))
                    state='unknown' if uncertain else 'absent' if neg else 'present'
                    span=[clause.start()+m.start(),clause.start()+m.end()]
                    found.setdefault(k,[]).append({'state':state,'span':span,'phrase':text[span[0]:span[1]]})
    suggestions=[]
    for k,hits in found.items():
        states={h['state'] for h in hits}
        state=states.pop() if len(states)==1 else 'unknown'
        suggestions.append({'id':k,'label':schema.evidences[k]['question_en'],'suggested_state':state,'matches':hits})
    return {'suggestions':suggestions,'requires_confirmation':True,'method':'versioned local allowlist and exact text spans',
            'unmatched_text_policy':'Not interpreted. Use search or mark the complaint unsupported; no model evidence added.',
            'limitations':'English phrases only; limited negation and context handling. Check each suggestion before confirming.'}
