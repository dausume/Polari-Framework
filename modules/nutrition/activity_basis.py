"""
@cross-cutting
@module nutrition.activity_basis
@tags @xc:bindings

nmp-5 — activity as data: ActivityDefinition rows for a CURATED
common subset of the 2024 Adult Compendium (real codes, values
VERBATIM from vendor/compendium_2024_adult_mets.csv at import — the
full 1,111-activity catalog stays searchable through the vendor CSV
and any activity can be materialized on demand; seeding all 1,111
as DB rows would be boot weight nothing needs yet). ActivityLog =
one logged session with first-class TIMING (decision 14 / nmp-5b).

Intensity bands by the Compendium MET cutoffs: light < 3.0,
moderate 3.0-5.9, vigorous >= 6.0.

Attribution (required): Herrmann SD et al., 2024 Adult Compendium
of Physical Activities, pacompendium.com — values unaltered.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.activity_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-5
"""

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.vendor_data import compendium_mets

INTENSITY_BANDS = ('light', 'moderate', 'vigorous')
COMPENDIUM_ATTRIBUTION = ('Herrmann SD et al., 2024 Adult Compendium '
                          'of Physical Activities (pacompendium.com); '
                          'values unaltered')


def intensity_band(met):
    """Compendium MET cutoffs: <3 light, 3-5.9 moderate, >=6 vigorous."""
    return ('light' if met < 3.0
            else 'moderate' if met < 6.0 else 'vigorous')


class ActivityDefinition(treeObject):
    """One Compendium activity (code + MET, verbatim)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('walking-25mph-level').
        name: str = '',
        display_name: str = '',
        # the Compendium activity code — the real pin.
        activity_code: str = '',
        met_value: float = 0.0,
        category: str = '',
        # INTENSITY_BANDS entry, derived from the MET cutoffs.
        intensity: str = 'moderate',
        source: str = COMPENDIUM_ATTRIBUTION,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.activity_code = activity_code
        self.met_value = met_value
        self.category = category
        self.intensity = intensity
        self.source = source
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ActivityLog(treeObject):
    """One logged activity session, with timing (decision 14)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('alex-2026-08-20-run').
        name: str = '',
        person_name: str = '',
        # a seeded ActivityDefinition name OR a raw Compendium code
        # (the analysis resolves either; code wins when both set).
        activity_name: str = '',
        activity_code: str = '',
        duration_min: float = 0.0,
        # nmp-5b: first-class timing — ISO date + start clock time.
        date: str = '',
        start_hhmm: str = '',
        # ties a log onto a plan day for the timeline view (0 = use
        # the date against the plan's start_date).
        day_index: int = 0,
        # the perceived-intensity knob: scales the MET +-30% (a felt
        # correction, labeled in results when != 1).
        perceived_intensity_factor: float = 1.0,
        # honest flag: was this session started without eating
        # beforehand (the fasted-exercise page uses it).
        fasted: bool = False,
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.activity_name = activity_name
        self.activity_code = activity_code
        self.duration_min = duration_min
        self.date = date
        self.start_hhmm = start_hhmm
        self.day_index = day_index
        self.perceived_intensity_factor = perceived_intensity_factor
        self.fasted = fasted
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# curated common subset — (seed name, Compendium code). MET/category
# come VERBATIM from the vendored CSV at import; a bad code fails
# loudly at import (never a silently wrong MET).
_CURATED = [
    ('walking-25mph-level', '17170'),
    ('walking-20-24mph-slow', '17152'),
    ('hiking-cross-country', '17080'),
    ('running-5mph', '12030'),
    ('running-6mph', '12050'),
    ('bicycling-12-14mph', '01030'),
    ('bicycling-stationary', '01200'),
    ('swimming-laps-slow', '18240'),
    ('swimming-laps-fast', '18230'),
    ('swimming-leisurely', '18310'),
    ('weight-lifting-vigorous', '02050'),
    ('resistance-circuit', '02055'),
    ('calisthenics-vigorous', '02020'),
    ('rope-skipping', '02068'),
    ('elliptical-moderate', '02048'),
    ('elliptical-vigorous', '02049'),
    ('rowing-machine-moderate', '02071'),
    ('stair-machine', '02065'),
    ('yoga-hatha', '02150'),
    ('stretching-mild', '02101'),
    ('aerobics-general', '02000'),
    ('basketball-general', '15055'),
    ('soccer-casual', '15610'),
    ('tennis-moderate', '15675'),
    ('house-cleaning-moderate', '05030'),
    ('gardening-moderate', '08245'),
    ('mowing-walking', '08095'),
    ('sitting-quietly', '07021'),
    ('sleeping', '07030'),
]


def _build_seed():
    by_code = {r['activity_code']: r for r in compendium_mets()}
    out = []
    for name, code in _CURATED:
        row = by_code.get(code)
        if row is None:
            raise ValueError(
                f'curated activity {name}: Compendium code {code} '
                f'not in the vendored CSV — fix the curation list')
        met = float(row['met_value'])
        out.append({
            'name': name,
            'display_name': row['description'].replace('\xa0', ' '),
            'activity_code': code, 'met_value': met,
            'category': row['category'],
            'intensity': intensity_band(met),
            'source': COMPENDIUM_ATTRIBUTION,
            'is_prior': True, 'provenance_id': 'nmp-5'})
    return out


SEED_ACTIVITY_DEFINITIONS = _build_seed()
