"""
@module pspp.reaction_windows

Reaction WINDOWS, not magic ratios (Ch.8 convergence): the book's
composition ranges are empirical regions where geopolymerization
proceeds properly — graded, not pass/fail. A ReactionWindow row grades
one computed descriptor (pspp.composition_math derives it) as
ideal / acceptable / marginal / failure around a center with widening
tolerances.

NO windows are seeded yet: the Ch.8 numeric ranges have not been
photographed — hardcoding remembered values would violate invariant
I5. The machinery ships now; the windows arrive as DATA rows with
citations (like DigitizedDataset).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - future pspp-4 process admissibility + pspp-6 slice gates
"""

from objectTreeDecorators import treeObject, treeObjectInit

GRADES = ('ideal', 'acceptable', 'marginal', 'failure')


class ReactionWindow(treeObject):
    """One empirical composition window for one derived descriptor."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('mk-geopolymer:SiO2/Al2O3').
        name: str = '',
        # The material family / system the window was established for
        # — windows do NOT transfer between families (invariant I5).
        material_family: str = '',
        # The computed descriptor it grades ('SiO2/Al2O3', 'H2O/M2O',
        # 'Si/Al'… — pspp.composition_math.oxide_ratios keys).
        descriptor: str = '',
        center: float = 0.0,
        # Widening half-tolerances around center per grade.
        ideal_tolerance: float = 0.0,
        acceptable_tolerance: float = 0.0,
        marginal_tolerance: float = 0.0,
        # What physically goes wrong outside ('too little alkali —
        # incomplete dissolution') — the evidence half of a verdict.
        behavior_note: str = '',
        source_reference: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.material_family = material_family
        self.descriptor = descriptor
        self.center = center
        self.ideal_tolerance = ideal_tolerance
        self.acceptable_tolerance = acceptable_tolerance
        self.marginal_tolerance = marginal_tolerance
        self.behavior_note = behavior_note
        self.source_reference = source_reference
        self.provenance_id = provenance_id
        self.notes = notes


def window_dict(row):
    get = (row.get if isinstance(row, dict)
           else lambda k, d='': getattr(row, k, d))
    return {
        'name': get('name', ''),
        'materialFamily': get('material_family', ''),
        'descriptor': get('descriptor', ''),
        'center': get('center', 0.0),
        'tolerances': {
            'ideal': get('ideal_tolerance', 0.0),
            'acceptable': get('acceptable_tolerance', 0.0),
            'marginal': get('marginal_tolerance', 0.0),
        },
        'behaviorNote': get('behavior_note', ''),
        'source': get('source_reference', ''),
    }


def grade_value(window, value):
    """Grade one descriptor value against one window — graded verdict
    with distance and the window's physical behavior note."""
    w = window if isinstance(window, dict) and 'tolerances' in window \
        else window_dict(window)
    tol = w['tolerances']
    if not (0 < tol['ideal'] <= tol['acceptable'] <= tol['marginal']):
        return {'ok': False,
                'refusal': f"window {w['name']!r} has non-widening "
                           f'tolerances {tol}',
                'suggestion': 'fix the ReactionWindow row: '
                              '0 < ideal <= acceptable <= marginal'}
    distance = abs(value - w['center'])
    if distance <= tol['ideal']:
        grade = 'ideal'
    elif distance <= tol['acceptable']:
        grade = 'acceptable'
    elif distance <= tol['marginal']:
        grade = 'marginal'
    else:
        grade = 'failure'
    return {
        'ok': True, 'grade': grade,
        'descriptor': w['descriptor'], 'value': value,
        'center': w['center'], 'distance': distance,
        'behaviorNote': w['behaviorNote'],
        'source': w['source'],
    }


def grade_composition(windows, ratios, material_family):
    """Grade a whole derived-ratio set against one family's windows.
    Descriptors with NO window are reported unjudged (honest absence
    — never assumed fine, never assumed failing); the overall grade
    is the worst graded descriptor."""
    family = [window_dict(w) for w in windows]
    family = [w for w in family
              if w['materialFamily'] == material_family]
    if not family:
        return {
            'ok': False,
            'refusal': f'no ReactionWindow rows exist for family '
                       f'{material_family!r}',
            'suggestion': 'enter the family\'s windows as '
                          'ReactionWindow rows with citations (Ch.8 '
                          'ranges once photographed) — windows from '
                          'other families do NOT transfer',
        }
    graded, unjudged = [], []
    for key, value in sorted(ratios.items()):
        window = next((w for w in family if w['descriptor'] == key),
                      None)
        if window is None or value is None:
            unjudged.append(key)
            continue
        graded.append(grade_value(window, value))
    worst = max((g['grade'] for g in graded if g['ok']),
                key=GRADES.index, default=None)
    return {'ok': True, 'overall': worst, 'graded': graded,
            'unjudged': unjudged,
            'note': 'unjudged descriptors carry no verdict — absence '
                    'of a window is honest data'}
