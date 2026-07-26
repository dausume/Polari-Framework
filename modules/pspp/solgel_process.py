"""
@module pspp.solgel_process

mtt-2 sg-3/sg-4: the sol-gel process route as data.

- SOLGEL_PROCESSING_STAGES — the state-DAG stage vocabulary: sol ->
  gel point -> aging (syneresis) -> the drying FORK (xerogel vs
  aerogel) -> densification. Maps 1:1 onto MaterialState +
  cure_checkpoints exactly like the geopolymer route.
- SOLGEL_DIGITIZED_DATASETS — the Brinker/Iler reference curves as
  POINTS-EMPTY provisional rows: the classic gel-time-vs-pH curve,
  29Si NMR Q^n-vs-time, and xerogel shrinkage-vs-temperature. The
  books are NOT in hand, so each row records the qualitative shape
  and REFUSES numeric reads until the figure is photographed and
  digitized (the Fig 5.22 precedent: refusal is the honest behavior,
  and the refusal itself names the exact data ask).

@consumers
  - polariServer.defClassList seeding (ProcessingStage +
    DigitizedDataset concatenation)
  - pspp.state_resolution / pspp.cure_checkpoints (stages)
"""

import json

_SG_PROVENANCE = ('mtt-2 sg-3/4 sol-gel process seed 2026-07-26 — '
                  'qualitative literature only; numeric curves await '
                  'photographed figures')

_BS = 'Brinker & Scherer, Sol-Gel Science (1990)'

SOLGEL_PROCESSING_STAGES = [
    {'name': 'precursor-solution', 'display_name': 'Precursor solution',
     'material_family': 'sol-gel',
     'description': 'Alkoxide + alcohol cosolvent + water + catalyst '
                    'mixed — hydrolysis beginning.'},
    {'name': 'hydrolyzing-sol', 'display_name': 'Hydrolyzing sol',
     'material_family': 'sol-gel',
     'typical_prior_stage': 'precursor-solution',
     'description': 'Colloidal sol: hydrolysis + condensation growing '
                    'oligomers (acid route) or dense particles (base '
                    'route).'},
    {'name': 'gel-point', 'display_name': 'Gel point',
     'material_family': 'sol-gel',
     'typical_prior_stage': 'hydrolyzing-sol',
     'description': 'A spanning cluster first percolates the volume — '
                    'viscosity diverges, the sol stops flowing.'},
    {'name': 'aging-gel', 'display_name': 'Aging gel (syneresis)',
     'material_family': 'sol-gel',
     'typical_prior_stage': 'gel-point',
     'description': 'Continued condensation + dissolution-'
                    'reprecipitation stiffens the wet network and '
                    'expels pore liquid (syneresis shrinkage).'},
    {'name': 'xerogel', 'display_name': 'Xerogel',
     'material_family': 'sol-gel',
     'typical_prior_stage': 'aging-gel',
     'description': 'Evaporative drying — capillary pressure '
                    'collapses much of the pore network; large '
                    'shrinkage. One arm of the drying FORK.'},
    {'name': 'aerogel', 'display_name': 'Aerogel',
     'material_family': 'sol-gel',
     'typical_prior_stage': 'aging-gel',
     'description': 'Supercritical drying — no liquid-vapor meniscus, '
                    'pore network preserved, minimal shrinkage. The '
                    'other arm of the drying fork.'},
    {'name': 'densified-gel-glass', 'display_name': 'Densified glass',
     'material_family': 'sol-gel',
     'typical_prior_stage': 'xerogel',
     'description': 'Viscous sintering to dense glass well below the '
                    'melt — the sol-gel route to monoliths/films. '
                    '(Aerogels densify too; typical_prior_stage is a '
                    'hint, never a constraint.)'},
]

for _row in SOLGEL_PROCESSING_STAGES:
    _row.setdefault('provenance_id', _SG_PROVENANCE)

