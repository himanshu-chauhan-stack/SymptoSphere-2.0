import json
from pathlib import Path
import numpy as np
import pytest
from ml.predictor import SymptoPredictor,MODELS
from ml.evidence_schema import empty_state

def test_reported_answer_effects_are_actual_recalculations():
    service=SymptoPredictor();state=empty_state();state['answers']={k:{'state':v,'values':[],'complete':True} for k,v in [('E_201','present'),('E_91','absent'),('E_53','present')]}
    state['answers']['E_56']={'state':'known','values':[0],'complete':True};state=service.schema.validate(state)
    p=service.probabilities(state);result=service.predict(state);seen=0
    for condition in result['ranked_conditions']:
        index=service.schema.classes.index(condition['id'])
        for group,sign in [('supporting',1),('contradicting',-1)]:
            for row in condition['explanation'][group]:
                removed=service.schema.remove_group(state,row['evidence_id']);actual=p[index]-service.probabilities(removed)[index]
                assert row['delta']==pytest.approx(actual,abs=1e-10) and sign*actual>0;seen+=1
                if row['evidence_id']=='E_53':assert 'E_56' not in removed['answers']
    assert seen>0

def test_non_ascii_classes_and_metadata_are_preserved_utf8():
    service=SymptoPredictor();manifest=json.loads((MODELS/'ddxplus_manifest.json').read_text(encoding='utf-8'))
    assert manifest==service.metadata and 'Guillain-Barré syndrome' in manifest['classes']
    assert len(manifest['feature_names'])==1200 and len(manifest['classes'])==49
    assert manifest['calibration_policy']=='rank_only'

def test_batched_and_one_row_inference_agree():
    service=SymptoPredictor();a=empty_state();b=empty_state();b['answers']['E_201']={'state':'present','values':[],'complete':True}
    batched=service.model.predict_proba(service.encoder.matrix([a,b]))
    np.testing.assert_allclose(batched,np.array([service.probabilities(a),service.probabilities(b)]),atol=1e-12)

def test_no_target_differential_anatomy_or_text_features():
    names=SymptoPredictor().encoder.features
    assert not any(any(token in name.lower() for token in ['pathology','differential','anatomy','fma','text']) for name in names)
