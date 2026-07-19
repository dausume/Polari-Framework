"""
@module pspp.reaction_windows

Reaction WINDOWS, not magic ratios (Ch.8 convergence): the book's
composition ranges are empirical regions where geopolymerization
proceeds properly — graded, not pass/fail. A ReactionWindow row grades
one computed descriptor (pspp.composition_math derives it) as
ideal / acceptable / marginal / failure around a center with widening
tolerances.

The first REAL windows arrived 2026-07-18 with the pp.191-192 patent
pages (US 4,349,386 Table A; US 4,472,199 Table C): the patents claim
BINARY ranges, so those seeds set all three tolerances to the range
half-width — 'ideal' there means 'inside the claimed range', and
finer grading honestly waits for finer data (the partially-visible
"preferably…" text on p.191 was cut off in the photo).

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


def _range_window(name, family, descriptor, lo, hi, note, source):
    """A patent-claimed BINARY range as a window row: center = range
    midpoint, every tolerance = half-width ('ideal' == inside the
    claimed range; the source grades no finer)."""
    center = (lo + hi) / 2.0
    half = (hi - lo) / 2.0
    return {
        'name': name, 'material_family': family,
        'descriptor': descriptor, 'center': center,
        'ideal_tolerance': half, 'acceptable_tolerance': half,
        'marginal_tolerance': half,
        'behavior_note': f'{note} Patent claims the binary range '
                         f'[{lo}, {hi}] — inside grades ideal, '
                         'outside failure; no finer bands in source.',
        'source_reference': source,
        'provenance_id': 'pspp patent-window transcription 2026-07-18',
    }


_TABLE_A = ('Davidovits p.192 Table A (French appl. 79.22041 / US '
            'Patent 4,349,386): (Na,K)-PSS reactant mixture')
_TABLE_C = ('Davidovits p.192 Table C (US Patent 4,472,199): K-PS '
            'kaliophilite-related reactant mixture')

SEED_REACTION_WINDOWS = [
    _range_window('na-k-pss:M2O/SiO2', 'na-k-pss', 'M2O/SiO2',
                  0.20, 0.28,
                  'Alkali-to-silica of the (Na,K)-PSS mix.', _TABLE_A),
    _range_window('na-k-pss:SiO2/Al2O3', 'na-k-pss', 'SiO2/Al2O3',
                  3.5, 4.5,
                  'Deliberately ABOVE the stoichiometric 2 of the '
                  'product (p.191: reactant ratios higher than '
                  'stoichiometric).', _TABLE_A),
    _range_window('na-k-pss:H2O/M2O', 'na-k-pss', 'H2O/M2O',
                  15.0, 17.5,
                  'Water-to-alkali of the (Na,K)-PSS mix.', _TABLE_A),
    _range_window('na-k-pss:M2O/Al2O3', 'na-k-pss', 'M2O/Al2O3',
                  0.8, 1.20,
                  'Alkali-to-alumina of the (Na,K)-PSS mix.',
                  _TABLE_A),
    _range_window('k-ps:M2O/SiO2', 'k-ps-kaliophilite', 'M2O/SiO2',
                  0.25, 0.48,
                  'K2O/SiO2 of the kaliophilite-related K-PS mix '
                  '(K-only: M2O = K2O).', _TABLE_C),
    _range_window('k-ps:SiO2/Al2O3', 'k-ps-kaliophilite',
                  'SiO2/Al2O3', 3.3, 4.5,
                  'Silica-to-alumina of the K-PS mix. p.193 GRADED '
                  'detail: preferably ~4.0-4.2; BELOW 3.7 the '
                  'solidified polymer has numerous cracks (unusable '
                  'for molded objects); higher ratios induce a free '
                  'potassium-silicate phase + migration that disturbs '
                  'physical/mechanical properties. (Asymmetric bands '
                  'MODELED in the ThresholdReactionWindow row '
                  "'k-ps:SiO2/Al2O3:banded' — it supersedes this row "
                  'in merged grading.)', _TABLE_C),
    _range_window('k-ps:H2O/Al2O3', 'k-ps-kaliophilite', 'H2O/Al2O3',
                  10.0, 25.0,
                  'Water-to-alumina of the K-PS mix.', _TABLE_C),
    _range_window('k-ps:M2O/Al2O3', 'k-ps-kaliophilite', 'M2O/Al2O3',
                  0.9, 1.60,
                  'K2O/Al2O3 of the K-PS mix (p.193 Table C cont.). '
                  'GRADED detail: preferably ~1.3-1.52; BELOW 1.1 '
                  'numerous cracks. (Asymmetric bands MODELED in '
                  "'k-ps:M2O/Al2O3:banded', which supersedes this "
                  'row in merged grading.)', _TABLE_C),
]


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
