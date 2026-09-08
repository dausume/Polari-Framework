"""@module scoring.objects.agreement_policy._shared — what the agreement_policy row classes share (constants, seeds, helpers); split from agreement_policy_basis.py (sap-2c)."""
import json

def classify_max(value, bands, fallback='unclassified'):
    """First band whose 'max' the value does not exceed."""
    for band in bands:
        if value <= band.get('max', 1.0) + 1e-9:
            return band.get('label', fallback)
    return bands[-1].get('label', fallback) if bands else fallback
def classify_min(value, bands, fallback='unclassified'):
    """First band whose 'min' the value meets (bands ordered
    strongest-first)."""
    for band in bands:
        if value >= band.get('min', 0.0) - 1e-9:
            return band.get('label', fallback)
    return bands[-1].get('label', fallback) if bands else fallback
def policy_bands(policy_row):
    """The three parsed band sets off a policy row."""
    def loads(attr):
        try:
            return json.loads(getattr(policy_row, attr, '') or '[]')
        except Exception:
            return []
    return {
        'direction': loads('direction_bands_json'),
        'weight': loads('weight_bands_json'),
        'similarity': loads('similarity_bands_json'),
    }
SEED_AGREEMENT_POLICIES = [{
    'name': 'default-agreement',
    'display_name': 'Default agreement bands',
    'description': 'Dustin 2026-07-08: 50/50 divisive; 50-65 slight '
                   'majority; 65-85 large majority; 85-99 '
                   'near-consensus; above = genuine consensus. Weight '
                   'and similarity bands are first-cut defaults — '
                   'edit this row to recalibrate every aggregate.',
    'direction_bands_json': json.dumps([
        {'label': 'divisive', 'max': 0.5},
        {'label': 'slight-majority', 'max': 0.65},
        {'label': 'large-majority', 'max': 0.85},
        {'label': 'near-consensus', 'max': 0.99},
        {'label': 'consensus', 'max': 1.0},
    ]),
    'weight_bands_json': json.dumps([
        {'label': 'aligned-weighting', 'max': 0.15},
        {'label': 'varied-weighting', 'max': 0.4},
        {'label': 'contested-weighting', 'max': 10.0},
    ]),
    'similarity_bands_json': json.dumps([
        {'label': 'shared-definition', 'min': 0.9},
        {'label': 'broadly-aligned', 'min': 0.7},
        {'label': 'partially-aligned', 'min': 0.4},
        {'label': 'divergent', 'min': -1.0},
    ]),
}]
