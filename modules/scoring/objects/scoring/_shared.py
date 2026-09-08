"""@module scoring.objects.scoring._shared — what the scoring row classes share (constants, seeds, helpers); split from scoring_basis.py (sap-2c)."""

VALUE_TYPES = ('percentage', 'currency', 'count', 'rate', 'index',
               'ratio', 'score', 'custom')
CONTEXT_TYPES = {
    'location': 4,      # granularity_json refines: city 8, state 4…
    'timeframe': 5,
    'economic': 3,
    'demographic': 3,
    'custom': 1,
}
LOCATION_SPECIFICITY = {'city': 8, 'state': 4, 'country': 2,
                        'region': 1}
