"""
@cross-cutting
@module scoring.evidence
@tags @xc:bindings

MediaEvidence + EvidencePolicy (scr-5, cited by scr-9..14) — proof is
DATA with a GRADE, and what a grade is worth is a SETTING.

MediaEvidence: one citable proof item (video, transcript, official
record, article…) with a quote/span, capture date, provenance and an
evidence_grade. Assertions, promises, rulings all cite these rows.

EvidencePolicy: the graded vocabulary as an editable row (the
AgreementPolicy idiom) — grade → weight, including the weight of
citing NOTHING ('unevidenced'), so how much proof matters is a policy
decision the user can see and change, never a constant buried in code.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.policy_scoring (assertion strength × evidence weight)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: MediaEvidence.kind vocabulary.
EVIDENCE_KINDS = ('video', 'transcript', 'official-record', 'article',
                  'social-post', 'dataset', 'document')

#: evidence_grade vocabulary (weights live on EvidencePolicy rows).
EVIDENCE_GRADES = ('primary-recording', 'official-record',
                   'contemporaneous-report', 'secondhand')


class MediaEvidence(treeObject):
    """One citable proof item."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('evidence-fair-wage-hearing').
        name: str = '',
        display_name: str = '',
        # EVIDENCE_KINDS entry.
        kind: str = 'document',
        url: str = '',
        # Optional objectRef to a stored file/object (JSON).
        file_ref_json: str = '',
        # The cited passage itself.
        quote: str = '',
        # Optional span into the source (JSON {'start','end'}).
        span_json: str = '',
        # ISO date the evidence was captured/archived.
        captured_date: str = '',
        # EVIDENCE_GRADES entry — weight comes from EvidencePolicy.
        evidence_grade: str = 'secondhand',
        # Contributor name (scoring.contributors).
        submitted_by: str = '',
        # ScoreSubject name (kind 'media-outlet') that PUBLISHED this
        # item — ties every cited article to an accountable outlet
        # (scr-15); '' = not outlet-published (official records…).
        outlet_name: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.kind = kind
        self.url = url
        self.file_ref_json = file_ref_json
        self.quote = quote
        self.span_json = span_json
        self.captured_date = captured_date
        self.evidence_grade = evidence_grade
        self.submitted_by = submitted_by
        self.outlet_name = outlet_name
        self.provenance_id = provenance_id
        self.notes = notes


class EvidencePolicy(treeObject):
    """Editable grade → weight vocabulary (what counts as proof)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Ordered JSON list of {'grade', 'weight'} (0-1). The
        # 'unevidenced' entry is the weight of citing nothing.
        grade_weights_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.grade_weights_json = grade_weights_json
        self.notes = notes


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
