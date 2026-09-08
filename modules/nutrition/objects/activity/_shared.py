"""@module nutrition.objects.activity._shared — what the activity row classes share (constants, seeds, helpers); split from activity_basis.py (sap-2c)."""
from nutrition.custom.vendor_data import compendium_mets

INTENSITY_BANDS = ('light', 'moderate', 'vigorous')
COMPENDIUM_ATTRIBUTION = ('Herrmann SD et al., 2024 Adult Compendium '
                          'of Physical Activities (pacompendium.com); '
                          'values unaltered')
def intensity_band(met):
    """Compendium MET cutoffs: <3 light, 3-5.9 moderate, >=6 vigorous."""
    return ('light' if met < 3.0
            else 'moderate' if met < 6.0 else 'vigorous')
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
