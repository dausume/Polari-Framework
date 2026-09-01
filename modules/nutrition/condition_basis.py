"""
@cross-cutting
@module nutrition.condition_basis
@tags @xc:bindings

mpb-2 — stated-condition comfort steering as data (Dustin,
ratified 2026-09-01 verbatim: "we should not be doing diagnosis in
any way, what we can say is 'try to make meals that do not make
this condition worse'"):

  StatedCondition     one person's OWN declaration ("I have
                      reflux") — stated, never inferred, never
                      diagnosed here. The row exists so meals can
                      be steered AWAY from that condition's known
                      aggravators; nothing more.
  ConditionSteering   one condition → the EXISTING evidence rows
                      (nmp-2 tolerance substances) that count as
                      its aggravators, plus plain-language
                      guidance and the citation the mapping rests
                      on. Rows, not code — new conditions are new
                      rows.

THE POSTURE (rides every payload): steering only — "try to make
meals that do not make this condition worse". No diagnosis, no
treatment, no magnitude claims (fsp D6); a clinician's numbers
always win (PersonThreshold overrides carry them).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.condition_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-2
"""

from objectTreeDecorators import treeObject, treeObjectInit

POSTURE = ('stated by you, never diagnosed here; we only steer '
           'toward meals that avoid known aggravators of the '
           'condition you named — comfort steering, not treatment '
           'or medical advice; your clinician\'s numbers always '
           'win')

_PROV = ('mpb-2 (MEAL_PLANNING_APP_PLAN §3b, ratified 2026-09-01); '
         'aggravator mappings ride the nmp-2 cited tolerance rows')


class StatedCondition(treeObject):
    """One person's own condition declaration."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-alex-reflux').
        name: str = '',
        person_name: str = '',
        # ConditionSteering.condition this refers to.
        condition: str = '',
        # the person's own words ('GERD diagnosed by my doctor',
        # 'heartburn after big meals').
        stated_reason: str = '',
        # ISO date declared.
        declared_date: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.condition = condition
        self.stated_reason = stated_reason
        self.declared_date = declared_date
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ConditionSteering(treeObject):
    """One condition's aggravator mapping — data, extendable."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case condition key ('reflux').
        condition: str = '',
        name: str = '',
        display_name: str = '',
        # JSON list of nmp-2 tolerance SUBSTANCES that count as
        # aggravators for this condition (evaluation rides the
        # existing cited rows; substances the rollup cannot
        # compute are reported as data gaps, never guessed).
        aggravator_substances_json: str = '[]',
        # plain-language do-not-worsen guidance.
        guidance: str = '',
        citation: str = '',
        # CONFIDENCE grades follow the tolerance table's.
        confidence: str = 'low',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.condition = condition
        self.name = name
        self.display_name = display_name
        self.aggravator_substances_json = aggravator_substances_json
        self.guidance = guidance
        self.citation = citation
        self.confidence = confidence
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


def _steer(condition, display, substances, guidance, citation,
           confidence='low', notes=''):
    import json as _json
    return {'condition': condition, 'name': f'steer-{condition}',
            'display_name': display,
            'aggravator_substances_json': _json.dumps(substances),
            'guidance': guidance, 'citation': citation,
            'confidence': confidence, 'is_prior': True,
            'provenance_id': _PROV, 'notes': notes}


#: The starter steering vocabulary — every substance here is an
#: EXISTING nmp-2 tolerance row; adding a condition = adding a row.
SEED_CONDITION_STEERINGS = [
    _steer('reflux', 'Reflux / heartburn (stated)',
           ['meal-acidity', 'meal-fat-load',
            'reflux-trigger-categories'],
           'prefer meals with a lower high-acid mass share, and '
           'avoid the high-fat x large-meal combination; the '
           'trigger categories (carbonation, caffeine, mint, '
           'chocolate) are noted when present',
           'decision-9 reflux rows (dietary-trigger surveys, '
           'heterogeneous evidence)', 'low'),
    _steer('sodium-sensitive', 'Sodium-sensitive (stated)',
           ['sodium'],
           'prefer meals that keep the day comfortably under the '
           'sodium CDRR; single very salty meals are flagged',
           'NASEM 2019 sodium CDRR', 'ul-grade'),
    _steer('glycemic-sensitive', 'Glycemic-sensitive (stated)',
           ['glycemic-load'],
           'prefer meals under the published high-GL convention; '
           'spikes are flagged per meal',
           'Atkinson 2008 GI/GL tables (GL>20 = the published '
           'high convention)', 'moderate',
           notes='diabetes MANAGEMENT stays out of scope — this '
                 'is spike-avoidance steering only, per the '
                 'ratified no-diagnosis boundary'),
    _steer('fodmap-sensitive', 'FODMAP-sensitive (stated)',
           ['fructans', 'lactose', 'sorbitol', 'xylitol'],
           'prefer meals under the published low-FODMAP '
           'per-serve cutoffs where we can compute them; the '
           'ones we cannot compute from FDC data are named as '
           'gaps, never guessed',
           'Varney et al. 2017 published cutoffs', 'low'),
]

#: A demo declaration so the pages exercise the surface.
SEED_STATED_CONDITIONS = [
    {'name': 'demo-alex-reflux', 'person_name': 'demo-alex',
     'condition': 'reflux',
     'stated_reason': 'demo row — heartburn after large meals',
     'declared_date': '2026-09-01', 'is_prior': True,
     'provenance_id': _PROV,
     'notes': 'demo — replace with real declarations'},
]
