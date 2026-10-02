import json
from pathlib import Path

RULES=json.loads((Path(__file__).parent/'safety_rules.json').read_text(encoding='utf-8'))


def safety_check(answers):
    matched=[r for r in RULES['rules'] if any(answers.get(k)=='present' for k in r['any'])]
    return {'urgent':bool(matched),'rule_ids':[r['id'] for r in matched],
            'sources':sorted({r['source'] for r in matched}),
            'message':('Seek urgent medical help now. Contact local emergency services. Do not wait for this tool or drive yourself.' if matched else
                       'This limited check cannot establish that you are safe. Seek medical care for severe, new or worsening symptoms.'),
            'assessment':'urgent_help' if matched else 'not_a_clearance',
            'unknown_count':sum(answers.get(k,'unknown')=='unknown' for r in RULES['rules'] for k in r['any']),
            'clinical_review_status':RULES['clinical_review_status']}
