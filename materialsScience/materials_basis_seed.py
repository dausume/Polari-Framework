"""
@cross-cutting
@module materialsScience.materials_basis_seed
@tags @xc:bindings

Seed rows for the materials basis — the wax world gains its shared
identities. Idempotent-by-name (the polariServer seed loop skips
existing names; changed content needs row deletion + restart on
existing volumes, the standing gotcha).

Each MaterialsScienceMaterial bridges a legacy root it honestly has:
the waxes bridge their seeded RawMaterial rows; paraffin-wax bridges
the live condensation simulation (its level-0 definition IS that sim).
Scale definitions exist ONLY where earned — every wax at level 0,
nothing else — so scale_presence gates have real absent levels to
refuse on (piecemeal-first, honest by construction).
"""

SEED_MS_MATERIALS = [
    {
        'name': 'beeswax',
        'display_name': 'Beeswax',
        'description': 'Natural wax (Apis mellifera comb) — seeded '
                       'formulation base.',
        'material_kind': 'pure',
        'raw_material_name': 'Beeswax',
        'element_symbols_json': '["C", "H", "O"]',
    },
    {
        'name': 'carnauba-wax',
        'display_name': 'Carnauba Wax',
        'description': 'Hard palm wax (Copernicia prunifera) — hardness/'
                       'melt-point booster in wax formulations.',
        'material_kind': 'pure',
        'raw_material_name': 'Carnauba Wax',
        'element_symbols_json': '["C", "H", "O"]',
    },
    {
        'name': 'soy-wax',
        'display_name': 'Soy Wax',
        'description': 'Hydrogenated soybean-oil wax — soft, cheap '
                       'formulation base.',
        'material_kind': 'pure',
        'raw_material_name': 'Soy Wax',
        'element_symbols_json': '["C", "H", "O"]',
    },
    {
        'name': 'paraffin-wax',
        'display_name': 'Paraffin Wax',
        'description': 'Petroleum alkane wax — the msim condensation '
                       'test substance (Milestone F).',
        'material_kind': 'pure',
        'element_symbols_json': '["C", "H"]',
    },
    {
        'name': 'candelilla-wax',
        'display_name': 'Candelilla Wax',
        'description': 'Hard shrub wax (Euphorbia cerifera) — inherent '
                       'fine crystal morphology per Dustin\'s notes; NOT '
                       'in the legacy raw-material seeds (no bridge yet).',
        'material_kind': 'pure',
        'element_symbols_json': '["C", "H", "O"]',
    },
    {
        'name': 'coconut-wax',
        'display_name': 'Coconut Wax',
        'description': 'Soft hydrogenated coconut-oil wax — lowest melt '
                       'range of the noted bases (35-38C).',
        'material_kind': 'pure',
        'raw_material_name': 'Coconut Wax',
        'element_symbols_json': '["C", "H", "O"]',
    },
    {
        'name': 'beeswax-carnauba-blend',
        'display_name': 'Beeswax–Carnauba Blend',
        'description': 'Demonstration mixture: beeswax base hardened '
                       'with carnauba — the rules-of-mixtures worked '
                       'example.',
        'material_kind': 'mixture',
    },
]

