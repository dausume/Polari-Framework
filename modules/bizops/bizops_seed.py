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

SEED_RISK_NOTES = [
    {'name': 'risk-naoh-caustic', 'step_ref': 'buy-materials',
     'severity': 'safety-critical',
     'risk': 'Sodium hydroxide (lye) is CAUSTIC — burns skin and '
             'eyes; the waterglass digestion and geopolymer alkali '
             'both use it.',
     'mitigation': 'Gloves + goggles ALWAYS; add lye to water '
                   'never water to lye; keep vinegar nearby to '
                   'neutralize splashes.',
     'is_prior': True, 'provenance_id': 'biz-3', 'notes': ''},
    {'name': 'risk-alkaline-mix', 'step_ref': 'first-batch',
     'severity': 'high',
     'risk': 'Fresh geopolymer paste is strongly alkaline — skin '
             'contact causes chemical burns over minutes, like wet '
             'cement.',
     'mitigation': 'Nitrile gloves, long sleeves, wash splashes '
                   'immediately; cured pieces are safe to handle.',
     'is_prior': True, 'provenance_id': 'biz-3', 'notes': ''},
    {'name': 'risk-hot-wax', 'step_ref': 'first-batch',
     'severity': 'high',
     'risk': 'Melted wax burns and can ignite if overheated; even '
             'natural blends fume near their safety ceiling.',
     'mitigation': 'Respect the feedstock safe_melt_max (the print '
                   'gate enforces it); ventilate; never leave melts '
                   'unattended.',
     'is_prior': True, 'provenance_id': 'biz-3', 'notes': ''},
    {'name': 'risk-unsold-stock', 'step_ref': 'sell-and-log',
     'severity': 'medium',
     'risk': 'Stage-0 batches are SPECULATIVE — some products will '
             'not sell and that money is spent.',
     'mitigation': 'Keep batches small, vary products, log every '
                   'session so the next batch learns; unsold stock '
                   'is tuition, budget it as such.',
     'is_prior': True, 'provenance_id': 'biz-3', 'notes': ''},
    {'name': 'risk-price-drift', 'step_ref': 'buy-materials',
     'severity': 'medium',
     'risk': 'Several cited prices are FLAGGED estimates and '
             'marketplace prices swing; your real receipt may '
             'differ.',
     'mitigation': 'Re-cite with your actual receipts (screenshots '
                   'count); the drift checker flags divergence.',
     'is_prior': True, 'provenance_id': 'biz-3', 'notes': ''},
    {'name': 'risk-overpromise', 'step_ref': 'step-up',
     'severity': 'high',
     'risk': 'Taking advance orders before you have measured your '
             'own speed leads to broken promises.',
     'mitigation': 'The readiness ladder gates quoting on made+'
                   'sold+timed for a reason — do not shortcut it.',
     'is_prior': True, 'provenance_id': 'biz-3', 'notes': ''},
    {'name': 'risk-burnout', 'step_ref': 'step-up',
     'severity': 'medium',
     'risk': 'Off-time hours are real hours from your life; '
             'committing more (stage 1) trades rest for growth.',
     'mitigation': 'Take commit-hours only when its evidence gate '
                   'holds two plans running — not on one good '
                   'market day.',
     'is_prior': True, 'provenance_id': 'biz-3', 'notes': ''},
    {'name': 'risk-not-food-safe', 'step_ref': 'sell-and-log',
     'severity': 'high',
     'risk': 'Geopolymer planters/vases are NOT food-contact '
             'vessels — no food-safety claim exists anywhere in '
             'this stack.',
     'mitigation': 'Say so on the stall card; sell as planters and '
                   'decor until testing ever says otherwise.',
     'is_prior': True, 'provenance_id': 'biz-3', 'notes': ''},
]

