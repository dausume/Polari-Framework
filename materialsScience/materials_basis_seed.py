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
]
