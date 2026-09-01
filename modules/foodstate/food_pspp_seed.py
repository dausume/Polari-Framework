"""
@module foodstate.food_pspp_seed

fsp-0 — the food vocabulary as PSPP ROWS (the zero-schema-change
proof): processing stages (family 'food'), process definitions with
their I2 execution effects DECLARED, and the three evidence methods
the food honesty ladder adds to the one shared vocabulary. All of it
seeds classes pspp already owns — foodstate adds no state/claim/
process schema of its own.

I2 examples made concrete here: `chop` and `simmer` are
TRANSFORMATIVE (each produces a NEW FoodState — chop changes
structure only, and its output schema says so); `measure-ph` and
`titrate-acidity` are OBSERVATIONAL (they attach PropertyClaims to
the existing state, never a new state — the measured-pH-on-
tomato-sauce-state example from the ratified direction).

@consumers
  - polariServer (seed pairs: ProcessingStage / MaterialProcess-
    Definition / EvidenceMethod concat these onto the pspp seeds)
  - foodstate.selftest_foodstate
"""

import json

_PROV = 'fsp-0 (FOOD_STATE_PSPP_PLAN.md, ratified 2026-08-31)'

#: Evidence methods the food ladder ADDS to pspp's shared vocabulary
#: (rows in pspp.EvidenceMethod — same class, new identifiers).
SEED_FOOD_EVIDENCE_METHODS = [
    {'name': 'mass-balance', 'category': 'derived',
     'description': 'Deterministic conservation bookkeeping across a '
                    'transform: water loss/evaporation, '
                    'concentration, dilution, mixing. No model — '
                    'exact given the inputs.',
     'required_provenance': 'input state claims + the conservation '
                            'basis (what was conserved, what left)',
     'default_validation_class': 'unvalidated',
     'supports_uncertainty': True},
    {'name': 'retention-factor', 'category': 'empirical',
     'description': 'USDA Nutrient Retention Factors R6 + Cooking '
                    'Yields (CC0) applied per cooking method — the '
                    'cited BULK fallback (ladder rung 4) for '
                    'micronutrients when no mechanistic model '
                    'exists; already the nmp-3 method.',
     'required_provenance': 'R6 table row + cooking-method match',
     'default_validation_class': 'unvalidated',
     'supports_uncertainty': False},
    {'name': 'conditional-prediction', 'category': 'derived-model',
     'description': 'A DIRECTION with conditions and confidence — '
                    'never a magnitude (D6). The only method '
                    'physiological gastric-response claims may use.',
     'required_provenance': 'model/source + the conditions list + '
                            'confidence label',
     'default_validation_class': 'unvalidated',
     'supports_uncertainty': True},
]

#: Food route stages (pspp.ProcessingStage rows, family 'food') —
#: extensible rows, families add their own without code changes.
SEED_FOOD_STAGES = [
    {'name': 'raw-ingredient', 'display_name': 'Raw ingredient',
     'description': 'As-harvested/as-purchased — the canonical '
                    "'#as-defined' anchor of a food material."},
    {'name': 'washed', 'display_name': 'Washed',
     'typical_prior_stage': 'raw-ingredient',
     'description': 'Surface-cleaned; composition ~unchanged.'},
    {'name': 'cut', 'display_name': 'Cut / chopped',
     'typical_prior_stage': 'washed',
     'description': 'Structure changed (particle size, exposed '
                    'surface); composition unchanged — the '
                    'structure-only transform.'},
    {'name': 'mixed', 'display_name': 'Mixed / combined',
     'typical_prior_stage': 'cut',
     'description': 'Multiple input states combined — composition '
                    'by mass-weighted balance.'},
    {'name': 'cooked-moist', 'display_name': 'Cooked (moist heat)',
     'typical_prior_stage': 'mixed',
     'description': 'Simmered/boiled/steamed: gelatinization, '
                    'denaturation, cell breakdown, leaching.'},
    {'name': 'cooked-dry', 'display_name': 'Cooked (dry heat)',
     'typical_prior_stage': 'mixed',
     'description': 'Baked/fried/roasted: Maillard regime, surface '
                    'dehydration, lipid uptake when fried.'},
    {'name': 'concentrated', 'display_name': 'Concentrated / reduced',
     'typical_prior_stage': 'cooked-moist',
     'description': 'Water driven off — solutes (acids, sugars) '
                    'concentrate by mass balance.'},
    {'name': 'fermented', 'display_name': 'Fermented',
     'typical_prior_stage': 'raw-ingredient',
     'description': 'Microbial transformation — acids produced, the '
                    'legitimate plant-B12 route (nut-2).'},
    {'name': 'dried', 'display_name': 'Dried',
     'typical_prior_stage': 'raw-ingredient',
     'description': 'Water activity lowered for stability.'},
    {'name': 'frozen', 'display_name': 'Frozen',
     'description': 'Storage state; ice crystals may damage cell '
                    'integrity (structure claim on thaw).'},
    {'name': 'thawed', 'display_name': 'Thawed',
     'typical_prior_stage': 'frozen',
     'description': 'Post-freeze state — structure ≠ never-frozen.'},
    {'name': 'prepared-food', 'display_name': 'Prepared food',
     'description': 'Terminal state a recipe process-graph yields — '
                    'what meal planning consumes (fsp-6).'},
]

for _row in SEED_FOOD_STAGES:
    _row.setdefault('material_family', 'food')
    _row.setdefault('provenance_id', _PROV)


