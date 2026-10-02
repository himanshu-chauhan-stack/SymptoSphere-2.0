import copy
import numpy as np
import pytest
from ml.evidence_schema import EvidenceError,ORPHAN_PARENTS
from ml.evaluate import masked_state

def binary(value):return {'state':value,'values':[],'complete':True}

def test_three_states_have_different_encodings(schema,encoder,state):
    unknown=encoder.encode(schema.validate(state));state['answers']['E_201']=binary('absent')
    absent=encoder.encode(schema.validate(state));state['answers']['E_201']=binary('present')
    present=encoder.encode(schema.validate(state));j=encoder.masks['E_201'];v=encoder.slots[('E_201','1')]
    assert (unknown[j],unknown[v])==(0,0)
    assert (absent[j],absent[v])==(1,0)
    assert (present[j],present[v])==(1,1)

def test_dependent_zero_is_known_and_parent_is_required(schema,encoder,state):
    key=next(k for k in schema.parents if schema.evidences[k]['data_type']=='C' and 0 in schema.evidences[k]['possible-values'])
    parent=schema.parents[key];state['answers'][key]={'state':'known','values':[0],'complete':True}
    with pytest.raises(EvidenceError,match='parent'):schema.validate(state)
    state['answers'][parent]=binary('present');good=schema.validate(state);x=encoder.encode(good)
    assert x[encoder.slots[(key,'0')]]==x[encoder.masks[key]]==1
    good['answers'][parent]=binary('absent');assert encoder.encode(good)[encoder.masks[key]]==0

def test_multi_choice_requires_complete_and_valid_set(schema,encoder,state):
    key=next(k for k in schema.ids if schema.evidences[k]['data_type']=='M')
    if key in schema.parents:state['answers'][schema.parents[key]]=binary('present')
    default=schema.evidences[key]['default_value'];other=next(v for v in schema.evidences[key]['possible-values'] if v!=default)
    state['answers'][key]={'state':'known','values':[other],'complete':False}
    assert encoder.encode(schema.validate(state))[encoder.masks[key]]==0
    state['answers'][key]['complete']=True
    assert encoder.encode(schema.validate(state))[encoder.masks[key]]==1
    for vals in [[default,other],[other,other],['invented_option']]:
        state['answers'][key]['values']=vals
        with pytest.raises(EvidenceError):schema.validate(state)

@pytest.mark.parametrize('field,value',[('age',True),('age',-1),('age',110),('age',2.2),('dataset_sex','X')])
def test_invalid_demographics(schema,state,field,value):
    state['demographics'][field]=value
    with pytest.raises(EvidenceError):schema.validate(state)

def test_orphans_are_explicit_and_other_parents_stay_enforced(schema,state):
    assert len(ORPHAN_PARENTS)==5
    for k in ORPHAN_PARENTS:state['answers'][k]=binary('present')
    schema.validate(state)

def test_unknown_demographics_distinct_from_age_zero(encoder,state):
    x=encoder.encode(state);assert x[encoder.demo+1]==x[encoder.demo+4]==0
    state['demographics']['age']=0;x=encoder.encode(state);assert x[encoder.demo]==0 and x[encoder.demo+1]==1

def test_full_retention_preserves_dependent_answers(schema,encoder):
    parent=next(iter(schema.parents.values()));child=next(k for k,v in schema.parents.items() if v==parent)
    # Parent intentionally follows child in the source ontology/order.
    token=child if schema.evidences[child]['data_type']=='B' else child+'_@_'+str(schema.evidences[child]['possible-values'][0])
    row={'AGE':35,'SEX':'F','EVIDENCES':repr([token,parent]),'INITIAL_EVIDENCE':parent}
    full=schema.full_state(row);masked=masked_state(schema,full,parent,np.random.default_rng(1),retention=1)
    assert masked['answers']==full['answers']
    np.testing.assert_array_equal(encoder.encode(masked),encoder.encode(full))

def test_malformed_source_literals_are_not_executed(schema):
    for literal in ["__import__('os').system('echo unsafe')", "['E_9999']", "['E_201','E_201']", "['E_201_@_1']"]:
        with pytest.raises(EvidenceError):schema.parse_tokens(literal)

def test_profile_hash_excludes_targets_and_token_order():
    from ml.ddxplus_data import profile_hash
    row={'AGE':30,'SEX':'M','PATHOLOGY':'a'};other={**row,'PATHOLOGY':'b','INITIAL_EVIDENCE':'anything'}
    assert profile_hash(row,['E_1','E_2'])==profile_hash(other,['E_2','E_1'])
