"""
@module bizops.bizops_seed

The canonical ladder (setup axiom -> upgrade edges), the local-
economy baseline track, the three generic workflows, and the one
live business profile. NO orders are seeded — the registrar starts
honest and empty.

@consumers polariServer seed_pairs
"""

import json

SEED_BUSINESS_STAGES = [
    {
        'name': 'stage-0-solo-offtime',
        'stage_index': 0,
        'display_name': 'Solo, off-time (the origin)',
        'headcount': 1, 'weekly_hours': 10.0,
        'time_commitment': 'off-time',
        'work_mode': 'pre-staged-speculative',
        'sales_channels_json': json.dumps(
            ['online', 'farmer-market', 'maker-market']),
        'sourcing_posture': 'retail-available',
        'capabilities_json': json.dumps(['wax-printing',
                                         'geopolymer-casting']),
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': 'THE AXIOM: every business starts as one person '
                 'buying whatever is available, selling only in '
                 'off-time — online or at farmer/maker markets. '
                 'WORK MODE pre-staged: produce what you can '
                 'afford with what you have, TRY DIFFERENT '
                 'products, then try to sell them — unsold '
                 'stock is the tuition, MarketSessionRecord '
                 'rows are the learning.',
    },
    {
        'name': 'stage-1-solo-committed',
        'stage_index': 1,
        'display_name': 'Solo, committed hours',
        'headcount': 1, 'weekly_hours': 25.0,
        'time_commitment': 'part-time',
        'work_mode': 'mixed',
        'sales_channels_json': json.dumps(
            ['online', 'farmer-market', 'maker-market',
             'standing-orders']),
        'sourcing_posture': 'bulk',
        'capabilities_json': json.dumps(['wax-printing',
                                         'geopolymer-casting']),
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': 'Same person, real hours; sourcing flips to bulk '
                 'tiers (the 40-bag metakaolin tier becomes real).',
    },
    {
        'name': 'stage-2-plus-one',
        'stage_index': 2,
        'display_name': 'Plus one hire on a task',
        'headcount': 2, 'weekly_hours': 55.0,
        'time_commitment': 'part-time',
        'work_mode': 'order-driven',
        'sales_channels_json': json.dumps(
            ['online', 'farmer-market', 'maker-market',
             'standing-orders', 'local-retail']),
        'sourcing_posture': 'local-partners',
        'capabilities_json': json.dumps(['wax-printing',
                                         'geopolymer-casting']),
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': 'One more person ON A TASK (casting, finishing, '
                 'or market days) — the upgrade flow names the '
                 'task, never a vague hire.',
    },
    {
        'name': 'stage-3-capability-shop',
        'stage_index': 3,
        'display_name': 'Capability shop (kiln, reclaim, partners)',
        'headcount': 2, 'weekly_hours': 70.0,
        'time_commitment': 'full-time-mixed',
        'work_mode': 'order-driven',
        'sales_channels_json': json.dumps(
            ['online', 'standing-orders', 'local-retail',
             'wholesale']),
        'sourcing_posture': 'self-made-intermediaries',
        'capabilities_json': json.dumps(
            ['wax-printing', 'geopolymer-casting',
             'wax-reclaim-loop', 'ceramic-firing',
             'waterglass-production']),
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': 'The cascaded-cost stack running for real: '
                 'self-made waterglass/metakaolin, reclaim loops, '
                 'fired ceramic molds.',
    },
]

SEED_BUSINESS_UPGRADES = [
    {
        'name': 'commit-hours',
        'display_name': 'Commit real hours (0 -> 1)',
        'from_stage': 'stage-0-solo-offtime',
        'to_stage': 'stage-1-solo-committed',
        'kind': 'process-change', 'role_or_capability': '',
        'evidence_gate': 'order backlog exceeds off-time capacity '
                         'in two consecutive plans AND margin per '
                         'hour beats the off-time wage floor',
        'effects_json': json.dumps({'weekly_hours_delta': 15.0}),
        'is_prior': True, 'provenance_id': 'biz-1', 'notes': '',
    },
    {
        'name': 'adopt-wax-reclaim-loop',
        'display_name': 'Adopt the wax reclaim loop',
        'from_stage': '', 'to_stage': '',
        'kind': 'process-change',
        'role_or_capability': 'wax-reclaim-loop',
        'evidence_gate': 'monthly mold count makes the ~84% '
                         'per-mold wax saving exceed the wash/'
                         'filter time cost',
        'effects_json': json.dumps(
            {'capabilities_added': ['wax-reclaim-loop']}),
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': 'Ties to reclaim_analysis — the planner prices '
                 'wax at makeup-only once this capability is on.',
    },
    {
        'name': 'hire-caster',
        'display_name': 'Hire one person onto casting',
        'from_stage': 'stage-1-solo-committed',
        'to_stage': 'stage-2-plus-one',
        'kind': 'hire-role', 'role_or_capability': 'caster',
        'evidence_gate': 'plan shows casting hours > half of total '
                         'hours AND deferred orders carry more '
                         'margin than the hire costs',
        'effects_json': json.dumps({'weekly_hours_delta': 30.0}),
        'is_prior': True, 'provenance_id': 'biz-1', 'notes': '',
    },
    {
        'name': 'add-ceramic-firing',
        'display_name': 'Add ceramic firing (kiln)',
        'from_stage': 'stage-2-plus-one',
        'to_stage': 'stage-3-capability-shop',
        'kind': 'add-capability',
        'role_or_capability': 'ceramic-firing',
        'evidence_gate': 'repeat-order volume per size rung '
                         'exceeds the ceramic-mold crossover in '
                         'the mold strategy comparison',
        'effects_json': json.dumps(
            {'capabilities_added': ['ceramic-firing'],
             'weekly_hours_delta': 15.0}),
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': 'The Table 8.8 upgrade path becomes a business '
                 'step: fire geopolymer molds into ceramic molds.',
    },
    {
        'name': 'add-waterglass-production',
        'display_name': 'Make waterglass in-house',
        'from_stage': '', 'to_stage': '',
        'kind': 'add-capability',
        'role_or_capability': 'waterglass-production',
        'evidence_gate': 'monthly waterglass consumption makes the '
                         'make-vs-buy gap (1.54 vs 8.85/kg) exceed '
                         'the digestion labor',
        'effects_json': json.dumps(
            {'capabilities_added': ['waterglass-production']}),
        'is_prior': True, 'provenance_id': 'biz-1', 'notes': '',
    },
]

SEED_BUSINESS_PROFILES = [
    {
        'name': 'wax-mold-goods',
        'display_name': 'Wax-Mold Goods (the live micro-business)',
        'business_model_ref': 'wax-mold-goods-microbusiness',
        'current_stage': 'stage-0-solo-offtime',
        'headcount': 1, 'weekly_hours': 10.0,
        'capabilities_json': json.dumps(['wax-printing',
                                         'geopolymer-casting']),
        'region_note': 'local',
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': 'Starts AT the axiom: one person, off-time, '
                 'markets + online, buying retail-available.',
    },
]

SEED_ECONOMY_MILESTONES = [
    {'name': 'ms-local-wax-feedstock', 'track_order': 1,
     'display_name': 'Local wax-source feedstock',
     'kind': 'local-available-source-for',
     'target_ref': 'wax-source-biomass',
     'description': 'A LOCAL AVAILABLE source supplies the wax '
                    'feedstock (the hydroponic farm turning real).',
     'is_prior': True, 'provenance_id': 'biz-1', 'notes': ''},
    {'name': 'ms-waterglass-makeable', 'track_order': 2,
     'display_name': 'Waterglass makeable in-economy',
     'kind': 'makeable-intermediary',
     'target_ref': 'sodium-silicate-solution',
     'description': 'The critical intermediary has a working local '
                    'recipe.', 'is_prior': True,
     'provenance_id': 'biz-1', 'notes': ''},
    {'name': 'ms-metakaolin-makeable', 'track_order': 3,
     'display_name': 'Metakaolin makeable in-economy',
     'kind': 'makeable-intermediary', 'target_ref': 'metakaolin',
     'description': 'Precursor calcined locally from raw kaolin.',
     'is_prior': True, 'provenance_id': 'biz-1', 'notes': ''},
    {'name': 'ms-first-business-committed', 'track_order': 4,
     'display_name': 'First business past the origin stage',
     'kind': 'business-at-stage', 'target_ref': '1',
     'description': 'At least one BusinessProfile beyond '
                    'stage-0 (real committed hours).',
     'is_prior': True, 'provenance_id': 'biz-1', 'notes': ''},
    {'name': 'ms-mutual-loop', 'track_order': 5,
     'display_name': 'A mutual supply loop exists',
     'kind': 'mutual-loop-exists', 'target_ref': '',
     'description': 'Some source both SUPPLIES and DEMANDS across '
                    'the economy (farm <-> goods maker).',
     'is_prior': True, 'provenance_id': 'biz-1', 'notes': ''},
    {'name': 'ms-reclaim-running', 'track_order': 6,
     'display_name': 'Material reclaim physically running',
     'kind': 'reclaim-active', 'target_ref': '',
     'description': 'WaxReclaimBatch rows exist — loops are real, '
                    'not planned.', 'is_prior': True,
     'provenance_id': 'biz-1', 'notes': ''},
    {'name': 'ms-crush-loop-logged', 'track_order': 7,
     'display_name': 'Mold crush-recycle logged',
     'kind': 'crush-loop-logged', 'target_ref': '',
     'description': 'Retired molds measurably re-entered new '
                    'geopolymer.', 'is_prior': True,
     'provenance_id': 'biz-1', 'notes': ''},
    {'name': 'ms-second-business', 'track_order': 8,
     'display_name': 'A second local business profile',
     'kind': 'business-count', 'target_ref': '2',
     'description': 'The economy has more than one modeled '
                    'business (e.g. the farm incorporates).',
     'is_prior': True, 'provenance_id': 'biz-1', 'notes': ''},
]

SEED_PROCESS_WORKFLOWS = [
    {
        'name': 'wax-mold-print-workflow',
        'display_name': 'Print a wax mold',
        'product_item_ref': 'wax-mold',
        'mold_strategy': 'wax-printed',
        'hours_per_unit_ref': 0.0, 'hours_per_mold_ref': 2.0,
        'passive_hours_per_batch': 0.0,
        'volume_exponent': 0.667,
        'steps_json': json.dumps(
            ['slice/setup', 'print (attended fraction)',
             'inspect']),
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': 'HOUR PRIORS ARE ESTIMATES until timed runs '
                 'replace them (2.0 attended h per 1 L-class '
                 'mold).',
    },
    {
        'name': 'geopolymer-cast-workflow',
        'display_name': 'Cast geopolymer in a wax mold',
        'product_item_ref': 'geopolymer-mix',
        'mold_strategy': 'wax-printed',
        'hours_per_unit_ref': 0.8, 'hours_per_mold_ref': 0.0,
        'passive_hours_per_batch': 24.0,
        'volume_exponent': 0.667,
        'steps_json': json.dumps(
            ['mix', 'pour', 'cure (passive 24h)',
             'demold/melt-off', 'finish']),
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': '0.8 attended h/unit at 1 L; cure is passive — '
                 'it gates calendar throughput, not labor.',
    },
    {
        'name': 'ceramic-mold-from-master-workflow',
        'display_name': 'Ceramic mold from a wax master',
        'product_item_ref': 'ceramic-mold',
        'mold_strategy': 'ceramic-fired',
        'hours_per_unit_ref': 0.0, 'hours_per_mold_ref': 3.5,
        'passive_hours_per_batch': 12.0,
        'volume_exponent': 0.667,
        'steps_json': json.dumps(
            ['cast geopolymer mold from wax master',
             'cure (passive)', 'fire (kiln, passive)',
             'inspect/fit']),
        'is_prior': True, 'provenance_id': 'biz-1',
        'notes': 'Needs the ceramic-firing capability; kiln energy '
                 'excluded from cost v1 (the sintering engine can '
                 'cost schedules later).',
    },
]
