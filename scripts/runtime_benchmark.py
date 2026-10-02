"""Measured local startup, warm endpoint latency and memory. No hosted claims."""
import ctypes
import json
import platform
import time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def memory():
    if platform.system()=='Windows':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(k,ctypes.c_size_t) for k in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
        c=Counters();c.cb=ctypes.sizeof(c);kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=wintypes.HANDLE
        psapi=ctypes.WinDLL('psapi');psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(c),c.cb):raise OSError('Cannot measure process memory')
        return {'working_set_bytes':c.WorkingSetSize,'peak_working_set_bytes':c.PeakWorkingSetSize}
    import resource
    return {'peak_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}

def main():
    start=time.perf_counter()
    from app import app
    from ml.evidence_schema import empty_state
    cold=(time.perf_counter()-start)*1000;assert app.config['MODEL_READY']
    import numpy as np
    client=app.test_client();state=empty_state();state['answers']={k:{'state':v,'values':[],'complete':True} for k,v in [('E_201','present'),('E_91','absent'),('E_97','absent')]}
    report={'environment':platform.platform(),'cold_import_and_model_load_ms':cold,'memory_after_import':memory(),'endpoints':{},'note':'Local Flask test-client wall-clock; model load is fresh-process, OS file cache not cleared. Includes explanations/question selection. Not hosted latency.'}
    for route in ['/api/predict','/api/next-question']:
        assert client.post(route,json=state).status_code==200
        values=[]
        for _ in range(30):
            t=time.perf_counter();response=client.post(route,json=state);assert response.status_code==200;values.append((time.perf_counter()-t)*1000)
        report['endpoints'][route]={'samples':30,'mean_ms':float(np.mean(values)),'p95_ms':float(np.quantile(values,.95)),'min_ms':float(np.min(values))}
    report['memory_after_requests']=memory();out=Path(__file__).resolve().parents[1]/'evaluation/runtime_benchmark.json';out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
