"""
@cross-cutting
@module aquaponics.vermicompost_seed
@tags @xc:bindings

Demo vermicompost bins + release profile + two compost loops (aqp-7),
plus the scoring bridge (nutrient-enrichment efficiency). One bin, two
loops over the SAME basil pot system — a direct loop and a periodic
loop — so compare-modes has a live contrast and the scoring engine can
RANK enrichment configurations. Idempotent-by-name.

enrichment_result_json seeds are precomputed snapshots so the score
resolves live out of the box; POST /compost-loops/{name}/simulate
refreshes them. Values ride ABSTRACT PRIORS (flagged).

@consumers
  - polariServer seed_pairs (bins/profiles/loops + scoring rows)
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-7
"""

import json

SEED_VERMICOMPOST_PROFILES = [
    {
        'name': 'mature-castings-mixed',
        'display_name': 'Mature castings (mixed feedstock)',
        'description': 'Soluble release profile of well-cured worm '
                       'castings from mixed kitchen + manure feedstock. '
                       'ABSTRACT literature-range priors (mg soluble '
                       'per kg bed) until a bed is measured.',
        # mg soluble / kg bed — leachable pool.
        'concentrations_json': json.dumps({
            'nitrate-n': 120.0, 'ammonium-n': 40.0,
            'phosphorus-p': 35.0, 'potassium-k': 150.0,
            'calcium-ca': 90.0, 'magnesium-mg': 30.0}),
        'k_min_per_day_20c': 0.03, 'q10': 2.0,
        'transfer_coeff_per_hr': 0.15, 'priors_flagged': True,
        'source': 'vermicompost mineralization literature ranges',
        'provenance_id': 'aqp-7',
    },
]

SEED_COMPOST_BINS = [
    {
        'name': 'kitchen-worm-bin',
        'display_name': 'Kitchen worm bin (Eisenia fetida)',
        'description': 'A 40 L worm bin the aquaponic loop passes '
                       'through for nutrient enrichment.',
        'volume_l': 40.0, 'bed_mass_kg': 12.0, 'worm_density': 0.1,
        'feedstock_kind': 'mixed', 'c_to_n_ratio': 25.0,
        'moisture_target': 0.8, 'temperature_c': 22.0,
        'maturity_days': 60.0,
        'release_profile_name': 'mature-castings-mixed',
        'mode': 'direct', 'on_minutes': 20.0, 'cycle_hours': 6.0,
        'provenance_id': 'aqp-7',
    },
]

SEED_COMPOST_LOOPS = [
    {
        'name': 'basil-loop-direct',
        'display_name': 'Basil loop — direct (continuous) enrichment',
        'description': 'Worm bin inline; all loop water flows through '
                       'the castings continuously.',
        'bin_name': 'kitchen-worm-bin',
        'pot_system_name': 'basil-aquaponic-tent',
        'mode': 'direct', 'assumed_flow_l_per_hr': 1.5,
        'enrichment_result_json': json.dumps({
            'mode': 'direct', 'totalLeachedMg': 74.9,
            'nitrogenUpliftMgPerL': 1.15, 'phosphorusUpliftMgPerL': 0.28,
            'pulsePeakNMgPerL': 1.4}),
        'provenance_id': 'aqp-7 direct',
    },
    {
        'name': 'basil-loop-periodic',
        'display_name': 'Basil loop — periodic (pulsed) enrichment',
        'description': 'Same bin + pot, water routed through on a '
                       'schedule; the bed recharges between windows.',
        'bin_name': 'kitchen-worm-bin',
        'pot_system_name': 'basil-aquaponic-tent',
        'mode': 'periodic', 'assumed_flow_l_per_hr': 1.5,
        'enrichment_result_json': json.dumps({
            'mode': 'periodic', 'totalLeachedMg': 51.2,
            'nitrogenUpliftMgPerL': 0.79, 'phosphorusUpliftMgPerL': 0.19,
            'pulsePeakNMgPerL': 3.6}),
        'provenance_id': 'aqp-7 periodic',
    },
]