SEED_MS_SCALE_DEFINITIONS = [
    {
        'name': 'beeswax@L0',
        'material_name': 'beeswax',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'RawMaterial', 'definition_ref': 'Beeswax',
        'status': 'defined', 'derivation_method': 'measured',
    },
    {
        'name': 'carnauba-wax@L0',
        'material_name': 'carnauba-wax',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'RawMaterial', 'definition_ref': 'Carnauba Wax',
        'status': 'defined', 'derivation_method': 'measured',
    },
    {
        'name': 'soy-wax@L0',
        'material_name': 'soy-wax',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'RawMaterial', 'definition_ref': 'Soy Wax',
        'status': 'defined', 'derivation_method': 'measured',
    },
    {
        # Paraffin's level-0 home is the LIVE condensation simulation —
        # the definition_ref bridge into the executable msim world.
        'name': 'paraffin-wax@L0',
        'material_name': 'paraffin-wax',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'SimulationDefinition',
        'definition_ref': 'material-condensation',
        'status': 'defined', 'derivation_method': 'measured',
        'notes': 'Melt line + phase gate live in the msim condensation '
                 'space (solid-ball-achievable).',
    },
    {
        # EXECUTABLE level-1 definition: run it (POST /api/msci/
        # scale-definitions/execute) and the FEM result lands in
        # parameters_json['result'], status partial→defined. k=0.25
        # W/m·K is beeswax's literature-order conductivity; geometry is
        # the engine's unit-square demo slab (honest note below).
        'name': 'beeswax@L1',
        'material_name': 'beeswax',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'EngineComputation', 'definition_ref': '',
        'status': 'partial',
        'derived_from_name': 'beeswax@L0',
        'derivation_method': 'homogenized',
        'parameters_json': '{"engine": "fem.conduction", "inputs": '
                           '{"thermalConductivity": 0.25, '
                           '"heatSource": 1.0, "refine": 4}}',
        'notes': 'partial until executed; unit-square demo slab, not a '
                 'part geometry — proves the level-1 engine path.',
    },
    {
        # EXECUTABLE level-4 definition: molecular DFT on a SHORT-ALKANE
        # REPRESENTATIVE FRAGMENT (propane) — honest stand-in; real
        # paraffin chains (C20+) come once basis-set strategy is chosen.
        'name': 'paraffin-wax@L4',
        'material_name': 'paraffin-wax',
        'scale_level': 4, 'scale_category': 'quantum',
        'definition_class': 'EngineComputation', 'definition_ref': '',
        'status': 'partial',
        'derivation_method': 'dft-parameterized',
        'parameters_json': '{"engine": "dft.molecular-energy", "inputs": '
                           '{"atoms": "C 0 0 0; C 1.54 0 0; C 2.31 1.33 0; '
                           'H -0.63 0.88 0; H -0.63 -0.88 0; '
                           'H -0.36 -0.9 -0.5; H 1.9 -0.5 0.88; '
                           'H 1.9 -0.5 -0.88; H 3.37 1.1 0; '
                           'H 2.1 1.9 0.88; H 2.1 1.9 -0.88", '
                           '"basis": "6-31g", "xc": "b3lyp"}}',
        'notes': 'partial until executed; propane fragment as a '
                 'representative short alkane, NOT the full paraffin '
                 'chain.',
    },
    {
        # EXECUTABLE level-1 homogenization of the blend: numerical
        # effective conductivity of carnauba inclusions (k≈0.30) in a
        # beeswax matrix (k≈0.25) at 20% volume — the rigorous sibling
        # of the algebraic L0 rules-of-mixtures row below, with lineage.
        'name': 'beeswax-carnauba-blend@L1',
        'material_name': 'beeswax-carnauba-blend',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'EngineComputation', 'definition_ref': '',
        'status': 'partial',
        'derived_from_name': 'beeswax-carnauba-blend@L0',
        'derivation_method': 'homogenized',
        'parameters_json': '{"engine": "fem.effective-conductivity", '
                           '"inputs": {"matrixK": 0.25, '
                           '"inclusionK": 0.30, '
                           '"volumeFraction": 0.2}}',
        'notes': 'partial until executed; 2D unit-cell with circular '
                 'inclusion — literature-order wax conductivities.',
    },
    {
        # Derived definition with explicit lineage — the cross-scale
        # link machinery in miniature (level 0 → level 0 mixing).
        'name': 'beeswax-carnauba-blend@L0',
        'material_name': 'beeswax-carnauba-blend',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'Formulation', 'definition_ref': '',
        'status': 'partial',
        'derived_from_name': 'beeswax@L0',
        'derivation_method': 'rules-of-mixtures',
        'parameters_json': '{"constituents": ["beeswax@L0", '
                           '"carnauba-wax@L0"], '
                           '"volumeFractions": [0.8, 0.2], '
                           '"rule": "hybrid"}',
        'notes': 'partial: fractions chosen for the worked example, not '
                 'yet target-searched.',
    },
    {
        # A scale level BACKED BY A CONFIGURED MODEL DEFINITION
        # (msci-19): executing this row runs the wax-thermal-continuum
        # FEMModelDefinition (whose inputs are object-bound) and stores
        # the result here — levels-by-component, the third executable
        # definition_class after EngineComputation.
        'name': 'beeswax-carnauba-blend@L1c',
        'material_name': 'beeswax-carnauba-blend',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'FEMModelDefinition',
        'definition_ref': 'wax-thermal-continuum',
        'status': 'partial',
        'derived_from_name': 'beeswax-carnauba-blend@L0',
        'derivation_method': 'homogenized',
        'parameters_json': '{}',
        'notes': 'partial until executed; the configured-model sibling '
                 'of the inline @L1 EngineComputation row.',
    },
]
