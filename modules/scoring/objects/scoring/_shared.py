"""@module scoring.objects.scoring._shared — what the scoring row classes share (constants, seeds, helpers); split from scoring_basis.py (sap-2c)."""

VALUE_TYPES = ('percentage', 'currency', 'count', 'rate', 'index',
               'ratio', 'score', 'custom')
CONTEXT_TYPES = {
    'location': 4,      # granularity_json refines: city 8, state 4…
    'timeframe': 5,
    'economic': 3,
    'demographic': 3,
    'custom': 1,
    # fsc-1: Firmware Score Profiles reuse this pipeline. A hardware context
    # ('hardware:<board>') holds a whole-solution value; a purpose context
    # ('purpose:<name>') holds one Purpose's share of it (more specific).
    'hardware': 5,
    'purpose': 6,
}
LOCATION_SPECIFICITY = {'city': 8, 'state': 4, 'country': 2,
                        'region': 1}
