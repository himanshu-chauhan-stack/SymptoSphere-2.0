"""The identical encoder is used offline and at inference; unknown != absent."""
import numpy as np
from .evidence_schema import SCHEMA_VERSION

ENCODER_VERSION='values-known-demographics-v1'


class EvidenceEncoder:
    def __init__(self, schema):
        self.schema=schema
        self.features=[];self.slots={};self.masks={}
        for k in schema.ids:
            e=schema.evidences[k]
            for v in ([1] if e['data_type']=='B' else e['possible-values']):
                self.slots[(k,str(v))]=len(self.features);self.features.append(f'{k}={v}')
            self.masks[k]=len(self.features);self.features.append(f'{k}:known')
        self.demo=len(self.features)
        self.features+=['age/109','age:known','sex=M','sex=F','sex:known']

    def encode(self, state):
        x=np.zeros(len(self.features),dtype=np.float32)
        for k,a in state['answers'].items():
            if a['state']=='unknown' or not a['complete'] or not self.schema.applicable(k,state['answers']):continue
            x[self.masks[k]]=1
            if a['state']=='present':x[self.slots[(k,'1')]]=1
            elif a['state']=='known':
                for v in a['values']:x[self.slots[(k,str(v))]]=1
        d=state['demographics'];age=d['age'];sex=d['dataset_sex']
        if age is not None:x[self.demo:self.demo+2]=[age/109,1]
        if sex!='unknown':x[self.demo+2:self.demo+5]=[sex=='M',sex=='F',1]
        return x

    def matrix(self,states):
        return np.asarray([self.encode(s) for s in states],dtype=np.float32)

    def metadata(self):
        return {'schema_version':SCHEMA_VERSION,'encoder_version':ENCODER_VERSION,
                'feature_names':self.features,'ontology_hashes':self.schema.hashes,'classes':self.schema.classes}