SEED_PARTNERSHIPS = [
    {
        'name': 'deal-rice-husk-supply',
        'display_name': 'Rice husk/ash supply deal (partner to be '
                        'found)',
        'party_a': 'local-rice-mill (to be found)',
        'party_b': 'wax-mold-goods',
        'kind': 'supply-deal',
        'flows_json': json.dumps([
            {'from': 'local-rice-mill (to be found)',
             'to': 'wax-mold-goods', 'item_ref': 'rice-hulls',
             'terms_note': 'mill waste, near-free vs the $30/50lb '
                           'homebrew channel — haul-it-yourself is '
                           'the usual term'}]),
        'terms_note': 'The husk->RHA->waterglass chain is what this '
                      'unlocks at real prices.',
        'status': 'proposed',
        'is_prior': True, 'provenance_id': 'biz-3',
        'notes': 'The archetype local-byproduct deal — same shape '
                 'works for fly ash (ready-mix plant) and bagasse '
                 '(sugar mill).',
    },
    {
        'name': 'deal-hydro-mold-loop',
        'display_name': 'Hydroponic farm <-> mold-goods mutual deal',
        'party_a': 'local-hydroponics-farm',
        'party_b': 'wax-mold-goods',
        'kind': 'mutual-supply',
        'flows_json': json.dumps([
            {'from': 'local-hydroponics-farm',
             'to': 'wax-mold-goods',
             'item_ref': 'wax-source-biomass',
             'alternative_item_ref': 'soy-wax',
             'terms_note': 'transfer price 3.50/kg (scenario-2 '
                           'seed; price discovery ongoing — '
                           'buyer\'s alternative is commercial '
                           'soy wax)'},
            {'from': 'wax-mold-goods',
             'to': 'local-hydroponics-farm',
             'item_ref': 'geopolymer-self-watering-pot',
             'terms_note': '18.00/unit; shelving to follow'}]),
        'terms_note': 'The scenario-2 mutual loop as an actual '
                      'agreement row.',
        'status': 'proposed',
        'is_prior': True, 'provenance_id': 'biz-3', 'notes': '',
    },
    {
        'name': 'deal-printer-maintenance',
        'display_name': '3D-printer makers <-> assemblers '
                        'maintenance + scaling deal',
        'party_a': 'printer-maker-collective (to be found)',
        'party_b': 'printer-assembler-group (to be found)',
        'kind': 'service-maintenance',
        'flows_json': json.dumps([
            {'from': 'printer-assembler-group (to be found)',
             'to': 'printer-maker-collective (to be found)',
             'item_ref': 'printer-maintenance-service',
             'terms_note': 'maintain fielded wax printers; parts '
                           'from the makers'},
            {'from': 'printer-maker-collective (to be found)',
             'to': 'printer-assembler-group (to be found)',
             'item_ref': 'printer-kits',
             'terms_note': 'kits + training; assemblers scale '
                           'other operations as demand needs'}]),
        'terms_note': 'The capacity-scaling archetype: makers make, '
                      'assemblers maintain and flex.',
        'status': 'proposed',
        'is_prior': True, 'provenance_id': 'biz-3',
        'notes': 'Both parties are placeholders — the deal SHAPE '
                 'is the seed; the open-hardware wax printer work '
                 'is where these groups come from.',
    },
]

