"""@module scoring.objects.evidence._shared — what the evidence row classes share (constants, seeds, helpers); split from evidence_basis.py (sap-2c)."""
import json

EVIDENCE_KINDS = ('video', 'transcript', 'official-record', 'article',
                  'social-post', 'dataset', 'document')
EVIDENCE_GRADES = ('primary-recording', 'official-record',
                   'contemporaneous-report', 'secondhand')
def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)
def _policy(manager, policy_name):
    rows = _rows(manager, 'EvidencePolicy')
    wanted = policy_name or 'default-evidence'
    row = next((r for r in rows
                if getattr(r, 'name', '') == wanted), None)
    if row is None and rows:
        row = rows[0]
    return row
def grade_weights(manager, policy_name=''):
    """{grade: weight} off the named (or default) policy row."""
    row = _policy(manager, policy_name)
    if row is None:
        return {}, ''
    try:
        entries = json.loads(
            getattr(row, 'grade_weights_json', '') or '[]')
    except Exception:
        entries = []
    return ({e.get('grade', ''): float(e.get('weight', 0))
             for e in entries},
            getattr(row, 'name', ''))
def evidence_weight(manager, evidence_names, policy_name=''):
    """The weight an assertion earns from its cited evidence: the
    STRONGEST cited item sets it (more evidence never hurts, weaker
    extras never dilute). Citing nothing = the policy's 'unevidenced'
    weight, labeled. Dangling names surface, never silently ignored.

    Returns (weight, detail)."""
    weights, policy = grade_weights(manager, policy_name)
    if not weights:
        return 1.0, {'policy': None,
                     'note': 'no EvidencePolicy rows — evidence '
                             'weighting inactive (weight 1.0)'}
    by_name = {getattr(e, 'name', ''): e
               for e in _rows(manager, 'MediaEvidence')}
    items, dangling = [], []
    for name in evidence_names or []:
        row = by_name.get(name)
        if row is None:
            dangling.append(name)
            continue
        grade = getattr(row, 'evidence_grade', 'secondhand')
        items.append({'evidence': name, 'grade': grade,
                      'weight': weights.get(grade, 0.0),
                      'quote': getattr(row, 'quote', ''),
                      'url': getattr(row, 'url', '')})
    if not items:
        weight = weights.get('unevidenced', 0.0)
        return weight, {'policy': policy, 'items': [],
                        'dangling': dangling,
                        'grade': 'unevidenced', 'weight': weight}
    best = max(items, key=lambda i: i['weight'])
    return best['weight'], {'policy': policy, 'items': items,
                            'dangling': dangling,
                            'grade': best['grade'],
                            'weight': best['weight']}
SEED_EVIDENCE_POLICIES = [{
    'name': 'default-evidence',
    'display_name': 'Default evidence grading',
    'description': 'What each grade of proof is worth when weighting '
                   'assertions (scr-9 vocabulary: primary-recording > '
                   'official-record > contemporaneous-report > '
                   "secondhand). 'unevidenced' is the weight of citing "
                   'nothing. Edit this row to recalibrate every '
                   'assertion-weighted score.',
    'grade_weights_json': json.dumps([
        {'grade': 'primary-recording', 'weight': 1.0},
        {'grade': 'official-record', 'weight': 0.9},
        {'grade': 'contemporaneous-report', 'weight': 0.6},
        {'grade': 'secondhand', 'weight': 0.3},
        {'grade': 'unevidenced', 'weight': 0.1},
    ]),
}]
