"""
@module foodstate.food_acid_seed

fsp-3 (first slice) — ORGANIC-ACID claims for the acid-chain proof
food (tomato), partially closing the D4 organic-acid gap for the
one ingredient the fsp-3 acceptance chain exercises.

Source (fetched + read this session, 2026-09-01): Agius, von
Tucher & Rozhon 2018, "Quantification of sugars and organic acids
in tomato fruits" (MethodsX 5:537-550, PMC6046607; HPLC-UV 210 nm,
GC-MS cross-validated <3%). Ripe Heinz 1706 fruit: citric
1940 mg/l, malic ~511 mg/l; unripe green: citric 4553 mg/l, malic
607 mg/l. Values are per litre of extract — converted to per-100g
FRESH WEIGHT under a stated density≈1.0 g/ml assumption (named on
every claim). The RANGE (ripe→green) rides value_json; the RIPE
value is the claim (the canonical raw-ripe state).

Other roster foods stay honest UNKNOWNs — one cited measurement
per food is the only way more of these appear (D4).

@consumers
  - polariServer (PropertyClaim seed concat)
  - foodstate.custom.food_chemistry (ingredient_acidity), selftests
"""

import json

_CITE = ('Agius, von Tucher & Rozhon 2018, MethodsX 5:537-550 '
         '(PMC6046607), HPLC-UV 210 nm, GC-MS cross-validated; '
         'read 2026-09-01')

_ASSUMPTIONS = [
    'mg/l extract converted to mg/100g fresh weight under a stated '
    'density ~1.0 g/ml assumption (named, not measured)',
    'ripe-fruit value is the claim (canonical raw state); the '
    'ripe-to-green span rides value_json.range',
    'single cultivar (Heinz 1706) — varietal spread is real and '
    'larger than this row states (published malic spans ~60-484 '
    'mg/100g across studies)',
]


def _acid_claim(species, ripe_g, green_g):
    subject = 'tomato-raw#as-defined'
    return {
        'name': f'{subject}:organic-acid-{species}@L0',
        'subject_state_key': subject,
        'property_meaning_name': f'organic-acid-{species}',
        'scale_level': 0,
        'value': ripe_g,
        'value_json': json.dumps(
            {'range': sorted([ripe_g, green_g]),
             'rangeMeaning': 'ripe-to-green span, same study'}),
        'units': 'g/100g',
        'evidence_method': 'literature',
        'assumptions_json': json.dumps(_ASSUMPTIONS),
        'validity_json': json.dumps(
            {'basis': 'per-100g fresh weight', 'state': 'as-defined',
             'cultivar': 'Heinz 1706'}),
        'source_execution_id': '',
        'confidence_json': '',
        'provenance_id': _CITE,
        'notes': '',
    }


SEED_FOOD_ACID_CLAIMS = [
    _acid_claim('citric', 0.194, 0.455),
    _acid_claim('malic', 0.051, 0.061),
]
