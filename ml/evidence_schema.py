"""Canonical DDXPlus contract. Display text never becomes an inference ID."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path

SCHEMA_VERSION = 'ddxplus-en-v2-app1'
KNOWLEDGE = Path(__file__).resolve().parents[1] / 'knowledge'
ORPHAN_PARENTS = {'E_69': 'E_68', 'E_37': 'E_36', 'E_118': 'E_117', 'E_123': 'E_122', 'E_87': 'E_85'}
SAFETY_IDS = {'chest_pain', 'sudden_persistent_chest_pain', 'radiating_chest_pain',
              'chest_pain_with_sweat_sickness_lightheadedness_breathlessness',
              'sudden_face_weakness_24h', 'sudden_arm_weakness_24h', 'sudden_speech_problem_24h'}


class EvidenceError(ValueError):
    def __init__(self, code, field, message):
        super().__init__(message)
        self.code, self.field = code, field


def fail(field, message, code='invalid_evidence'):
    raise EvidenceError(code, field, message)


def empty_state():
    return {'schema_version': SCHEMA_VERSION, 'demographics': {'age': None, 'dataset_sex': 'unknown'},
            'answers': {}, 'skipped_questions': [], 'safety_answers': {}, 'language': 'en',
            'complaint_scope': 'supported'}


class EvidenceSchema:
    def __init__(self, directory=KNOWLEDGE):
        self.directory = Path(directory)
        self.evidences = json.loads((self.directory/'release_evidences.json').read_text(encoding='utf-8'))
        self.conditions = json.loads((self.directory/'release_conditions.json').read_text(encoding='utf-8'))
        self.ids = sorted(self.evidences)
        self.classes = sorted(self.conditions)
        self.hashes = {name: hashlib.sha256((self.directory/name).read_bytes()).hexdigest()
                       for name in ['release_evidences.json', 'release_conditions.json']}
        actual = {k: v['code_question'] for k, v in self.evidences.items() if v['code_question'] not in self.evidences}
        if actual != ORPHAN_PARENTS:
            raise ValueError('Ontology orphan policy mismatch')
        # Engineering applicability review: these five self-contained B questions are independent.
        # This does not invent the missing parents or constitute clinical review.
        self.parents = {k: v['code_question'] for k, v in self.evidences.items()
                        if v['code_question'] in self.evidences and k != v['code_question']}
        self.children = {k: [c for c,p in self.parents.items() if p == k] for k in self.ids}
        self.domains = {k: {str(v): v for v in e['possible-values']} for k,e in self.evidences.items()}

    def applicable(self, key, answers):
        parent = self.parents.get(key)
        return not parent or (answers.get(parent, {}).get('state') == 'present'
                              and answers[parent].get('complete') is True)

    def remove_group(self, state, key):
        out = copy.deepcopy(state)
        for item in [key, *self.children[key]]:
            out['answers'].pop(item, None)
        return out

    def validate(self, payload):
        if not isinstance(payload, dict): fail('body', 'Expected a JSON object')
        allowed = set(empty_state())
        if set(payload)-allowed: fail('body', 'Unknown state fields')
        if payload.get('schema_version') != SCHEMA_VERSION: fail('schema_version', 'Schema version mismatch')
        out = empty_state()
        out.update(copy.deepcopy(payload))
        d = out['demographics']
        if not isinstance(d, dict) or set(d)-{'age', 'dataset_sex'}: fail('demographics','Invalid demographics')
        age = d.get('age')
        if age is not None and (type(age) is not int or not 0 <= age <= 109): fail('demographics.age','Use an integer age 0–109 or unknown')
        sex = d.get('dataset_sex', 'unknown')
        if sex not in ('M', 'F', 'unknown'): fail('demographics.dataset_sex','Use M, F or unknown')
        out['demographics'] = {'age': age, 'dataset_sex': sex}
        if out['language'] not in ('en', 'hi'): fail('language', 'Unsupported language')
        if out['complaint_scope'] not in ('supported', 'unsupported', 'unsure'): fail('complaint_scope','Invalid scope')
        a = out['answers']
        if not isinstance(a, dict) or len(a) > len(self.ids): fail('answers', 'Invalid answers')
        for k, ans in a.items():
            if k not in self.evidences: fail('answers', 'Unknown evidence ID')
            if not isinstance(ans, dict) or set(ans)-{'state','values','complete'}: fail(f'answers.{k}', 'Invalid answer fields')
            st, vals, complete = ans.get('state'), ans.get('values', []), ans.get('complete', True)
            if not isinstance(vals,list) or type(complete) is not bool: fail(f'answers.{k}', 'Invalid values or completion')
            typ = self.evidences[k]['data_type']
            if st == 'unknown':
                if vals: fail(f'answers.{k}', 'Unknown answers cannot contain values')
                a[k] = {'state': st, 'values': [], 'complete': True}
                continue
            if typ == 'B':
                if st not in ('present','absent') or vals or not complete: fail(f'answers.{k}', 'Binary answer must be Present, Absent or Unknown')
            else:
                if st != 'known' or not vals or (typ == 'C' and (len(vals) != 1 or not complete)):
                    fail(f'answers.{k}', 'Complete categorical answer or nonempty multi-choice selection required')
                if len(vals) > (len(self.domains[k]) if typ == 'M' else 1): fail(f'answers.{k}', 'Too many selected values')
                if any(type(v) not in (int,str) or str(v) not in self.domains[k] for v in vals): fail(f'answers.{k}', 'Unknown option')
                # Domains have both integer 0–10 and coded-string options. Booleans are not integers here.
                vals = [self.domains[k][str(v)] for v in vals]
                if len({str(v) for v in vals}) != len(vals): fail(f'answers.{k}', 'Duplicate options')
                default = self.evidences[k]['default_value']
                if typ == 'M' and default in vals and len(vals)>1: fail(f'answers.{k}', 'Default cannot be combined with other values')
                vals = sorted(vals, key=str)
            a[k] = {'state': st, 'values': vals, 'complete': complete}
        for k, ans in a.items():
            if ans['state'] != 'unknown' and not self.applicable(k,a): fail(f'answers.{k}', 'Confirm the parent answer before its dependent question', 'inapplicable_answer')
        skips = out['skipped_questions']
        if not isinstance(skips,list) or any(type(k) is not str or k not in self.evidences for k in skips) or len(set(skips)) != len(skips): fail('skipped_questions','Invalid skipped question IDs')
        if any(a.get(k,{}).get('state','unknown') != 'unknown' for k in skips): fail('skipped_questions','Answered questions cannot also be skipped')
        safety = out['safety_answers']
        if not isinstance(safety,dict) or set(safety)-SAFETY_IDS or any(v not in ('present','absent','unknown') for v in safety.values()): fail('safety_answers', 'Invalid safety answers')
        return out

    def parse_tokens(self, literal):
        try: tokens = ast.literal_eval(literal)
        except (ValueError, SyntaxError, MemoryError, RecursionError): fail('EVIDENCES','Invalid literal list')
        if not isinstance(tokens,list) or len(tokens)>1024 or any(not isinstance(t,str) for t in tokens): fail('EVIDENCES','Invalid evidence list')
        if len(set(tokens)) != len(tokens): fail('EVIDENCES','Duplicate evidence tokens')
        grouped = {}
        for token in tokens:
            k,sep,v = token.partition('_@_')
            if k not in self.evidences: fail('EVIDENCES','Unknown source ID')
            typ = self.evidences[k]['data_type']
            if typ == 'B':
                if sep: fail('EVIDENCES','Binary token has a value')
                grouped[k] = [1]
            else:
                if not sep or v not in self.domains[k]: fail('EVIDENCES','Invalid source option')
                grouped.setdefault(k,[]).append(self.domains[k][v])
        for k,vals in grouped.items():
            e=self.evidences[k]
            if e['data_type']=='C' and len(vals)!=1: fail('EVIDENCES','Multiple categorical values')
            if e['data_type']=='M' and e['default_value'] in vals and len(vals)>1: fail('EVIDENCES','Invalid multi-choice set')
        return tokens, grouped

    def full_state(self, row, grouped=None):
        if grouped is None: _, grouped = self.parse_tokens(row['EVIDENCES'])
        out=empty_state();out['demographics']={'age':int(row['AGE']), 'dataset_sex':row['SEX']}
        for k,e in self.evidences.items():
            if e['data_type']=='B': ans={'state':'present' if k in grouped else 'absent','values':[],'complete':True}
            else: ans={'state':'known','values':grouped.get(k,[e['default_value']]),'complete':True}
            out['answers'][k]=ans
        for k in self.parents:
            if not self.applicable(k,out['answers']): out['answers'].pop(k)
        return out

    def catalogue(self, navigation):
        evidence_regions = navigation['evidence_regions']
        return [{'id':k,'label':e['question_en'],'type':e['data_type'],'history':e['is_antecedent'],
                 'parent':self.parents.get(k), 'regions':evidence_regions.get(k,['general']),
                 'options':[{'value':v,'label':e['value_meaning'].get(str(v),{}).get('en',str(v))} for v in e['possible-values']],
                 'default':e['default_value']} for k,e in sorted(self.evidences.items())]
