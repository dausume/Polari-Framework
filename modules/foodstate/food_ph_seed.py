"""
@module foodstate.food_ph_seed

mpa-1 — literature pH PRIORS as PropertyClaims on the canonical
states (the chemistry-domain contract's first cited rows; fsp-3
proper adds titratable acidity + speciation later).

Source: the FDA/CFSAN-lineage "Approximate pH of Foods and Food
Products" table (public domain; compiled from Bridges & Mattice
1939, FDA BAM 1995 Landry et al., et al.). Ranges VERIFIED
2026-09-01 against a live mirror (webpal.org lacf-phs.htm) — each
verified row says so; the few rows the table does not carry
(cultured yogurt, fresh meats) are TRANSCRIBED typical ranges,
labeled unverified with their own citation line. Midpoint = the
claim value; the printed range rides value_json. No food gets a pH
invented: roster foods absent here stay honest UNKNOWNs in the
acidity reports.

@consumers
  - polariServer (PropertyClaim seed concat)
  - nutrition.custom.acidity_analysis (meal acid share)
  - foodstate.selftest_food_ph
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-1
"""

import json

_VERIFIED = ('FDA/CFSAN-lineage approximate-pH table (Bridges & '
             'Mattice 1939; FDA BAM 1995); range verified 2026-09-01 '
             'against the webpal.org lacf-phs mirror')
_TRANSCRIBED = ('typical published range, TRANSCRIBED WITHOUT '
                'same-session verification — verify against the '
                'cited literature before publication-grade use')

#: slug → (lo, hi, provenance, note)
_PH_RANGES = {
    # fruits + tomato (the acid backbone)
    'tomato-raw': (4.30, 4.90, _VERIFIED, 'straddles 4.6'),
    'orange-raw': (3.69, 4.34, _VERIFIED, 'Florida oranges row'),
    'apple-raw': (3.30, 4.00, _VERIFIED, ''),
    'banana-raw': (4.50, 5.20, _VERIFIED, 'straddles 4.6'),
    'blueberries-raw': (3.12, 3.33, _VERIFIED, 'Maine row'),
    'strawberries-raw': (3.00, 3.90, _VERIFIED, ''),
    # vegetables
    'carrot-raw': (5.88, 6.40, _VERIFIED, ''),
    'celery-raw': (5.70, 6.00, _VERIFIED, ''),
    'cucumber-raw': (5.12, 5.78, _VERIFIED, ''),
    'potato-russet-raw': (5.40, 5.90, _VERIFIED, ''),
    'sweet-potato-raw': (5.30, 5.60, _VERIFIED, ''),
    'spinach-raw': (5.50, 6.80, _VERIFIED, ''),
    'broccoli-raw': (6.30, 6.52, _VERIFIED, 'cooked-broccoli row'),
    'kale-raw': (6.36, 6.80, _VERIFIED, 'cooked-kale row'),
    'lettuce-romaine-raw': (5.80, 6.15, _VERIFIED, 'lettuce row'),
    'onion-raw': (5.32, 5.60, _VERIFIED, 'yellow-onion row'),
    'garlic-raw': (5.80, 5.80, _VERIFIED, 'single value printed'),
    'mushroom-white-raw': (6.00, 6.70, _VERIFIED, ''),
    'bell-pepper-red-raw': (4.65, 5.45, _VERIFIED, 'peppers row'),
    'avocado-raw': (6.27, 6.58, _VERIFIED, ''),
    # dairy + egg
    'milk-whole': (6.40, 6.80, _VERIFIED, 'cow milk row'),
    'cheese-cheddar': (5.90, 5.90, _VERIFIED,
                       'single value printed'),
    'egg-whole-raw': (6.58, 6.58, _VERIFIED,
                      'new-laid whole egg; white 7.96 / yolk 6.10 '
                      'on the same table'),
    'yogurt-plain-whole': (4.00, 4.65, _TRANSCRIBED,
                           'cultured dairy; buttermilk on the '
                           'verified table is 4.41-4.83'),
    # fish + meats (post-rigor muscle ranges)
    'salmon-atlantic-raw': (5.85, 6.50, _VERIFIED,
                            'fresh boiled salmon row'),
    'cod-raw': (5.30, 6.10, _VERIFIED, 'boiled cod row'),
    'chicken-breast-raw': (5.70, 6.10, _TRANSCRIBED,
                           'post-rigor breast muscle'),
    'beef-chuck-raw': (5.30, 6.20, _TRANSCRIBED, ''),
    'ground-beef-90-raw': (5.30, 6.20, _TRANSCRIBED, ''),
    'pork-loin-raw': (5.50, 6.20, _TRANSCRIBED, ''),
    'turkey-ground-raw': (5.70, 6.20, _TRANSCRIBED, ''),
    'tilapia-raw': (6.00, 6.80, _TRANSCRIBED, ''),
    # grains / legumes as eaten (cooked rows where the table
    # carries them — the raw dry goods have no meaningful pH)
    'rice-white-raw': (6.00, 6.70, _VERIFIED,
                       'cooked-white-rice row (as-eaten)'),
    'oats-rolled': (6.20, 6.60, _VERIFIED,
                    'cooked-oatmeal row (as-eaten)'),
    'pasta-dry': (5.10, 6.41, _VERIFIED,
                  'cooked-macaroni row (as-eaten)'),
    'black-beans-dry': (5.60, 6.50, _VERIFIED,
                        'beans row (as-eaten)'),
    'lentils-dry': (6.30, 6.83, _VERIFIED,
                    'cooked-lentils row (as-eaten)'),
    'chickpeas-dry': (6.48, 6.80, _VERIFIED, 'garbanzo row'),
    'tofu-firm': (7.20, 7.20, _VERIFIED,
                  'soybean-curd row, single value'),
    'walnuts-raw': (5.42, 5.42, _VERIFIED,
                    'English-walnuts row, single value'),
}


def build_ph_claim_seeds():
    seeds = []
    for slug, (lo, hi, prov, note) in sorted(_PH_RANGES.items()):
        subject = f'{slug}#as-defined'
        assumptions = [
            'approximate pH of the food as described by the cited '
            'table (varietal/ripeness/handling variation is real — '
            'the RANGE is the claim, the midpoint a convenience)',
        ]
        if 'as-eaten' in note or 'cooked' in note:
            assumptions.append(
                'value is for the COOKED/as-eaten form riding the '
                'raw-goods identity — the dry good itself has no '
                'meaningful solution pH')
        if prov is _TRANSCRIBED:
            assumptions.append(_TRANSCRIBED)
        seeds.append({
            'name': f'{subject}:pH@L0',
            'subject_state_key': subject,
            'property_meaning_name': 'pH',
            'scale_level': 0,
            'value': round((lo + hi) / 2.0, 3),
            'value_json': json.dumps({'range': [lo, hi]}),
            'units': 'pH',
            'evidence_method': 'literature',
            'assumptions_json': json.dumps(assumptions),
            'validity_json': json.dumps(
                {'basis': 'as-described', 'state': 'as-defined'}),
            'source_execution_id': '',
            'confidence_json': ('' if prov is _VERIFIED else
                                json.dumps({'label': 'unverified-'
                                                     'transcription'})),
            'provenance_id': prov + (f'; {note}' if note else ''),
            'notes': '',
        })
    return seeds


SEED_FOOD_PH_CLAIMS = build_ph_claim_seeds()
