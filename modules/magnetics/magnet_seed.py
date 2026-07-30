"""
@module magnetics.magnet_seed

Section-A seeds: the mag-2r role vocabulary (predicates as knobs,
honesty notes that travel) and the §1c option catalog with
realization levels + per-value provenance. Property numbers tagged
'literature-est' are literature-order values, not ours; 'measured'
appears only when OUR rows exist (none yet — honestly).

Composite mu_eff values reference the msci-22 FEM results
(geopolymer-ferrite 2.196 @35vol%, sol-gel-ferrite 1.714 @25vol%,
ferrite-ceramic 2.484 @40vol%) — provenance 'literature-est' would
be wrong for those: they are OUR simulation outputs, tagged
'simulated' in the note but carried as literature-est-grade evidence
(not measurements) for viability purposes.

@consumers polariServer seed_pairs
"""

import json

PROV = 'mag-2'


def _props(**kwargs):
    """properties_json shorthand: prop=(value, unit, provenance[,
    note])."""
    out = {}
    for prop, spec in kwargs.items():
        value, unit, provenance = spec[0], spec[1], spec[2]
        entry = {'value': value, 'unit': unit,
                 'provenance': provenance}
        if len(spec) > 3:
            entry['note'] = spec[3]
        out[prop] = entry
    return json.dumps(out)


