"""
@module pspp.threshold_windows

The THRESHOLD-SHAPED (asymmetric/banded) ReactionWindow variant the
p.193 graded detail needed and the symmetric center+tolerance shape
could not express (handoff item: 'preferred 1.3-1.52 / 4.0-4.2 +
crack thresholds <1.1 / <3.7 — recorded, not yet modeled' — modeled
HERE).

A ThresholdReactionWindow grades one descriptor through an ORDERED,
CONTIGUOUS, FULL-COVERAGE list of bands, each carrying its own grade
AND its own physical behavior note ('numerous cracks', 'free
potassium-silicate phase') — asymmetry and hard thresholds are just
bands. Bands are half-open [lo, hi); lo=None ⇒ -inf, hi=None ⇒ +inf.

Banded rows COMPLEMENT the symmetric patent-claim rows: where both
exist for one (family, descriptor), the banded row wins in merged
grading (finer cited data beats the binary claim; the symmetric row
stays as the patent-claim record).

Also here: CONDITION-GATE windows — thresholds that open/close
reaction pathways rather than grade quality (p.188 §8.5.3: mild
depolymerization frees Q0 only when the Na-silicate solution has
MR < 1.20; p.196 pins the K routes to the SAME threshold). A rule
names gate windows in condition_windows_json; the pspp-8 stepper
refuses to fire the rule where the gate grades 'failure'.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.network_stepping (condition gates)
  - pspp.pspp_views / pspp.experiment_guidance (merged grading)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.reaction_windows import GRADES


class ThresholdReactionWindow(treeObject):
    """One banded (asymmetric/threshold) window for one descriptor."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('k-ps:SiO2/Al2O3:banded').
        name: str = '',
        # Windows never transfer between families (invariant I5).
        material_family: str = '',
        # The computed descriptor it grades ('SiO2/Al2O3', 'MR'…).
        descriptor: str = '',
        # JSON ordered band list: [{"lo": n|null, "hi": n|null,
        # "grade": "<GRADES>", "note": "..."}] — contiguous half-open
        # [lo, hi) bands covering the whole line.
        bands_json: str = '[]',
        # 'quality' grades a composition; 'condition-gate' opens or
        # closes reaction pathways (failure = closed).
        window_role: str = 'quality',
        behavior_note: str = '',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material_family = material_family
        self.descriptor = descriptor
        self.bands_json = bands_json
        self.window_role = window_role
        self.behavior_note = behavior_note
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes


WINDOW_ROLES = ('quality', 'condition-gate')


def banded_window_dict(row):
    get = (row.get if isinstance(row, dict)
           else lambda k, d='': getattr(row, k, d))
    raw = get('bands_json', '[]') or '[]'
    try:
        bands = raw if isinstance(raw, list) else json.loads(raw)
    except Exception:
        bands = []
    return {
        'name': get('name', ''),
        'materialFamily': get('material_family', ''),
        'descriptor': get('descriptor', ''),
        'bands': bands,
        'windowRole': get('window_role', 'quality'),
        'behaviorNote': get('behavior_note', ''),
        'source': get('source_reference', ''),
    }


def validate_banded_window(window):
    """Bands must be ordered, contiguous, full-coverage (first lo and
    last hi None), with declared grades — so grading is total and no
    value falls silently between bands."""
    w = window if isinstance(window, dict) and 'bands' in window \
        else banded_window_dict(window)
    bands = w['bands']
    if not bands:
        return {'ok': False,
                'refusal': f"window {w['name']!r} has no bands",
                'suggestion': 'enter the cited bands as data on the '
                              'row (bands_json)'}
    if w['windowRole'] not in WINDOW_ROLES:
        return {'ok': False,
                'refusal': f"window {w['name']!r} has unknown role "
                           f"{w['windowRole']!r}",
                'suggestion': f'one of {list(WINDOW_ROLES)}'}
    if bands[0].get('lo') is not None or bands[-1].get('hi') is not None:
        return {'ok': False,
                'refusal': f"window {w['name']!r} bands do not cover "
                           'the whole line',
                'suggestion': 'first band lo=null and last band '
                              'hi=null — out-of-claim regions are '
                              'explicit failure bands, never silent'}
    for i, band in enumerate(bands):
        if band.get('grade') not in GRADES:
            return {'ok': False,
                    'refusal': f"band {i} of {w['name']!r} has grade "
                               f"{band.get('grade')!r}",
                    'suggestion': f'one of {list(GRADES)}'}
        lo, hi = band.get('lo'), band.get('hi')
        if lo is not None and hi is not None and not lo < hi:
            return {'ok': False,
                    'refusal': f"band {i} of {w['name']!r} has "
                               f'lo {lo} >= hi {hi}',
                    'suggestion': 'bands are half-open [lo, hi) — '
                                  'fix the row'}
        if i and bands[i - 1].get('hi') != lo:
            return {'ok': False,
                    'refusal': f"bands {i - 1}/{i} of {w['name']!r} "
                               'are not contiguous',
                    'suggestion': 'each band\'s lo must equal the '
                                  'previous band\'s hi — no gaps, no '
                                  'overlaps'}
    return {'ok': True, 'name': w['name'], 'bandCount': len(bands)}