# ---- Scoring bridge: enrichment efficiency as a ScoreConcept -------
# Ranks compost loops by the nitrogen they add per unit water (the
# bioremediation uplift). Resolves live from enrichment_result_json.

SEED_ENRICH_SCORE_TERMS = [
    {
        'name': 'nitrogen-enrichment-uplift',
        'display_name': 'Nitrogen enrichment uplift',
        'description': 'Nitrogen the worm bin adds to the loop water '
                       'per litre (bioremediation source uplift).',
        'category': 'aquaponics', 'value_type': 'count',
        'unit': 'mg/L', 'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 0.0, 'max': 3.0}),
        'abstract_tags_json': json.dumps(
            ['nitrogen', 'enrichment', 'vermicompost']),
        'provenance_id': 'aqp-7',
    },
    {
        'name': 'enrichment-total-delivered',
        'display_name': 'Total nutrient delivered',
        'description': 'Total soluble nutrient the bin leaches into the '
                       'loop over the run (mg).',
        'category': 'aquaponics', 'value_type': 'count',
        'unit': 'mg', 'is_positive': True,
        'normalization_json': json.dumps(
            {'method': 'min-max', 'min': 0.0, 'max': 120.0}),
        'abstract_tags_json': json.dumps(['enrichment', 'throughput']),
        'provenance_id': 'aqp-7',
    },
]

SEED_ENRICH_SCORE_CONCEPTS = [
    {
        'name': 'nutrient-enrichment-efficiency',
        'display_name': 'Nutrient enrichment efficiency',
        'description': 'Ranks compost loops by nitrogen uplift per '
                       'litre (w5) and total nutrient delivered (w2) — '
                       'values resolve live from each loop\'s computed '
                       'enrichment.',
        'subject_kind': 'compost-loop',
        'term_weights_json': json.dumps([
            {'term': 'nitrogen-enrichment-uplift', 'weight': 5},
            {'term': 'enrichment-total-delivered', 'weight': 2},
        ]),
        'required_context_names_json': '[]',
        'aggregation': 'weighted-mean', 'levelize': True,
        'abstract_tags_json': json.dumps(
            ['aquaponics', 'vermicompost', 'bioremediation']),
        'provenance_id': 'aqp-7',
    },
]

SEED_ENRICH_SCORE_SUBJECTS = [
    {'name': f'compostloop-{s["name"]}',
     'display_name': s['display_name'], 'kind': 'compost-loop',
     'object_ref_json': json.dumps(
         {'kind': 'objectRef', 'className': 'CompostLoopDefinition',
          'name': s['name']}),
     'description': 'Compost loop scored for enrichment efficiency.'}
    for s in SEED_COMPOST_LOOPS
]

SEED_ENRICH_CONTEXTUALIZED_VALUES = [
    v for s in SEED_COMPOST_LOOPS for v in (
        {'name': f'n-uplift@{s["name"]}',
         'term_name': 'nitrogen-enrichment-uplift',
         'subject_name': f'compostloop-{s["name"]}',
         'context_names_json': '[]', 'pre_normalized_value': None,
         'data_ref_json': json.dumps(
             {'kind': 'objectRef',
              'className': 'CompostLoopDefinition', 'name': s['name'],
              'path': 'enrichment_result_json.nitrogenUpliftMgPerL'}),
         'source': 'objectRef → loop enrichment_result_json',
         'provenance_id': 'aqp-7'},
        {'name': f'total-delivered@{s["name"]}',
         'term_name': 'enrichment-total-delivered',
         'subject_name': f'compostloop-{s["name"]}',
         'context_names_json': '[]', 'pre_normalized_value': None,
         'data_ref_json': json.dumps(
             {'kind': 'objectRef',
              'className': 'CompostLoopDefinition', 'name': s['name'],
              'path': 'enrichment_result_json.totalLeachedMg'}),
         'source': 'objectRef → loop enrichment_result_json',
         'provenance_id': 'aqp-7'},
    )
]