SEED_USE_ROLES = [
    {
        'name': 'electric-conductor-power',
        'display_name': 'Electric conductor — POWER grade',
        'description': 'Carries winding current. Copper-class '
                       'conductivity required; today only magnet '
                       'wire qualifies.',
        'predicates_json': json.dumps({'all': [
            {'prop': 'sigma_s_m', 'op': '>=', 'value': 1.0e7}]}),
        'applicable_forms_json': json.dumps(['wire']),
        'honesty_note': '',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Threshold 1e7 S/m (copper 5.96e7, aluminum '
                 '3.5e7) — an editable knob, not physics.',
    },
    {
        'name': 'electric-conductor-signal',
        'display_name': 'Electric conductor — SIGNAL grade',
        'description': 'Carries signals/sensing through the matrix; '
                       'percolated-composite territory.',
        'predicates_json': json.dumps({'all': [
            {'prop': 'sigma_s_m', 'op': '>=', 'value': 10.0}]}),
        'applicable_forms_json': json.dumps(
            ['trace', 'mortar', 'castable-block', 'wire']),
        'honesty_note': 'Composite conduction sits ~5 orders below '
                        'copper (227 S/m vs 6e7) — signals, '
                        'shielding, static dissipation; NEVER power '
                        'windings, NOT induction cages until a '
                        'measured row says otherwise.',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'magnetic-conductor',
        'display_name': 'Magnetic conductor (soft flux guide)',
        'description': 'Guides flux: min effective permeability, '
                       'LOW coercivity (soft).',
        'predicates_json': json.dumps({'all': [
            {'prop': 'mu_r_eff', 'op': '>=', 'value': 1.5},
            {'prop': 'h_c_ka_m', 'op': '<=', 'value': 20.0}]}),
        'applicable_forms_json': json.dumps(
            ['castable-block', 'mortar', 'powder', 'sintered-part']),
        'honesty_note': 'Our cast composites run mu ~1.7-2.5 — '
                        'air-gap-dominated parts yes, motor iron '
                        'no (laminated steel runs 1e3-1e4).',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'mu>=1.5 admits the cast composites BY DESIGN — '
                 'the honesty note carries the caveat; raise the '
                 'knob to exclude them.',
    },
    {
        'name': 'torque-magnet',
        'display_name': 'Torque magnet (hard PM doing work)',
        'description': 'Permanent magnet producing usable torque: '
                       'min remanence AND min coercivity.',
        'predicates_json': json.dumps({'all': [
            {'prop': 'b_r_t', 'op': '>=', 'value': 0.1},
            {'prop': 'h_c_ka_m', 'op': '>=', 'value': 100.0}]}),
        'applicable_forms_json': json.dumps(
            ['sintered-part', 'castable-block', 'powder']),
        'honesty_note': 'Magnetite FAILS this predicate (soft) — '
                        'the taxonomy itself enforces the '
                        'soft/hard split.',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'flux-containment',
        'display_name': 'Flux containment (shunt OR fence)',
        'description': 'Keeps stray flux where it belongs — two '
                       'REAL mechanisms, the matched one is tagged '
                       'on every verdict.',
        'predicates_json': json.dumps({'any': [
            {'mechanism': 'high-mu-shunt', 'all': [
                {'prop': 'mu_r_eff', 'op': '>=', 'value': 1.5}]},
            {'mechanism': 'non-magnetic-fence', 'all': [
                {'prop': 'mu_r_eff', 'op': '<=', 'value': 1.1}]},
        ]}),
        'applicable_forms_json': json.dumps(
            ['castable-block', 'mortar', 'sintered-part']),
        'honesty_note': 'A shunt ROUTES stray flux (higher mu than '
                        'surroundings); a fence bounds it (mu~1 '
                        'boundary courses). Both viable; pick by '
                        'geometry.',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'structural-containment',
        'display_name': 'Structural containment (rotor safety)',
        'description': 'Physically contains the spinning rotor — '
                       'needs strength/toughness data.',
        'predicates_json': json.dumps({'all': [
            {'prop': 'tensile_mpa', 'op': '>=', 'value': 5.0}]}),
        'applicable_forms_json': json.dumps(
            ['castable-block', 'sintered-part']),
        'honesty_note': 'Most rows lack mechanical data — they '
                        'stay UNASSESSED until it exists; nothing '
                        'is assumed strong.',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'magnetic-bearing',
        'display_name': 'Magnetic bearing (PM centering)',
        'description': 'PM rings holding the rotor centered.',
        'predicates_json': json.dumps({'all': [
            {'prop': 'b_r_t', 'op': '>=', 'value': 0.2},
            {'prop': 'h_c_ka_m', 'op': '>=', 'value': 150.0}]}),
        'applicable_forms_json': json.dumps(
            ['sintered-part', 'castable-block']),
        'honesty_note': 'EARNSHAW (theorem, not opinion): passive '
                        'PM levitation is unstable in at least one '
                        'axis. Real designs center radially with PM '
                        'rings and constrain ONE axis mechanically '
                        '(jewel/pin point contact) or with active/'
                        'diamagnetic assist. The role is viable; '
                        '"fully floating passive" is not.',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'in-matrix-sensing',
        'display_name': 'In-matrix sensing (cast-in electrodes)',
        'description': 'Sensing electrodes/traces cast into blocks '
                       'or carried by the mortar.',
        'predicates_json': json.dumps({'all': [
            {'prop': 'sigma_s_m', 'op': '>=', 'value': 1.0},
            {'prop': 'sigma_s_m', 'op': '<=', 'value': 1.0e5}]}),
        'applicable_forms_json': json.dumps(
            ['trace', 'mortar', 'castable-block']),
        'honesty_note': 'The near-term ferrite-CNT win: sensor '
                        'wiring disappears into the matrix. Signal '
                        'band only — the copper gap prints on '
                        'every report.',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'potting-encapsulant',
        'display_name': 'Potting / encapsulant (winding pot)',
        'description': 'Encapsulates windings into the monolith '
                       '(§2b) — electrically insulating.',
        'predicates_json': json.dumps({'all': [
            {'prop': 'sigma_s_m', 'op': '<=', 'value': 1.0e-3}]}),
        'applicable_forms_json': json.dumps(['potting', 'mortar']),
        'honesty_note': 'Enamel magnet-wire vs ALKALINE geopolymer '
                        'contact = chemistry compatibility UNKNOWN '
                        '(a QA check row, not an assumption); '
                        'washed near-neutral sol-gel is the safer '
                        'potting bet.',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
    {
        'name': 'mortar-joint',
        'display_name': 'Mortar joint (block-to-block)',
        'description': 'Fills the joints of the §2b monolith; '
                       'magnetic grade for flux continuity, plain '
                       'grade as a deliberate gap.',
        'predicates_json': json.dumps({'any': [
            {'mechanism': 'flux-continuity', 'all': [
                {'prop': 'mu_r_eff', 'op': '>=', 'value': 1.5}]},
            {'mechanism': 'deliberate-gap', 'all': [
                {'prop': 'mu_r_eff', 'op': '<=', 'value': 1.1}]},
        ]}),
        'applicable_forms_json': json.dumps(['mortar']),
        'honesty_note': 'Every joint IS a circuit element (thin '
                        'series reluctance) — the mortar grade per '
                        'joint is a DESIGN knob the solver prices.',
        'is_prior': True, 'provenance_id': PROV, 'notes': '',
    },
]


SEED_MAGNETIC_POWDERS = [
    # --- real powders (item_refs tie into the mag-1 citations) ---
    {
        'name': 'magnetite-powder-def',
        'display_name': 'Magnetite (Fe3O4) pigment powder',
        'is_theoretical': False, 'item_ref': 'magnetite-powder',
        'mu_i': 70.0, 'b_sat_t': 0.60, 'h_c_ka_m': 8.0,
        'b_r_t': 0.02, 'density_kg_m3': 5200.0,
        'particle_size_um': 5.0, 'sigma_s_m': 2.5e4,
        'property_provenance': 'literature-est',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Soft-ish oxide; mu_i literature scatter is WIDE '
                 '(20-100s, grain/size dependent). CONDUCTIVE '
                 '(half-metal ~2.5e4 S/m) — eddy/percolation '
                 'caveat for AC use, msci-23 covers the axis.',
    },
    {
        'name': 'carbonyl-iron-powder-def',
        'display_name': 'Carbonyl iron powder',
        'is_theoretical': False, 'item_ref': 'carbonyl-iron-powder',
        'mu_i': 100.0, 'b_sat_t': 2.15, 'h_c_ka_m': 0.3,
        'b_r_t': 0.005, 'density_kg_m3': 7860.0,
        'particle_size_um': 5.0, 'sigma_s_m': 1.0e7,
        'property_provenance': 'literature-est',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Commercial powdered-iron cores ARE this + binder; '
                 'highest B_sat of our cheap fillers — likely best '
                 'core filler. Metallic conductivity mandates '
                 'insulated particles (the binder does it).',
    },
    {
        'name': 'srfe12o19-powder-def',
        'display_name': 'Strontium hexaferrite (SrFe12O19) powder',
        'is_theoretical': False, 'item_ref': 'srfe12o19-powder',
        'mu_i': 1.3, 'b_sat_t': 0.45, 'h_c_ka_m': 250.0,
        'b_r_t': 0.40, 'density_kg_m3': 5100.0,
        'particle_size_um': 1.5, 'sigma_s_m': 1.0e-6,
        'property_provenance': 'literature-est',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'THE local hard magnet (§1b Rung 1). B_r 0.40 is '
                 'the SINTERED literature order; bonded isotropic '
                 'lands ~0.2. Insulating — no eddy caveat.',
    },
    {
        'name': 'nizn-ferrite-powder-def',
        'display_name': 'NiZn soft-ferrite powder',
        'is_theoretical': False, 'item_ref': 'mnzn-ferrite-powder',
        'mu_i': 200.0, 'b_sat_t': 0.33, 'h_c_ka_m': 1.0,
        'b_r_t': 0.01, 'density_kg_m3': 5300.0,
        'particle_size_um': 1.0, 'sigma_s_m': 1.0e-3,
        'property_provenance': 'literature-est',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Insulating high-frequency soft ferrite; sol-gel '
                 'synthesis route exists in literature (our stack '
                 'could make it — an uncited candidate recipe).',
    },
    {
        'name': 'mnzn-ferrite-powder-def',
        'display_name': 'MnZn soft-ferrite powder',
        'is_theoretical': False, 'item_ref': 'mnzn-ferrite-powder',
        'mu_i': 800.0, 'b_sat_t': 0.45, 'h_c_ka_m': 0.5,
        'b_r_t': 0.01, 'density_kg_m3': 4900.0,
        'particle_size_um': 50.0, 'sigma_s_m': 1.0,
        'property_provenance': 'literature-est',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Higher mu, lower frequency; the msci FEM rows use '
                 'mu 800 as the literature-order inclusion value — '
                 'THIS row is that number\'s home.',
    },
    # --- theoretical powders (mag-2t watermarked hypotheses) ---
    {
        'name': 'fe16n2-theoretical',
        'display_name': "α″-Fe16N2 (theoretical here; Niron-class)",
        'is_theoretical': True, 'item_ref': '',
        'mu_i': 1.5, 'b_sat_t': 2.9, 'h_c_ka_m': 190.0,
        'b_r_t': 1.0, 'density_kg_m3': 7200.0,
        'particle_size_um': 0.05, 'sigma_s_m': 1.0e6,
        'property_provenance': 'theoretical',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Iron + ammonia-derived nitrogen, ~150-200C '
                 'nitriding — the flagship proof nanostructure '
                 'physics can beat rare elements (actively '
                 'commercialized by others). Metastable nanoscale '
                 'control = the hard part. SIMULATION-ONLY here.',
    },
    {
        'name': 'exchange-spring-theoretical',
        'display_name': 'Exchange-spring hexaferrite/magnetite '
                        'nanocomposite (theoretical)',
        'is_theoretical': True, 'item_ref': '',
        'mu_i': 1.4, 'b_sat_t': 0.8, 'h_c_ka_m': 180.0,
        'b_r_t': 0.55, 'density_kg_m3': 5150.0,
        'particle_size_um': 0.01, 'sigma_s_m': 1.0e-2,
        'property_provenance': 'theoretical',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Hard+soft coupled at ~10 nm — the sol-gel '
                 'toolkit\'s long-run target. L4-CLASS GAP flagged: '
                 'true exchange coupling is beyond mean-field '
                 'homogenization; these numbers are aspiration '
                 'bookkeeping, not predictions.',
    },
]


SEED_MATERIAL_OPTIONS = [
    # ---------------- SOFT MAGNETIC ---------------- #
    {
        'name': 'opt-magnetite-powder',
        'display_name': 'Magnetite powder (Fe3O4)',
        'family': 'soft-magnetic',
        'realization_level': 'recipe-seeded',
        'item_ref': 'magnetite-powder',
        'msci_material_ref': '',
        'powder_ref': 'magnetite-powder-def',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            mu_r_eff=(70.0, '', 'literature-est',
                      'intrinsic powder value — composites land '
                      'far lower'),
            b_sat_t=(0.60, 'T', 'literature-est'),
            h_c_ka_m=(8.0, 'kA/m', 'literature-est'),
            b_r_t=(0.02, 'T', 'literature-est'),
            density_kg_m3=(5200.0, 'kg/m3', 'vendor'),
            sigma_s_m=(2.5e4, 'S/m', 'literature-est')),
        'role_overrides_json': '{}',
        'is_reference_only': False,
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Buy 9.70/kg beats make 20.11 (src-6/7) — cited '
                 'AND recipe-seeded.',
    },
    {
        'name': 'opt-carbonyl-iron',
        'display_name': 'Carbonyl/atomized iron powder',
        'family': 'soft-magnetic',
        'realization_level': 'literature-demonstrated',
        'item_ref': 'carbonyl-iron-powder',
        'powder_ref': 'carbonyl-iron-powder-def',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            mu_r_eff=(100.0, '', 'literature-est'),
            b_sat_t=(2.15, 'T', 'literature-est'),
            h_c_ka_m=(0.3, 'kA/m', 'literature-est'),
            b_r_t=(0.005, 'T', 'literature-est'),
            density_kg_m3=(7860.0, 'kg/m3', 'vendor'),
            sigma_s_m=(1.0e7, 'S/m', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Commercial powdered-iron cores ARE this + '
                 'binder; highest B_sat cheap filler (mag-1 cite '
                 '86/kg small-lot, out-of-stock at observation).',
    },
    {
        'name': 'opt-maghemite',
        'display_name': 'Maghemite (γ-Fe2O3)',
        'family': 'soft-magnetic',
        'realization_level': 'literature-demonstrated',
        'item_ref': '', 'powder_ref': '',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            b_sat_t=(0.39, 'T', 'literature-est'),
            density_kg_m3=(4900.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Magnetite oxidation product; ACICULAR particles '
                 '= semi-hard (recording-tape physics), equiaxed = '
                 'soft. mu/H_c honestly unassessed until a shape '
                 'is pinned.',
    },
    {
        'name': 'opt-nizn-ferrite-powder',
        'display_name': 'NiZn ferrite powder',
        'family': 'soft-magnetic',
        'realization_level': 'literature-demonstrated',
        'item_ref': 'mnzn-ferrite-powder',
        'powder_ref': 'nizn-ferrite-powder-def',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            mu_r_eff=(200.0, '', 'literature-est'),
            b_sat_t=(0.33, 'T', 'literature-est'),
            h_c_ka_m=(1.0, 'kA/m', 'literature-est'),
            sigma_s_m=(1.0e-3, 'S/m', 'literature-est'),
            density_kg_m3=(5300.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Insulating high-frequency soft ferrite; '
                 'literature sol-gel route = a makeable candidate '
                 '(uncited recipe gap).',
    },
    {
        'name': 'opt-mnzn-ferrite-powder',
        'display_name': 'MnZn ferrite powder',
        'family': 'soft-magnetic',
        'realization_level': 'literature-demonstrated',
        'item_ref': 'mnzn-ferrite-powder',
        'powder_ref': 'mnzn-ferrite-powder-def',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            mu_r_eff=(800.0, '', 'literature-est'),
            b_sat_t=(0.45, 'T', 'literature-est'),
            h_c_ka_m=(0.5, 'kA/m', 'literature-est'),
            sigma_s_m=(1.0, 'S/m', 'literature-est'),
            density_kg_m3=(4900.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The msci FEM inclusion value (mu 800) lives '
                 'here. UK small-lot retail cited est (mag-1); US '
                 'channel quote-only.',
    },
    {
        'name': 'opt-geopolymer-ferrite',
        'display_name': 'Geopolymer-ferrite composite (35 vol%)',
        'family': 'soft-magnetic',
        'realization_level': 'recipe-seeded',
        'item_ref': 'magnetic-geopolymer-mix',
        'msci_material_ref': 'geopolymer-ferrite',
        'forms_json': json.dumps(['castable-block']),
        'properties_json': _props(
            tensile_mpa=(3.5, 'MPa', 'literature-est', 'literature CLASS value; our castings are untested, and brittle strength scatters widely (Weibull) so the mean is not the design number'),
            youngs_modulus_mpa=(16000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.2, '', 'literature-est'),
            compressive_mpa=(50.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('brittle', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            mu_r_eff=(2.196, '', 'literature-est',
                      'OUR msci-22 FEM homogenization @35vol% — '
                      'simulated, not measured'),
            h_c_ka_m=(8.0, 'kA/m', 'literature-est',
                      'inherits the filler\'s soft character'),
            b_sat_t=(0.21, 'T', 'literature-est',
                     'volume-diluted filler B_sat (0.6 T x 35 '
                     'vol%) — the honest composite ceiling prior'),
            density_kg_m3=(3120.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The bulk castable magnetic part; cascades '
                 '6.09/kg (mag-1). Cure-with-ferrite + moisture = '
                 'stated unknowns.',
    },
    {
        'name': 'opt-solgel-ferrite',
        'display_name': 'Sol-gel-ferrite mortar (25 vol%)',
        'family': 'soft-magnetic',
        'realization_level': 'recipe-seeded',
        'item_ref': 'magnetic-solgel-composite',
        'msci_material_ref': 'sol-gel-ferrite',
        'forms_json': json.dumps(['mortar', 'potting']),
        'properties_json': _props(
            mu_r_eff=(1.714, '', 'literature-est',
                      'msci-22 FEM @25vol% — simulated'),
            h_c_ka_m=(8.0, 'kA/m', 'literature-est'),
            sigma_s_m=(1.0e-4, 'S/m', 'literature-est',
                       'sub-percolation at 25vol% oxide — '
                       'unverified'),
            density_kg_m3=(2800.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'THE flux-continuity mortar of the §2b monolith '
                 'model; 10.22/kg cascaded.',
    },
    {
        'name': 'opt-plain-solgel-mortar',
        'display_name': 'Plain sol-gel mortar (mu~1)',
        'family': 'containment-structural',
        'realization_level': 'recipe-seeded',
        'item_ref': 'silica-xerogel',
        'forms_json': json.dumps(['mortar', 'potting']),
        'properties_json': _props(
            mu_r_eff=(1.0, '', 'literature-est'),
            sigma_s_m=(1.0e-6, 'S/m', 'literature-est'),
            density_kg_m3=(2000.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Magnetically a GAP — use where flux should NOT '
                 'couple; the deliberate-gap mortar grade and the '
                 'safer (near-neutral) winding potting.',
    },
    {
        'name': 'opt-wax-ferrite',
        'display_name': 'Wax-ferrite print feedstock (30 vol%)',
        'family': 'soft-magnetic',
        'realization_level': 'recipe-seeded',
        'item_ref': 'wax-ferrite-feedstock',
        'msci_material_ref': '',
        'forms_json': json.dumps(['castable-block']),
        'properties_json': _props(
            mu_r_eff=(1.9, '', 'literature-est',
                      'msci wax-ferrite row @30vol% — simulated '
                      'order'),
            density_kg_m3=(2210.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'PRINTABLE magnetics (10.01/kg cascaded); 71wt% '
                 'loading printability = trial-gated; melts back '
                 'to the reclaim pool.',
    },
    {
        'name': 'opt-fired-ferrite-ceramic',
        'display_name': 'Fired ferrite-ceramic (Table 8.8 rung)',
        'family': 'soft-magnetic',
        'realization_level': 'recipe-seeded',
        'item_ref': '',
        'msci_material_ref': 'ferrite-ceramic',
        'forms_json': json.dumps(['sintered-part',
                                  'castable-block']),
        'properties_json': _props(
            tensile_mpa=(35.0, 'MPa', 'literature-est', 'literature CLASS value; our castings are untested, and brittle strength scatters widely (Weibull) so the mean is not the design number'),
            youngs_modulus_mpa=(110000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.24, '', 'literature-est'),
            compressive_mpa=(450.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('brittle', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            mu_r_eff=(2.484, '', 'literature-est',
                      'msci FEM @40vol% — the cast-composite '
                      'ceiling; SINTERED ferrite parts run '
                      '1e2-1e4'),
            b_sat_t=(0.24, 'T', 'literature-est',
                     'volume-diluted filler B_sat (0.6 T x 40 '
                     'vol%)'),
            density_kg_m3=(3400.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The mu escalation of any cast composite '
                 '(geopolymer->ceramic firing; kiln energy '
                 'excluded-loud). No item_ref: costing rides the '
                 'input composite + firing.',
    },
    {
        'name': 'opt-electrical-steel',
        'display_name': 'Electrical steel laminations (REFERENCE)',
        'family': 'reference',
        'realization_level': 'literature-demonstrated',
        'item_ref': '',
        'forms_json': json.dumps(['sintered-part']),
        'properties_json': _props(
            tensile_mpa=(350.0, 'MPa', 'literature-est', 'literature CLASS value; our castings are untested, and brittle strength scatters widely (Weibull) so the mean is not the design number'),
            youngs_modulus_mpa=(200000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.29, '', 'literature-est'),
            compressive_mpa=(350.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('ductile', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            mu_r_eff=(4000.0, '', 'literature-est'),
            b_sat_t=(2.0, 'T', 'literature-est'),
            h_c_ka_m=(0.06, 'kA/m', 'literature-est'),
            density_kg_m3=(7650.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_reference_only': True,
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Benchmark row for parity math — NOT our route '
                 '(radial laminations want manufacturing we '
                 'don\'t have; §2d designs AROUND this).',
    },
    # ---------------- HARD MAGNETIC ---------------- #
    {
        'name': 'opt-srfe12o19',
        'display_name': 'Strontium hexaferrite powder (SrFe12O19)',
        'family': 'hard-magnetic',
        'realization_level': 'recipe-seeded',
        'item_ref': 'srfe12o19-powder',
        'powder_ref': 'srfe12o19-powder-def',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            b_r_t=(0.40, 'T', 'literature-est',
                   'sintered order; bonded isotropic ~0.2'),
            h_c_ka_m=(250.0, 'kA/m', 'literature-est'),
            b_sat_t=(0.45, 'T', 'literature-est'),
            mu_r_eff=(1.3, '', 'literature-est'),
            sigma_s_m=(1.0e-6, 'S/m', 'literature-est'),
            density_kg_m3=(5100.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': '§1b Rung 1: MAKEABLE from pottery chemicals '
                 '(mag-1 recipes 11.81-16.94/kg feed, kiln '
                 'excluded); buy-side QUOTE-ONLY in the US — the '
                 'local route answers a real gap. Magnetizing '
                 'pulse required.',
    },
    {
        'name': 'opt-bafe12o19',
        'display_name': 'Barium hexaferrite powder (BaFe12O19)',
        'family': 'hard-magnetic',
        'realization_level': 'literature-demonstrated',
        'item_ref': 'barium-carbonate',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            b_r_t=(0.38, 'T', 'literature-est'),
            h_c_ka_m=(240.0, 'kA/m', 'literature-est'),
            density_kg_m3=(5300.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Same chemistry as SrM; BaCO3 TOXICITY caveat as '
                 'data (mag-1 citation note) — SrCO3 preferred for '
                 'exactly this reason. item_ref points at the '
                 'feedstock (no BaM recipe seeded on purpose).',
    },
    {
        'name': 'opt-bonded-hexaferrite-geopolymer',
        'display_name': 'Bonded hexaferrite in geopolymer '
                        '(isotropic)',
        'family': 'hard-magnetic',
        'realization_level': 'literature-demonstrated',
        'item_ref': '',
        'powder_ref': 'srfe12o19-powder-def',
        'forms_json': json.dumps(['castable-block']),
        'properties_json': _props(
            tensile_mpa=(3.0, 'MPa', 'literature-est', 'literature CLASS value; our castings are untested, and brittle strength scatters widely (Weibull) so the mean is not the design number'),
            youngs_modulus_mpa=(14000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.22, '', 'literature-est'),
            compressive_mpa=(45.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('brittle', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            b_r_t=(0.12, 'T', 'literature-est',
                   'isotropic bonded at ~50-60wt% — literature '
                   'order for bonded magnets, OUR matrix untested'),
            h_c_ka_m=(200.0, 'kA/m', 'literature-est'),
            mu_r_eff=(1.15, '', 'literature-est',
                      'recoil permeability order for bonded '
                      'hexaferrite'),
            density_kg_m3=(3200.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'DERIVED option: rides the SrFe12O19 recipe + the '
                 'magnetic-geopolymer requirement (hexaferrite is '
                 'a filler candidate there). Anisotropic grade '
                 'needs the ALIGNER (§1b: itself a buildable '
                 'tool). Commercial bonded-ferrite BLDC motors = '
                 'the industry proof.',
    },
    {
        'name': 'opt-sintered-hexaferrite',
        'display_name': 'Sintered hexaferrite (ceramic magnet)',
        'family': 'hard-magnetic',
        'realization_level': 'literature-demonstrated',
        'item_ref': 'ceramic-ring-magnet',
        'forms_json': json.dumps(['sintered-part']),
        'properties_json': _props(
            tensile_mpa=(35.0, 'MPa', 'literature-est', 'literature CLASS value; our castings are untested, and brittle strength scatters widely (Weibull) so the mean is not the design number'),
            youngs_modulus_mpa=(150000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.28, '', 'literature-est'),
            compressive_mpa=(600.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('brittle', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            b_r_t=(0.39, 'T', 'literature-est',
                   'grade 5 ceramic order'),
            h_c_ka_m=(260.0, 'kA/m', 'literature-est'),
            density_kg_m3=(4900.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'BUYABLE-CITED (mag-1 ring magnets, deep tiers) = '
                 'the make-vs-buy benchmark for the PM rotor; also '
                 'OUR pottery-kiln sinter rung once powder lands.',
    },
    {
        'name': 'opt-aligned-magnetite-chains',
        'display_name': 'Field-aligned magnetite chains (semi-hard)',
        'family': 'hard-magnetic',
        'realization_level': 'literature-demonstrated',
        'item_ref': '',
        'msci_material_ref': '',
        'forms_json': json.dumps(['castable-block', 'mortar']),
        'properties_json': _props(
            b_r_t=(0.03, 'T', 'literature-est',
                   'shape-anisotropy chains — WEAK vs hexaferrite '
                   'by an order'),
            h_c_ka_m=(30.0, 'kA/m', 'literature-est'),
            density_kg_m3=(3100.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': '§1b Rung 2 — the msci ferrite-chaining rows '
                 '(lambda=12, 20nm) ARE this physics; field-align '
                 'during cure. Honest ceiling: bias/bearing-assist '
                 '/sensing, NOT main torque (fails the '
                 'torque-magnet predicate by design).',
    },
    {
        'name': 'opt-fe16n2',
        'display_name': "α″-Fe16N2 (aspiration node)",
        'family': 'hard-magnetic',
        'realization_level': 'theoretical',
        'item_ref': '', 'powder_ref': 'fe16n2-theoretical',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            b_r_t=(1.0, 'T', 'theoretical'),
            h_c_ka_m=(190.0, 'kA/m', 'theoretical'),
            b_sat_t=(2.9, 'T', 'theoretical'),
            density_kg_m3=(7200.0, 'kg/m3', 'theoretical')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Literature-demonstrated BY OTHERS (Niron); '
                 'theoretical FOR US — realization says our state, '
                 'the note says the world\'s. Low-temp nitriding '
                 '(~150-200C!) is the tantalizing part.',
    },
    {
        'name': 'opt-mnal-tau',
        'display_name': 'MnAl τ-phase (aspiration node)',
        'family': 'hard-magnetic',
        'realization_level': 'theoretical',
        'item_ref': '',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            b_r_t=(0.55, 'T', 'theoretical',
                   'lab order; real-world (BH)max modest so far'),
            h_c_ka_m=(200.0, 'kA/m', 'theoretical'),
            density_kg_m3=(5100.0, 'kg/m3', 'theoretical')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Dirt-common elements, metastable quench+anneal '
                 'metallurgy — the foundry-adjacent aspiration.',
    },
    {
        'name': 'opt-alnico',
        'display_name': 'Alnico (foundry rung)',
        'family': 'hard-magnetic',
        'realization_level': 'literature-demonstrated',
        'item_ref': '',
        'forms_json': json.dumps(['sintered-part']),
        'properties_json': _props(
            b_r_t=(1.25, 'T', 'literature-est',
                   'HIGH B_r...'),
            h_c_ka_m=(50.0, 'kA/m', 'literature-est',
                      '...but LOW H_c — demagnetizes in motor '
                      'duty without careful circuit design'),
            density_kg_m3=(7300.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Needs foundry ~1600C + field heat-treat (later '
                 'metal-casting tree); cobalt = semi-scarce (not '
                 'rare-earth). H_c 50 FAILS the torque-magnet '
                 'predicate (>=100) — the taxonomy honestly '
                 'excludes it for PM-motor duty (demag risk); '
                 'the threshold is an editable knob.',
    },
    {
        'name': 'opt-exchange-spring',
        'display_name': 'Exchange-spring nanocomposite (long-run)',
        'family': 'hard-magnetic',
        'realization_level': 'theoretical',
        'item_ref': '', 'powder_ref': 'exchange-spring-theoretical',
        'forms_json': json.dumps(['powder']),
        'properties_json': _props(
            b_r_t=(0.55, 'T', 'theoretical'),
            h_c_ka_m=(180.0, 'kA/m', 'theoretical'),
            density_kg_m3=(5150.0, 'kg/m3', 'theoretical')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'L4-CLASS GAP flagged: beyond mean-field '
                 'homogenization — aspiration bookkeeping, not '
                 'prediction.',
    },
    {
        'name': 'opt-ndfeb',
        'display_name': 'NdFeB (REFERENCE ONLY)',
        'family': 'reference',
        'realization_level': 'literature-demonstrated',
        'item_ref': '',
        'forms_json': json.dumps(['sintered-part']),
        'properties_json': _props(
            tensile_mpa=(80.0, 'MPa', 'literature-est', 'literature CLASS value; our castings are untested, and brittle strength scatters widely (Weibull) so the mean is not the design number'),
            youngs_modulus_mpa=(160000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.24, '', 'literature-est'),
            compressive_mpa=(1100.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('brittle', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            b_r_t=(1.3, 'T', 'literature-est'),
            h_c_ka_m=(900.0, 'kA/m', 'literature-est'),
            density_kg_m3=(7500.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_reference_only': True,
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'THE parity benchmark torque_parity() compares '
                 'against (ferrite B_r 0.2-0.4 vs 1.2-1.4 -> '
                 '3-6x gap area for parity, §2d). Against the '
                 'local ethos for USE; priced for HONESTY when a '
                 'citation lands.',
    },
    # ---------------- ELECTRIC CONDUCTORS ---------------- #
    {
        'name': 'opt-copper-magnet-wire',
        'display_name': 'Copper magnet wire (enameled)',
        'family': 'electric-conductor',
        'realization_level': 'made-and-measured',
        'item_ref': 'magnet-wire-copper',
        'forms_json': json.dumps(['wire']),
        'properties_json': _props(
            tensile_mpa=(210.0, 'MPa', 'literature-est', 'literature CLASS value; our castings are untested, and brittle strength scatters widely (Weibull) so the mean is not the design number'),
            youngs_modulus_mpa=(117000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.34, '', 'literature-est'),
            compressive_mpa=(210.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('ductile', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            sigma_s_m=(5.96e7, 'S/m', 'literature-est',
                       'IACS copper — the one number nobody '
                       'disputes'),
            density_kg_m3=(8960.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'made-and-measured is fair here: commodity wire '
                 'IS the measured state of the art, cited '
                 '31-108/kg by gauge (mag-1). Power current '
                 'stays in magnet wire — every ferrite-CNT '
                 'report prints this.',
    },
    {
        'name': 'opt-aluminum-wire',
        'display_name': 'Aluminum winding wire',
        'family': 'electric-conductor',
        'realization_level': 'literature-demonstrated',
        'item_ref': '',
        'forms_json': json.dumps(['wire']),
        'properties_json': _props(
            sigma_s_m=(3.5e7, 'S/m', 'literature-est'),
            density_kg_m3=(2700.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Power-lite alternative (61% IACS but 1/3 the '
                 'density — better sigma/kg than copper). '
                 'UNCITED: the mag-1 hunt found NO posted retail '
                 'price (Amazon/eBay bot-blocked) — a named gap.',
    },
    {
        'name': 'opt-ferrite-cnt-composite',
        'display_name': 'Ferrite-CNT composite (magnetic + signal)',
        'family': 'electric-conductor',
        'realization_level': 'recipe-seeded',
        'item_ref': 'ferrite-cnt-solgel-mortar',
        'forms_json': json.dumps(['mortar', 'trace',
                                  'castable-block']),
        'properties_json': _props(
            sigma_s_m=(227.0, 'S/m', 'literature-est',
                       'msci-23 percolation @2vol% CNT — '
                       'simulated'),
            mu_r_eff=(1.6, '', 'literature-est',
                      'ferrite fraction sets mu — simulated '
                      'order'),
            density_kg_m3=(2900.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Dual-property mortar (9.96/kg cascaded, mag-1); '
                 'sensor wiring disappears into the monolith. '
                 'Copper gap ~5 orders — printed on every report.',
    },
    {
        'name': 'opt-graphite-composite',
        'display_name': 'Graphite/carbon-black composite trace',
        'family': 'electric-conductor',
        'realization_level': 'literature-demonstrated',
        'item_ref': 'graphite-powder',
        'forms_json': json.dumps(['trace', 'mortar']),
        'properties_json': _props(
            sigma_s_m=(50.0, 'S/m', 'literature-est',
                       'percolated graphite-in-binder order — '
                       'loading-dependent, unverified here'),
            density_kg_m3=(2100.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The CHEAP common conductive filler (cited est '
                 '18.99/lb, mag-1) — resistive/signal grade; '
                 'the humble alternative to CNT.',
    },
    {
        'name': 'opt-cnt-yarn',
        'display_name': 'CNT yarn (theoretical here)',
        'family': 'electric-conductor',
        'realization_level': 'theoretical',
        'item_ref': '',
        'forms_json': json.dumps(['wire']),
        'properties_json': _props(
            sigma_s_m=(3.0e6, 'S/m', 'theoretical',
                       'best published yarns — far from our '
                       'bench'),
            density_kg_m3=(1500.0, 'kg/m3', 'theoretical')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'CNT synthesis is the EXPLICIT far-off '
                 'assumption (src-6) — yarn even further. '
                 'Simulation-only.',
    },
    # ------------- CONTAINMENT / STRUCTURAL / BEARING ------------- #
    {
        'name': 'opt-plain-geopolymer',
        'display_name': 'Plain geopolymer (structural + fence)',
        'family': 'containment-structural',
        'realization_level': 'recipe-seeded',
        'item_ref': 'geopolymer-mix',
        'forms_json': json.dumps(['castable-block', 'mortar']),
        'properties_json': _props(
            youngs_modulus_mpa=(18000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.2, '', 'literature-est'),
            compressive_mpa=(60.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('brittle', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            mu_r_eff=(1.0, '', 'literature-est'),
            tensile_mpa=(4.0, 'MPa', 'literature-est',
                         'flexural/tensile literature order for '
                         'ambient-cured — OUR mixes unmeasured'),
            sigma_s_m=(1.0e-5, 'S/m', 'literature-est'),
            density_kg_m3=(2000.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'Structural body + flux fence (mu~1) at 1.11/kg '
                 'cascaded. tensile 4 MPa FAILS the 5 MPa '
                 'structural predicate -> honestly unviable for '
                 'rotor containment until OUR measured rows beat '
                 'it (or the knob moves with reason).',
    },
    {
        'name': 'opt-fired-ceramic',
        'display_name': 'Fired ceramic (Table 8.8 structural rung)',
        'family': 'containment-structural',
        'realization_level': 'recipe-seeded',
        'item_ref': '',
        'forms_json': json.dumps(['sintered-part',
                                  'castable-block']),
        'properties_json': _props(
            youngs_modulus_mpa=(90000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.22, '', 'literature-est'),
            compressive_mpa=(400.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('brittle', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            mu_r_eff=(1.0, '', 'literature-est'),
            tensile_mpa=(30.0, 'MPa', 'literature-est'),
            density_kg_m3=(2400.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The dimensional-stability + strength escalation '
                 '(T2 in the §2c ladder); kiln energy '
                 'excluded-loud.',
    },
    {
        'name': 'opt-hexaferrite-pm-ring',
        'display_name': 'Hexaferrite PM ring (bearing centering)',
        'family': 'containment-structural',
        'realization_level': 'literature-demonstrated',
        'item_ref': 'ceramic-ring-magnet',
        'forms_json': json.dumps(['sintered-part']),
        'properties_json': _props(
            b_r_t=(0.39, 'T', 'literature-est'),
            h_c_ka_m=(260.0, 'kA/m', 'literature-est'),
            density_kg_m3=(4900.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The magnetic-bearing candidate — Earnshaw '
                 'honesty travels on every match via the role.',
    },
    {
        'name': 'opt-alumina',
        'display_name': 'Alumina (jewel/pin contact)',
        'family': 'containment-structural',
        'realization_level': 'literature-demonstrated',
        'item_ref': '',
        'msci_material_ref': 'alumina-geopolymer',
        'forms_json': json.dumps(['sintered-part']),
        'properties_json': _props(
            youngs_modulus_mpa=(370000.0, 'MPa', 'literature-est', 'FEM elasticity needs E; literature order for this material CLASS, never measured on our castings'),
            poisson_ratio=(0.22, '', 'literature-est'),
            compressive_mpa=(2500.0, 'MPa', 'literature-est', 'the compressive/tensile ASYMMETRY here is exactly why von Mises is the wrong criterion for this material'),
            failure_class=('brittle', '', 'literature-est', 'decides the criterion: brittle -> max PRINCIPAL stress, ductile -> von Mises'),
            tensile_mpa=(260.0, 'MPa', 'literature-est'),
            mu_r_eff=(1.0, '', 'literature-est'),
            density_kg_m3=(3950.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The ONE mechanically-constrained axis of the '
                 'Earnshaw-honest bearing (jewel/pin, '
                 'near-frictionless point contact).',
    },
    {
        'name': 'opt-ptfe-graphite-pad',
        'display_name': 'PTFE/graphite dry-slide pad',
        'family': 'containment-structural',
        'realization_level': 'literature-demonstrated',
        'item_ref': '',
        'forms_json': json.dumps(['sintered-part']),
        'properties_json': _props(
            tensile_mpa=(25.0, 'MPa', 'literature-est'),
            density_kg_m3=(2200.0, 'kg/m3', 'literature-est')),
        'role_overrides_json': '{}',
        'is_prior': True, 'provenance_id': PROV,
        'notes': 'The humble constrained-axis option (uncited — '
                 'hunt named); often beats cleverness.',
    },
]