SEED_COMPLIANCE_REQUIREMENTS = [
    {'name': 'req-food-contact', 'display_name': 'Food-contact '
     'safety (the hard one)', 'kind': 'legal-mandatory',
     'applies_context': 'sold-as-food-contact',
     'required_level': 'certified-third-party-pass',
     'requirement': 'A product sold for food contact must meet '
                    'food-contact-substance rules — NOTHING in this '
                    'stack may be sold as food safe without '
                    'CERTIFIED third-party testing, period.',
     'reference_note': 'US: FDA 21 CFR (food contact substances); '
                       'EU: 1935/2004. NOT LEGAL ADVICE — verify '
                       'for your jurisdiction.',
     'is_prior': True, 'provenance_id': 'biz-4',
     'notes': 'Geopolymer planters/vases are NOT food vessels '
              'until this is certified — the stall card says so.'},
    {'name': 'req-honest-labeling', 'display_name': 'Honest '
     'labeling / no false claims', 'kind': 'legal-mandatory',
     'applies_context': 'general-goods',
     'required_level': 'self-test-pass',
     'requirement': 'Describe materials honestly, make no unproven '
                    'claims (food-safe, frost-proof, load ratings) '
                    '— self-test-pass = your label template audited '
                    'against what the rows actually prove.',
     'reference_note': 'US FTC Act §5 (deceptive practices). NOT '
                       'LEGAL ADVICE.',
     'is_prior': True, 'provenance_id': 'biz-4', 'notes': ''},
    {'name': 'req-business-license', 'display_name': 'Business '
     'license + sales tax registration',
     'kind': 'legal-mandatory', 'applies_context': 'general-goods',
     'required_level': 'self-test-pass',
     'requirement': 'Local business license (or cottage/hobby '
                    'exemption verified) + sales tax collection '
                    'registered where required.',
     'reference_note': 'Varies by city/county/state. NOT LEGAL '
                       'ADVICE — one call to your county clerk '
                       'answers it.',
     'is_prior': True, 'provenance_id': 'biz-4', 'notes': ''},
    {'name': 'req-market-vendor-rules', 'display_name': 'Market '
     'vendor rules (fees, insurance)', 'kind': 'market-rule',
     'applies_context': 'farmer-maker-markets',
     'required_level': 'self-test-pass',
     'requirement': 'Each market sets vendor fees, sometimes '
                    'liability insurance; confirm per market '
                    'before booking a table.',
     'reference_note': 'Ask the market organizer.',
     'is_prior': True, 'provenance_id': 'biz-4', 'notes': ''},
    {'name': 'req-childrens-product', 'display_name': 'Children\'s '
     'product testing (CPSIA)', 'kind': 'legal-mandatory',
     'applies_context': 'marketed-for-children',
     'required_level': 'certified-third-party-pass',
     'requirement': 'Anything MARKETED for children needs '
                    'third-party CPSC-accepted testing — do not '
                    'market these goods for children.',
     'reference_note': 'US CPSIA. NOT LEGAL ADVICE.',
     'is_prior': True, 'provenance_id': 'biz-4', 'notes': ''},
    {'name': 'req-plant-safe-claim', 'display_name': 'Plant-safe '
     'claim (leachate pH)', 'kind': 'voluntary-standard',
     'applies_context': 'sold-as-plant-safe',
     'required_level': 'self-test-pass',
     'requirement': 'Fresh geopolymer can leach alkalinity into '
                    'soil at first — claim plant-safe only after '
                    'a soak + leachate pH self-test passes '
                    '(red-cabbage/strip from the research-tools '
                    'tree is enough).',
     'reference_note': 'Internal standard — the honest-claims '
                       'principle applied to planters.',
     'is_prior': True, 'provenance_id': 'biz-4', 'notes': ''},
]

SEED_QUALITY_CHECKS = [
    {'name': 'qa-visual-crack', 'display_name': 'Visual crack + '
     'edge inspection', 'product_kind': 'geopolymer-cast',
     'method': 'eyes + raking light; tap test for dull ring',
     'acceptance': 'no through-cracks, no crumbling edges',
     'frequency': 'every-unit', 'is_prior': True,
     'provenance_id': 'biz-4', 'notes': ''},
    {'name': 'qa-dimensional-fit', 'display_name': 'Dimensional '
     'fit vs the mold spec', 'product_kind': 'geopolymer-cast',
     'method': 'calipers on 3 axes vs mold nominal',
     'acceptance': 'within ±2% (shrinkage drift flags the mix)',
     'frequency': 'per-batch', 'is_prior': True,
     'provenance_id': 'biz-4', 'notes': ''},
    {'name': 'qa-water-tightness', 'display_name': 'Water '
     'tightness (planters)', 'product_kind': 'geopolymer-cast',
     'method': 'fill, stand 24h on dry paper',
     'acceptance': 'no weep-through (drain holes excepted)',
     'frequency': 'per-batch', 'is_prior': True,
     'provenance_id': 'biz-4', 'notes': ''},
    {'name': 'qa-cure-hardness', 'display_name': 'Cure hardness '
     'scratch test', 'product_kind': 'geopolymer-cast',
     'method': 'Mohs pick or nail scratch on the foot',
     'acceptance': 'no gouging at nail hardness after full cure',
     'frequency': 'per-batch', 'is_prior': True,
     'provenance_id': 'biz-4', 'notes': ''},
    {'name': 'qa-leachate-ph', 'display_name': 'Leachate pH '
     '(plant-safe gate)', 'product_kind': 'geopolymer-cast',
     'method': '24h soak, test the water (red-cabbage/strip)',
     'acceptance': 'pH <= 9 after soak (else keep curing/rinsing)',
     'frequency': 'per-batch', 'is_prior': True,
     'provenance_id': 'biz-4',
     'notes': 'The evidence row behind req-plant-safe-claim.'},
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
