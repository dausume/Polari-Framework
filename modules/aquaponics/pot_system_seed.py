"""
@cross-cutting
@module aquaponics.pot_system_seed
@tags @xc:bindings

Demo pot systems (aqp-6) + the scoring bridge. Two bound
configurations of the same basil pot — a healthy ventilated tent and
a failing sealed chamber — so survival + impact have a live pass/fail
contrast, and the context-scoring engine can RANK them for
environmental impact. Idempotent-by-name.

The impact_result_json seeds are precomputed snapshots so the score
resolves live out of the box; POST /system/{name}/impact refreshes
them.

@consumers
  - polariServer seed_pairs (systems + the scoring rows)
@see /AQUAPONICS_MODULE_PLAN.md
"""

import json

SEED_POT_SYSTEMS = [
    {
        'name': 'basil-aquaponic-tent',
        'display_name': 'Basil / aquaponic / ventilated tent',
        'description': 'The reference healthy configuration.',
        'pot_name': 'demo-herb-pot', 'soil_name': 'coir-perlite-mix',
        'water_name': 'tilapia-aquaponic-loop',
        'plant_name': 'sweet-basil',
        'atmosphere_name': 'ventilated-grow-tent',
        # plant-growth-sim phase 8 (2026-07-15) — binds the REAL
        # computed light-field path (aquaponics.light_field) alongside
        # the static atmosphere_name.light_ppfd_umol_m2_s field the
        # 'light' stress curve already used; see aquaponics.light_seed
        # for the source's own docstring on why its intensity_w_m2
        # was solved to roughly match this system's existing 350 PPFD.
        'light_source_name': 'demo-herb-pot-grow-light',
        # Precomputed snapshot (see system_impact); refreshed on POST.
        'impact_result_json': json.dumps({
            'permanentCarbonG': 1.76,
            'co2EquivalentSequesteredG': 6.4533,
            'carbonCapturedG': 7.7,
            'lifetimeCo2FixedMg': 52327.0,
            'lifetimeO2ReleasedMg': 38029.2,
            'nitrogenRemovedMg': 1695.1,
            'phosphorusRemovedMg': 221.1,
            'potassiumRemovedMg': 1105.5,
            'waterThroughputL': 4320.0,
            'lifetimeDays': 120.0}),
        'provenance_id': 'aqp-6 reference system',
    },
    {
        'name': 'basil-aquaponic-sealed',
        'display_name': 'Basil / aquaponic / sealed chamber',
        'description': 'Same plant + water, but a sealed chamber — '
                       'CO2 depletes and the plant fails.',
        'pot_name': 'demo-herb-pot', 'soil_name': 'coir-perlite-mix',
        'water_name': 'tilapia-aquaponic-loop',
        'plant_name': 'sweet-basil',
        'atmosphere_name': 'sealed-chamber',
        'impact_result_json': json.dumps({
            'permanentCarbonG': 1.76,
            'co2EquivalentSequesteredG': 6.4533,
            'carbonCapturedG': 7.7,
            'lifetimeCo2FixedMg': 52327.0,
            'lifetimeO2ReleasedMg': 38029.2,
            'nitrogenRemovedMg': 1695.1,
            'phosphorusRemovedMg': 221.1,
            'potassiumRemovedMg': 1105.5,
            'waterThroughputL': 4320.0,
            'lifetimeDays': 120.0}),
        'provenance_id': 'aqp-6 failing system',
    },
    {
        'name': 'basil-water-batched',
        'display_name': 'Basil / aquaponic / batched water',
        'description': 'Same pot/plant/atmosphere/light as the '
                       'healthy reference tent, but the water source '
                       'CYCLES on a schedule (plant-growth-sim phase '
                       '10, 2026-07-15) instead of one static binding '
                       '— a deliberate, controlled Fe-stress window '
                       'each cycle, distinct from '
                       'basil-aquaponic-tent (always rich) and '
                       'basil-aquaponic-sealed (atmosphere-stressed).',
        'pot_name': 'demo-herb-pot', 'soil_name': 'coir-perlite-mix',
        # Fallback only — water_batch_schedule_name overrides this
        # whenever it resolves; kept as an honest "what if the
        # schedule fails to resolve" default, same pattern as
        # light_source_name's own fallback-to-static-field behavior.
        'water_name': 'hydroponic-reservoir',
        'water_batch_schedule_name': 'basil-fe-stress-cycle',
        'plant_name': 'sweet-basil',
        'atmosphere_name': 'ventilated-grow-tent',
        'light_source_name': 'demo-herb-pot-grow-light',
        'impact_result_json': '',
        'provenance_id': 'plant-growth-sim phase 10',
        'notes': 'demo system for water batching/nutrient-source '
                 'cycling — see aquaponics.water_batch_seed.',
    },
    {
        'name': 'dwarf-pepper-tent',
        'display_name': 'Dwarf pepper / ventilated tent',
        'description': 'plant-growth-sim phase 12 (2026-07-15) — the '
                       'SAME pot/soil/water/atmosphere/light as '
                       'basil-aquaponic-tent, ONLY the plant species '
                       'differs, isolating species-specific growth '
                       'differences for a real, apples-to-apples '
                       'comparison against sweet-basil.',
        'pot_name': 'demo-herb-pot', 'soil_name': 'coir-perlite-mix',
        'water_name': 'hydroponic-reservoir',
        'plant_name': 'dwarf-pepper',
        'atmosphere_name': 'ventilated-grow-tent',
        'light_source_name': 'demo-herb-pot-grow-light',
        'impact_result_json': '',
        'provenance_id': 'plant-growth-sim phase 12',
        'notes': 'the second full-parity comparison species — see '
                 'aquaponics.plant_seed for the full rationale.',
    },
]