def grade_value_banded(window, value):
    """Grade one value through one banded window — the verdict carries
    the matched band's OWN physical note (what actually goes wrong
    here), not a window-wide summary."""
    w = window if isinstance(window, dict) and 'bands' in window \
        else banded_window_dict(window)
    valid = validate_banded_window(w)
    if not valid['ok']:
        return valid
    for band in w['bands']:
        lo, hi = band.get('lo'), band.get('hi')
        if (lo is None or value >= lo) and (hi is None or value < hi):
            return {
                'ok': True, 'grade': band['grade'],
                'descriptor': w['descriptor'], 'value': value,
                'band': {'lo': lo, 'hi': hi},
                'behaviorNote': band.get('note', '')
                or w['behaviorNote'],
                'windowRole': w['windowRole'],
                'source': w['source'],
                'windowKind': 'banded',
            }
    # Unreachable when validation passed (full coverage) — honest
    # refusal anyway rather than a silent None.
    return {'ok': False,
            'refusal': f'value {value} matched no band of '
                       f"{w['name']!r}",
            'suggestion': 'fix the row — validate_banded_window '
                          'should have caught this'}


def merged_family_windows(symmetric_windows, banded_windows, family):
    """One family's grading set with banded rows WINNING descriptor
    collisions (finer cited data beats the binary patent claim).
    Returns (winners, superseded_names). Condition-gate windows never
    enter quality grading."""
    from pspp.reaction_windows import window_dict
    banded = [banded_window_dict(w) for w in banded_windows]
    banded = [w for w in banded if w['materialFamily'] == family
              and w['windowRole'] == 'quality']
    symmetric = [window_dict(w) for w in symmetric_windows]
    symmetric = [w for w in symmetric if w['materialFamily'] == family]
    covered = {w['descriptor'] for w in banded}
    superseded = [w['name'] for w in symmetric
                  if w['descriptor'] in covered]
    winners = banded + [w for w in symmetric
                        if w['descriptor'] not in covered]
    return winners, superseded


def grade_composition_merged(symmetric_windows, banded_windows,
                             ratios, material_family):
    """grade_composition with the banded variant merged in: banded
    rows override symmetric rows per descriptor; ungraded descriptors
    stay honestly unjudged; overall = worst graded."""
    from pspp.reaction_windows import grade_value
    winners, superseded = merged_family_windows(
        symmetric_windows, banded_windows, material_family)
    if not winners:
        return {
            'ok': False,
            'refusal': f'no ReactionWindow or ThresholdReactionWindow '
                       f'rows exist for family {material_family!r}',
            'suggestion': 'enter the family\'s windows as cited rows '
                          '— windows from other families do NOT '
                          'transfer',
        }
    graded, unjudged = [], []
    for key, value in sorted(ratios.items()):
        window = next((w for w in winners if w['descriptor'] == key),
                      None)
        if window is None or value is None:
            unjudged.append(key)
            continue
        if 'bands' in window:
            graded.append(grade_value_banded(window, value))
        else:
            verdict = grade_value(window, value)
            if verdict.get('ok'):
                verdict['windowKind'] = 'symmetric'
            graded.append(verdict)
    worst = max((g['grade'] for g in graded if g.get('ok')),
                key=GRADES.index, default=None)
    return {'ok': True, 'overall': worst, 'graded': graded,
            'unjudged': unjudged, 'supersededWindows': superseded,
            'note': 'banded windows override symmetric rows per '
                    'descriptor; unjudged descriptors carry no '
                    'verdict — absence of a window is honest data'}


_P193 = ('Davidovits p.193 (US Patent 4,472,199 graded detail): '
         'preferred bands + crack thresholds')