def _proc(name, display, ptype, effect, description, params=None,
          out_schema=None, energy=''):
    return {
        'name': name, 'display_name': display,
        'process_type': ptype, 'execution_effect': effect,
        'energy_deposition_model': energy,
        'material_family': 'food',
        'accepted_input_constraints_json': '{}',
        'parameter_schema_json': json.dumps(params or {}),
        'transformation_engine_refs_json': '[]',  # fsp-2 wires engines
        'output_state_schema_json': json.dumps(out_schema or {}),
        'description': description,
        'provenance_id': _PROV,
        'notes': ('vocabulary-only in fsp-0 — engines arrive in '
                  'fsp-2 behind I5 interfaces; running this now '
                  'REFUSES rather than inventing numbers'),
    }


#: Food processes (pspp.MaterialProcessDefinition rows). I2: effects
#: DECLARED, never inferred.
SEED_FOOD_PROCESSES = [
    _proc('food-wash', 'Wash', 'preparation', 'TRANSFORMATIVE',
          'Surface cleaning; near-identity on composition.',
          {'water_temp_c': 'number'}, {'stage': 'washed'}),
    _proc('food-chop', 'Chop / cut', 'preparation', 'TRANSFORMATIVE',
          'STRUCTURE-ONLY transform: particle size + exposed '
          'surface change; composition passes through by identity '
          '(the raw→chopped tomato edge).',
          {'target_particle_size_m': 'number'},
          {'stage': 'cut', 'changes': ['particle-size'],
           'conserves': ['composition']}),
    _proc('food-mix', 'Mix / combine', 'preparation',
          'TRANSFORMATIVE',
          'Combine input states; composition = mass-weighted '
          'balance of inputs.',
          {}, {'stage': 'mixed', 'composition': 'mass-balance'}),
    _proc('food-simmer', 'Simmer', 'heating', 'TRANSFORMATIVE',
          'Moist heat below boil (the 95 °C, 30 min tomato edge): '
          'water evaporates (mass balance), cell integrity falls, '
          'gelatinization/denaturation fractions rise (cited models, '
          'fsp-2).',
          {'temp_c': 'number', 'minutes': 'number',
           'covered': 'bool'},
          {'stage': 'cooked-moist',
           'changes': ['water', 'cell-integrity',
                       'starch-gelatinization-fraction',
                       'protein-denaturation-fraction']},
          energy='conventional-heating'),
    _proc('food-boil', 'Boil', 'heating', 'TRANSFORMATIVE',
          'Moist heat at boil; adds leaching losses to water '
          '(retention factors cover micronutrients).',
          {'minutes': 'number', 'water_ratio': 'number'},
          {'stage': 'cooked-moist'},
          energy='conventional-heating'),
    _proc('food-steam', 'Steam', 'heating', 'TRANSFORMATIVE',
          'Moist heat without immersion — lower leaching than boil '
          '(the steam-vs-fry comparison lever).',
          {'minutes': 'number'}, {'stage': 'cooked-moist'},
          energy='conventional-heating'),
    _proc('food-fry', 'Fry', 'heating', 'TRANSFORMATIVE',
          'Dry high heat in fat: Maillard regime, surface '
          'dehydration, lipid uptake.',
          {'temp_c': 'number', 'minutes': 'number',
           'fat_type': 'string'},
          {'stage': 'cooked-dry',
           'changes': ['water', 'lipids', 'maillard-products']},
          energy='conventional-heating'),
    _proc('food-bake', 'Bake', 'heating', 'TRANSFORMATIVE',
          'Dry oven heat (the 180 °C, 25 min recipe edge).',
          {'temp_c': 'number', 'minutes': 'number'},
          {'stage': 'cooked-dry'},
          energy='conventional-heating'),
    _proc('food-reduce', 'Reduce / concentrate', 'heating',
          'TRANSFORMATIVE',
          'Drive water off: solute concentrations (organic acids, '
          'sugars) RISE by mass balance — the chopped→cooked→sauce '
          'acid-concentration edge.',
          {'target_mass_fraction': 'number'},
          {'stage': 'concentrated',
           'changes': ['water'],
           'concentrates': ['organic-acids', 'sugars', 'minerals']},
          energy='conventional-heating'),
    _proc('food-cool', 'Cool / rest', 'cooling', 'TRANSFORMATIVE',
          'Temperature falls; starch retrogradation may begin '
          '(crystallinity claim).',
          {'minutes': 'number'}, {}),
    _proc('food-freeze', 'Freeze', 'cooling', 'TRANSFORMATIVE',
          'Storage transform; ice-crystal damage lands as a '
          'cell-integrity claim on thaw.',
          {}, {'stage': 'frozen'}),
    _proc('food-thaw', 'Thaw', 'preparation', 'TRANSFORMATIVE',
          'Frozen → thawed; drip loss by mass balance.',
          {}, {'stage': 'thawed'}),
    _proc('food-ferment', 'Ferment', 'biotransformation',
          'TRANSFORMATIVE',
          'Microbial acid production (chemistry domain gains acids); '
          'the honest plant-B12 route.',
          {'days': 'number', 'culture': 'string'},
          {'stage': 'fermented', 'changes': ['organic-acids',
                                             'sugars']}),
    # ---- OBSERVATIONAL: measurements attach claims, never states --
    _proc('food-measure-ph', 'Measure pH', 'measurement',
          'OBSERVATIONAL',
          'Electrode pH on the CURRENT state → a MEASURED '
          'PropertyClaim (the pH-4.31-on-state-184 example); '
          'no new state.',
          {'electrode': 'string', 'temp_c': 'number'}),
    _proc('food-titrate-acidity', 'Titrate acidity', 'measurement',
          'OBSERVATIONAL',
          'Titratable acidity → MEASURED claim on the state.',
          {'titrant': 'string', 'endpoint_ph': 'number'}),
    _proc('food-measure-water-activity', 'Measure water activity',
          'measurement', 'OBSERVATIONAL',
          'aw meter → MEASURED structure-domain claim.',
          {}),
]