# ---- Scoring bridge: environmental impact as a ScoreConcept -------
# The context-scoring engine ranks pot systems by resolving these
# values LIVE from each system's impact_result_json (the objectRef
# seam, beeswax@L1 FEM idiom).

SEED_AQP_SCORE_TERMS = [
    {
        'name': 'permanent-carbon-sequestered',
        'display_name': 'Permanent carbon sequestered',
        'description': 'Carbon locked out of the atmosphere over the '
                       'plant lifetime (permanent-fate parts only).',
        'category': 'aquaponics', 'value_type': 'count',
        'unit': 'g', 'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 0.0, 'max': 5.0}),
        'abstract_tags_json': json.dumps(
            ['carbon', 'sequestration', 'environment']),
        'provenance_id': 'aqp-6',
    },
    {
        'name': 'nitrogen-bioremediation',
        'display_name': 'Nitrogen removed from the loop',
        'description': 'Nitrogen the plant pulls from the aquaponic '
                       'water over its lifetime (bioremediation).',
        'category': 'aquaponics', 'value_type': 'count',
        'unit': 'mg', 'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 0.0, 'max': 3000.0}),
        'abstract_tags_json': json.dumps(
            ['nitrogen', 'bioremediation', 'aquaponics']),
        'provenance_id': 'aqp-6',
    },
    {
        'name': 'water-throughput',
        'display_name': 'Water throughput',
        'description': 'Water passed through the pot over the '
                       'lifetime — lower is better per unit biomass.',
        'category': 'aquaponics', 'value_type': 'count',
        'unit': 'L', 'is_positive': False,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 0.0, 'max': 8000.0}),
        'abstract_tags_json': json.dumps(['water-use', 'efficiency']),
        'provenance_id': 'aqp-6',
    },
]

SEED_AQP_SCORE_SUBJECTS = [
    {'name': f'potsys-{s["name"]}',
     'display_name': s['display_name'], 'kind': 'pot-system',
     'object_ref_json': json.dumps(
         {'kind': 'objectRef', 'className': 'PotSystemDefinition',
          'name': s['name']}),
     'description': 'Pot system scored for environmental impact.'}
    for s in SEED_POT_SYSTEMS
]

SEED_AQP_CONTEXTUALIZED_VALUES = [
    v for s in SEED_POT_SYSTEMS for v in (
        {'name': f'permanent-carbon@{s["name"]}',
         'term_name': 'permanent-carbon-sequestered',
         'subject_name': f'potsys-{s["name"]}',
         'context_names_json': '[]',
         'pre_normalized_value': None,
         'data_ref_json': json.dumps(
             {'kind': 'objectRef',
              'className': 'PotSystemDefinition', 'name': s['name'],
              'path': 'impact_result_json.permanentCarbonG'}),
         'source': 'objectRef → system impact_result_json',
         'provenance_id': 'aqp-6'},
        {'name': f'nitrogen-removed@{s["name"]}',
         'term_name': 'nitrogen-bioremediation',
         'subject_name': f'potsys-{s["name"]}',
         'context_names_json': '[]',
         'pre_normalized_value': None,
         'data_ref_json': json.dumps(
             {'kind': 'objectRef',
              'className': 'PotSystemDefinition', 'name': s['name'],
              'path': 'impact_result_json.nitrogenRemovedMg'}),
         'source': 'objectRef → system impact_result_json',
         'provenance_id': 'aqp-6'},
        {'name': f'water-throughput@{s["name"]}',
         'term_name': 'water-throughput',
         'subject_name': f'potsys-{s["name"]}',
         'context_names_json': '[]',
         'pre_normalized_value': None,
         'data_ref_json': json.dumps(
             {'kind': 'objectRef',
              'className': 'PotSystemDefinition', 'name': s['name'],
              'path': 'impact_result_json.waterThroughputL'}),
         'source': 'objectRef → system impact_result_json',
         'provenance_id': 'aqp-6'},
    )
]

SEED_AQP_SCORE_CONCEPTS = [
    {
        'name': 'pot-environmental-impact',
        'display_name': 'Pot environmental impact',
        'description': 'Ranks bound pot systems by permanent carbon '
                       'sequestered (w5), nitrogen bioremediation '
                       '(w3), and water throughput (w2, inverted) — '
                       'values resolve live from each system\'s '
                       'computed impact.',
        'subject_kind': 'pot-system',
        'term_weights_json': json.dumps([
            {'term': 'permanent-carbon-sequestered', 'weight': 5},
            {'term': 'nitrogen-bioremediation', 'weight': 3},
            {'term': 'water-throughput', 'weight': 2},
        ]),
        'required_context_names_json': '[]',
        'aggregation': 'weighted-mean', 'levelize': True,
        'abstract_tags_json': json.dumps(
            ['environment', 'aquaponics', 'sustainability']),
        'provenance_id': 'aqp-6',
    },
]
