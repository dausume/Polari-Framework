"""
@cross-cutting
@module aquaponics.pot_materials_seed
@tags @xc:bindings

Waterproof pot materials (aqp-1) — Dustin: the pot is ceramic OR
geopolymer, a WATERPROOF variant. Seeded IN-IDIOM as materials-science
rows (MaterialsScienceMaterial identity + MaterialScaleDefinition L0),
so a pot's material_name points at a real material the rest of the
framework already understands.

'Waterproof' is modeled as near-zero HYDRAULIC permeability + low open
porosity — new property meanings this module contributes. NOTE: these
L0 values are literature/spec PRIORS, honestly flagged; the real
Darcy/absorption solve is a new engine in aqp-3 (the materials survey
confirmed no fluid-flow physics exists yet — this is where it starts).

@consumers
  - polariServer seed_pairs (appended to the materials-science lists)
@see /AQUAPONICS_MODULE_PLAN.md
"""

import json

_PROV = 'aqp-1 pot material spec (literature prior — Darcy solve pending)'

#: Two waterproof pot materials. Both reference the existing seeded
#: base families (geopolymer, alumina-ceramic) — a waterproof variant
#: is a distinct identity whose open porosity / hydraulic permeability
#: are driven toward zero (glaze / sealed gel).
SEED_POT_MATERIALS = [
    {
        'name': 'geopolymer-waterproof',
        'display_name': 'Waterproof geopolymer',
        'material_kind': 'composite',
        'category': 'structural',
        'element_symbols_json': json.dumps(
            ['Si', 'Al', 'O', 'Na', 'H']),
        'tags_json': json.dumps(
            ['pot', 'waterproof', 'geopolymer', 'aquaponics']),
        'reference_material_name': 'geopolymer',
        'provenance_id': _PROV,
    },
    {
        'name': 'ceramic-glazed',
        'display_name': 'Glazed ceramic (waterproof)',
        'material_kind': 'composite',
        'category': 'structural',
        'element_symbols_json': json.dumps(
            ['Al', 'O', 'Si', 'K']),
        'tags_json': json.dumps(
            ['pot', 'waterproof', 'ceramic', 'glazed', 'aquaponics']),
        'reference_material_name': 'alumina-ceramic',
        'provenance_id': _PROV,
    },
]

#: L0 scale definitions carrying the waterproofing priors. porosity =
#: OPEN (connected) porosity available to water; hydraulicPermeability
#: in m^2 (near-zero = waterproof); waterAbsorption = % mass gain at
#: saturation (glazed/sealed bodies are well under 0.5%).
SEED_POT_SCALE_DEFINITIONS = [
    {
        'name': 'geopolymer-waterproof@L0',
        'material_name': 'geopolymer-waterproof',
        'scale_level': 0,
        'scale_category': 'experimental',
        'status': 'partial',
        'derived_from_name': 'geopolymer@L0',
        'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'openPorosity': 0.02,
            'hydraulicPermeability': 1e-19,
            'waterAbsorption': 0.4,
            'density': 1900.0,
            'thermalConductivity': 0.9,
            'compressiveStrength': 45.0,
            'note': 'sealed/low-Ca geopolymer body; priors pending '
                    'a Darcy solve (aqp-3)',
        }),
        'provenance_id': _PROV,
    },
    {
        'name': 'ceramic-glazed@L0',
        'material_name': 'ceramic-glazed',
        'scale_level': 0,
        'scale_category': 'experimental',
        'status': 'partial',
        'derived_from_name': 'alumina-ceramic@L0',
        'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'openPorosity': 0.005,
            'hydraulicPermeability': 1e-20,
            'waterAbsorption': 0.1,
            'density': 2400.0,
            'thermalConductivity': 1.5,
            'compressiveStrength': 120.0,
            'note': 'vitreous glaze seals the body; priors pending '
                    'a Darcy solve (aqp-3)',
        }),
        'provenance_id': _PROV,
    },
]

#: Property meanings this module contributes to the shared vocabulary
#: (hydraulic — NOT the magnetic effectivePermeability already seeded).
SEED_POT_PROPERTY_MEANINGS = [
    {
        'name': 'openPorosity',
        'display_name': 'Open porosity',
        'units': 'fraction',
        'meaning': 'The connected void fraction water can actually '
                   'enter and move through — the porosity that '
                   'matters for waterproofing (distinct from total '
                   'porosity, which includes sealed voids).',
        'scenario_context': 'Higher open porosity → more absorption '
                            'and seepage; a waterproof pot drives it '
                            'toward zero (glaze, sealed gel).',
        'aliases_json': json.dumps(
            ['open_porosity', 'connectedPorosity', 'effectivePorosity']),
        'scale_levels_json': json.dumps([0, 1]),
    },
    {
        'name': 'hydraulicPermeability',
        'display_name': 'Hydraulic permeability',
        'units': 'm^2',
        'meaning': "The intrinsic (Darcy) permeability to LIQUID "
                   'water — how readily water seeps through the pot '
                   'wall under a pressure/head gradient. This is the '
                   'FLUID permeability, not the magnetic '
                   'effectivePermeability already in the vocabulary.',
        'scenario_context': 'Near 1e-20 m^2 = effectively waterproof; '
                            'a fired-but-unglazed body is orders of '
                            'magnitude higher. Wall values remain L0 '
                            'priors, but the SOIL flow they bound is '
                            'now COMPUTED: GET /api/aquaponics/pots/'
                            '{name}/drains (aqp-3 Darcy engine) '
                            'returns the solved rate + fidelity.',
        'aliases_json': json.dumps(
            ['hydraulic_permeability', 'darcyPermeability',
             'waterPermeability', 'k_hydraulic']),
        'scale_levels_json': json.dumps([0, 1]),
    },
    {
        'name': 'waterAbsorption',
        'display_name': 'Water absorption',
        'units': '% mass',
        'meaning': 'Mass of water a saturated body takes up, as a '
                   'percent of dry mass — the standard ceramic '
                   'water-tightness measure.',
        'scenario_context': 'Vitreous/glazed bodies sit under ~0.5%; '
                            'earthenware is 5-15%. A self-watering pot '
                            'wants low absorption so the wall does not '
                            'wick the reservoir dry into the air.',
        'aliases_json': json.dumps(
            ['water_absorption', 'absorptionPct']),
        'scale_levels_json': json.dumps([0]),
    },
]
