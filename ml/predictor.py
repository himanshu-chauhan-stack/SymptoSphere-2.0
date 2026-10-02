from __future__ import annotations
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits
from .evidence_schema import EvidenceSchema
from .encoding import EvidenceEncoder
from .question_engine import QuestionEngine,POLICY_VERSION
from .explain import explain_answers
from knowledge.safety import safety_check

MODELS=Path(__file__).parent/'models'


class SymptoPredictor:
    """One selected classifier, loaded only from a trusted shipped, hash-checked bundle."""
    def __init__(self,model_dir=MODELS,schema=None):
        self._thread_limit=threadpool_limits(limits=4)
        self.schema=schema or EvidenceSchema();self.encoder=EvidenceEncoder(self.schema)
        directory=Path(model_dir)
        self.metadata=json.loads((directory/'ddxplus_manifest.json').read_text(encoding='utf-8'))
        m=self.metadata
        if m['sklearn_version']!=sklearn.__version__:raise ValueError('Runtime sklearn version mismatch')
        if any(m[k]!=v for k,v in self.encoder.metadata().items()):raise ValueError('Artifact schema mismatch')
        if m['question_policy_version']!=POLICY_VERSION:raise ValueError('Question policy mismatch')
        data=(directory/'ddxplus_bundle.joblib').read_bytes()
        if hashlib.sha256(data).hexdigest()!=m['bundle_sha256']:raise ValueError('Artifact integrity mismatch')
        self.bundle=joblib.load(directory/'ddxplus_bundle.joblib')
        self.model=self.bundle['model'];self.best_model_name=m['selected_model']
        if list(self.model.classes_)!=self.schema.classes or self.model.n_features_in_!=len(self.encoder.features):raise ValueError('Model class or feature mismatch')
        self.questions=QuestionEngine(self.schema,self.encoder,self.model,self.bundle['frequencies'])

    def probabilities(self,state):
        return self.model.predict_proba(self.encoder.encode(state)[None])[0]

    def predict(self,state,explain=True):
        safety=safety_check(state['safety_answers']);a=state['answers']
        known=[k for k,v in a.items() if v['state']!='unknown' and v['complete']]
        present=[k for k in known if a[k]['state']=='present' and not self.schema.evidences[k]['is_antecedent']]
        base={'model_version':self.metadata['model_version'], 'ranked_conditions':[],
              'evidence_count':{'known':len(known),'positive':len(present),
                                'negative':sum(a[k]['state']=='absent' for k in known),'skipped':len(state['skipped_questions'])},
              'safety':safety, 'limitations':[
                  'Educational exploration using synthetic DDXPlus data; limited to 49 conditions, chiefly cough, sore throat and breathing presentations.',
                  'Not a diagnosis, exhaustive emergency check or clinical risk estimate. Conditions outside the dataset may explain your symptoms.',
                  'Sparse answers and unknown demographics can change rankings. Rare conditions have limited evaluation support.'],
              'uncertainty':'limited_information','next_question':None}
        if safety['urgent']:base['status']='urgent_help';return base
        if state['complaint_scope']!='supported':base['status']='unsupported_scope';return base
        if not present:base['status']='insufficient_information';return base
        p=self.probabilities(state);indices=np.argsort(-p,kind='stable')[:3]
        explanations=explain_answers(self.schema,self.encoder,self.model,state,p,indices) if explain else {}
        for rank,i in enumerate(indices,1):
            condition=self.schema.classes[i]
            base['ranked_conditions'].append({'id':condition,'name':condition,'rank':rank,
                'explanation':explanations.get(condition,{}),
                'recommended_specialty':'General clinician / primary care',
                'care_navigation':'Discuss persistent or concerning symptoms with a qualified clinician. They can decide whether a specialist or testing is appropriate.',
                'content_status':'Generic educational guidance; condition-specific clinical summaries not reviewed',
                'reference':{'title':'DDXPlus source and scope','url':'https://doi.org/10.6084/m9.figshare.22687585.v2'},
                'training_support':self.metadata['train_class_support'].get(condition,0)})
        base['status']='ok';base['next_question']=self.questions.choose(state,p,cap=False)
        return base