SEED_THRESHOLD_WINDOWS = [
    {
        'name': 'k-ps:SiO2/Al2O3:banded',
        'material_family': 'k-ps-kaliophilite',
        'descriptor': 'SiO2/Al2O3',
        'window_role': 'quality',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 3.3, 'grade': 'failure',
             'note': 'Outside the claimed range [3.3, 4.5] '
                     '(Table C).'},
            {'lo': 3.3, 'hi': 3.7, 'grade': 'failure',
             'note': 'Inside the patent claim but BELOW the 3.7 '
                     'crack threshold — the solidified polymer shows '
                     'numerous cracks, unusable for molded objects '
                     '(p.193).'},
            {'lo': 3.7, 'hi': 4.0, 'grade': 'acceptable',
             'note': 'Above the crack threshold, below the preferred '
                     'band.'},
            {'lo': 4.0, 'hi': 4.2, 'grade': 'ideal',
             'note': 'Preferred ratio approximately 4.0-4.2 '
                     '(p.193).'},
            {'lo': 4.2, 'hi': 4.5, 'grade': 'acceptable',
             'note': 'Above preferred, inside the claim — '
                     'approaching the free-silicate regime.'},
            {'lo': 4.5, 'hi': None, 'grade': 'failure',
             'note': 'Higher ratios induce a free potassium-silicate '
                     'phase whose migration disturbs physical and '
                     'mechanical properties (p.193).'},
        ]),
        'behavior_note': 'Asymmetric: the crack threshold sits 0.4 '
                         'below the preferred band; the free-silicate '
                         'failure starts right at the claim ceiling.',
        'source_reference': _P193,
    },
    {
        'name': 'k-ps:M2O/Al2O3:banded',
        'material_family': 'k-ps-kaliophilite',
        'descriptor': 'M2O/Al2O3',
        'window_role': 'quality',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 0.9, 'grade': 'failure',
             'note': 'Outside the claimed range [0.9, 1.60] '
                     '(Table C).'},
            {'lo': 0.9, 'hi': 1.1, 'grade': 'failure',
             'note': 'Inside the claim but BELOW the 1.1 crack '
                     'threshold — numerous cracks (p.193).'},
            {'lo': 1.1, 'hi': 1.3, 'grade': 'acceptable',
             'note': 'Above the crack threshold, below the preferred '
                     'band.'},
            {'lo': 1.3, 'hi': 1.52, 'grade': 'ideal',
             'note': 'Preferred K2O/Al2O3 approximately 1.3-1.52 '
                     '(p.193).'},
            {'lo': 1.52, 'hi': 1.6, 'grade': 'acceptable',
             'note': 'Above preferred, inside the claim.'},
            {'lo': 1.6, 'hi': None, 'grade': 'failure',
             'note': 'Outside the claimed range (Table C).'},
        ]),
        'behavior_note': 'Asymmetric: crack threshold 0.2 below the '
                         'preferred band; no graded detail above the '
                         'claim ceiling in source.',
        'source_reference': _P193,
    },
    {
        # The p.188/p.196 pathway gate — a THRESHOLD, not a quality
        # grade: it opens/closes the Q0-consuming routes.
        'name': 'na-silicate:mr-q0-depolymerization',
        'material_family': 'geopolymer',
        'descriptor': 'MR',
        'window_role': 'condition-gate',
        'bands_json': json.dumps([
            {'lo': None, 'hi': 1.20, 'grade': 'ideal',
             'note': 'Mild depolymerization of oligo-siloxonates '
                     'Q1/Q2 frees monomeric ortho-siloxonate Q0 '
                     '(p.188 §8.5.3) — the phillipsite (Na) and '
                     'leucite (K) routes are OPEN.'},
            {'lo': 1.20, 'hi': None, 'grade': 'failure',
             'note': 'At MR >= 1.20 the solution does not free Q0 — '
                     'the Q0-consuming routes are CLOSED (p.188; '
                     'p.196 pins the K leucite route to the same '
                     'threshold).'},
        ]),
        'behavior_note': 'Gate semantics: failure = pathway closed; '
                         'anything else = open. Consumed by '
                         'ReactionRule.condition_windows_json.',
        'source_reference': 'Davidovits p.188 §8.5.3 + p.196 §8.6.2',
    },
]

for _row in SEED_THRESHOLD_WINDOWS:
    _row.setdefault('provenance_id',
                    'pspp-8 threshold-window transcription 2026-07-19')
