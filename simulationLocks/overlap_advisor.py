"""
@module simulationLocks.overlap_advisor

xsim-5: the parallelization assist (Dustin directive 7) — detect when
a simulation definition parallelizes work that would touch the same
objects. ADVISOR, never enforcer ([[knobs-and-suggestions]]): findings
carry evidence (both branch paths + the shared selector) and
suggestions (serialize | partition | clone-then-merge); nothing is
ever rewritten or auto-applied.

The selector vocabulary is object_locks' — id | name | range |
class-wide — so the advisor's write-set manifest IS the lock manifest
(one analysis, two consumers: request_run_slot locks exactly what the
advisor analyzed). Dynamic/unresolvable refs produce a conservative
"cannot prove disjoint" note rather than silence.

Branch extraction from msim stage JSON lives in advisor_stages.py;
this file is the stage-agnostic disjointness engine.
"""

from typing import Dict, List

from simulationLocks.object_locks import SELECTOR_KINDS, selectors_overlap


def normalize_write_item(item: Dict) -> Dict:
    selector = item.get('selector') or {}
    kind = selector.get('kind', '')
    return {'authority': str(item.get('authority', 'local') or 'local'),
            'className': str(item.get('className', '') or ''),
            'selector': {'kind': kind if kind in SELECTOR_KINDS
                         else 'class-wide',
                         'value': selector.get('value', '')},
            'dynamic': bool(item.get('dynamic'))}


def items_overlap(a: Dict, b: Dict) -> bool:
    if a['className'] != b['className'] \
            or a['authority'] != b['authority']:
        return False
    if a['dynamic'] or b['dynamic']:
        return True     # cannot prove disjoint
    return selectors_overlap(a['selector']['kind'],
                             str(a['selector']['value']),
                             b['selector']['kind'],
                             str(b['selector']['value']))


def analyze_branches(branches: List[Dict]) -> Dict:
    """branches = [{'branch': <path label>, 'writeSet': [items]}] —
    every PARALLEL pair whose write sets are not provably disjoint
    becomes a finding. Returns {'ok', 'findings', 'writeManifest'}
    where writeManifest is the union set (the lock manifest)."""
    normalized = [{'branch': b.get('branch', f'branch-{i}'),
                   'writeSet': [normalize_write_item(w)
                                for w in b.get('writeSet') or []]}
                  for i, b in enumerate(branches)]
    findings: List[Dict] = []
    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            for a in normalized[i]['writeSet']:
                for b in normalized[j]['writeSet']:
                    if not items_overlap(a, b):
                        continue
                    dynamic = a['dynamic'] or b['dynamic']
                    findings.append({
                        'level': 'warning',
                        'kind': 'parallel-write-overlap',
                        'message':
                            (f"parallel branches "
                             f"'{normalized[i]['branch']}' and "
                             f"'{normalized[j]['branch']}' both write "
                             f"{a['className']} — "
                             + ('cannot prove disjoint (dynamic ref)'
                                if dynamic else
                                f"selectors "
                                f"{a['selector']['kind']}="
                                f"{a['selector']['value']} / "
                                f"{b['selector']['kind']}="
                                f"{b['selector']['value']} overlap")),
                        'evidence': {
                            'branchA': normalized[i]['branch'],
                            'branchB': normalized[j]['branch'],
                            'className': a['className'],
                            'selectorA': a['selector'],
                            'selectorB': b['selector'],
                            'dynamic': dynamic},
                        'suggestions': [
                            {'knob': 'stage ordering',
                             'action': 'serialize these branches'},
                            {'knob': 'write partitioning',
                             'action': 'partition by id/range so the '
                                       'sets are provably disjoint'},
                            {'knob': 'clone-then-merge',
                             'action': 'give each branch its own '
                                       'clone and merge after'}]})
                    break   # one finding per branch pair per class
                else:
                    continue
                break
    manifest, seen = [], set()
    for branch in normalized:
        for item in branch['writeSet']:
            key = (item['authority'], item['className'],
                   item['selector']['kind'],
                   str(item['selector']['value']))
            if key not in seen:
                seen.add(key)
                manifest.append({'authority': item['authority'],
                                 'className': item['className'],
                                 'selector': item['selector']})
    return {'ok': not findings, 'findings': findings,
            'writeManifest': manifest,
            'branchCount': len(normalized)}