#: Points-empty provisional rows — the generic reader REFUSES these
#: (status != 'ready'), and that refusal IS the data ask.
SOLGEL_DIGITIZED_DATASETS = [
    {
        'name': 'silica-solgel-gel-time-vs-ph',
        'source_reference': f'{_BS} (after Iler 1979) — gel time vs '
                            'pH for aqueous silica; figure/page '
                            'PENDING photograph',
        'status': 'provisional-low-confidence',
        'independent_variables_json': '["pH"]',
        'dependent_variables_json': '["gel_time_relative"]',
        'units_json': json.dumps({
            'pH': 'pH', 'gel_time_relative': 'relative (source '
                                             'units pending)'}),
        'source_conditions_json': json.dumps({
            'system': 'aqueous silica sols',
            'note': 'the canonical curve every sol-gel text '
                    'reproduces — exact conditions arrive with the '
                    'photographed figure'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{}',
        'digitization_method': 'NOT digitized — qualitative literature '
                               'recall only',
        'points_json': '[]',
        'qualitative_shape':
            'Gel time is LONGEST near pH 2 (silica isoelectric point '
            '— condensation-rate minimum), falls steeply to a MINIMUM '
            'around pH 5-6 (fastest gelation), then RISES again above '
            '~pH 7 where particles charge-stabilize (high-pH sols can '
            'be indefinitely stable). Metastable slow region below '
            'pH 2.',
        'notes': 'DATA ASK: photograph the gel-time-vs-pH figure '
                 '(Brinker & Scherer or Iler), then digitize points '
                 'and set status=ready. This row exists so the '
                 'refusal names the exact ask.',
    },
    {
        'name': 'silica-solgel-q-speciation-vs-time',
        'source_reference': f'{_BS} Ch.3 — 29Si NMR Q^n evolution '
                            'during TEOS hydrolysis/condensation; '
                            'figure/page PENDING photograph',
        'status': 'provisional-low-confidence',
        'independent_variables_json': '["time_relative"]',
        'dependent_variables_json': '["Q0", "Q1", "Q2", "Q3", "Q4"]',
        'units_json': json.dumps({
            'time_relative': 'relative (source units pending)',
            'Q0': 'fraction', 'Q1': 'fraction', 'Q2': 'fraction',
            'Q3': 'fraction', 'Q4': 'fraction'}),
        'source_conditions_json': json.dumps({
            'system': 'TEOS + water + catalyst',
            'note': 'catalysis (acid vs base) changes the curves — '
                    'the fork this library gates on'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{}',
        'digitization_method': 'NOT digitized — qualitative literature '
                               'recall only',
        'points_json': '[]',
        'qualitative_shape':
            'Sequential rise-and-fall: Q0 decays as Q1 rises; Q1 '
            'hands off to Q2, then Q3, then Q4. Acid-catalyzed '
            'systems plateau with LOW Q4 (weakly-branched gels); '
            'base-catalyzed systems drive on to Q4-rich dense '
            'particles. The SAME motif ledger as the geopolymer '
            'Maekawa curves.',
        'notes': 'DATA ASK: photograph a 29Si NMR Q^n-vs-time figure '
                 '(one acid, one base run ideally), digitize, set '
                 'status=ready — this unlocks measured (not stepped) '
                 'sol-gel structure groups.',
    },
    {
        'name': 'silica-xerogel-shrinkage-vs-temperature',
        'source_reference': f'{_BS} (drying/densification chapters) — '
                            'linear shrinkage vs temperature; '
                            'figure/page PENDING photograph',
        'status': 'provisional-low-confidence',
        'independent_variables_json': '["temperature_C"]',
        'dependent_variables_json': '["linear_shrinkage_percent"]',
        'units_json': json.dumps({
            'temperature_C': 'C',
            'linear_shrinkage_percent': '%'}),
        'source_conditions_json': json.dumps({
            'system': 'silica xerogel monolith, heating',
            'note': 'exact heating schedule arrives with the figure'}),
        'interpolation_policy': 'linear',
        'extrapolation_policy': 'UNSUPPORTED',
        'validity_domain_json': '{}',
        'digitization_method': 'NOT digitized — qualitative literature '
                               'recall only',
        'points_json': '[]',
        'qualitative_shape':
            'Xerogels already carry large drying shrinkage; on '
            'heating, continued dehydroxylation/condensation shrinks '
            'further (~400-700 C), then viscous sintering densifies '
            'to glass roughly 900-1100 C — far below fused-silica '
            'melting. Aerogels show minimal drying shrinkage but '
            'densify similarly at temperature.',
        'notes': 'DATA ASK: photograph a shrinkage-vs-temperature '
                 'figure, digitize, set status=ready — this is also '
                 'the natural calibration input for the mtt-2 Part B '
                 'sintering engine (densification curves).',
    },
]

for _row in SOLGEL_DIGITIZED_DATASETS:
    _row.setdefault('provenance_id', _SG_PROVENANCE)
