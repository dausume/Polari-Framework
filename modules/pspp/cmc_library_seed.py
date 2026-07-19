"""
@module pspp.cmc_library_seed

The GENERALITY PROOF (plan pspp-11, data-only half): the minimal
ceramic-matrix-composite library entered ENTIRELY through existing
classes — MaterialPropertyMeaning descriptors, ProcessingStage rows,
MaterialProcessDefinition rows. ZERO new classes, zero engines: if
this file needed a schema change, the PSPP schema was wrong.

Sources: the CMC book's table of contents + ChatGPT's Ch. survey
(structure descriptors that are load-bearing for CMCs) — numeric
relations wait for actual chapter pages (invariant I5).
"""

_PROV = ('pspp-11 CMC library (CMC book ToC + relayed survey '
         '2026-07-18; equations pending chapter pages)')

#: MaterialPropertyMeaning rows — the CMC structure/property
#: vocabulary (merged into the shared vocabulary; scale-qualified).
SEED_CMC_PROPERTY_MEANINGS = [
    {'name': 'reinforcementVolumeFraction',
     'display_name': 'Reinforcement volume fraction',
     'units': 'volume fraction',
     'meaning': 'Fraction of the composite occupied by the '
                'reinforcement (fibers/whiskers/particles).',
     'scenario_context': 'First-order driver of stiffness/strength; '
                         'rule-of-mixtures bounds apply along fibers '
                         'only with orientation/length efficiency.',
     'aliases_json': '["Vf", "fiberVolumeFraction"]',
     'scale_levels_json': '[0, 1]'},
    {'name': 'orientationTensor',
     'display_name': 'Fiber orientation tensor',
     'units': 'tensor (dimensionless)',
     'meaning': 'Statistical orientation of the reinforcement — '
                'aligned, woven, or random architectures.',
     'scenario_context': 'Sets the orientation efficiency in any '
                         'efficiency-factor stiffness model; textile '
                         'architectures need their own descriptors.',
     'aliases_json': '["fiberOrientation"]',
     'scale_levels_json': '[1, 2]'},
    {'name': 'interfaceShearStrength',
     'display_name': 'Interfacial shear strength',
     'units': 'MPa',
     'meaning': 'Shear strength of the fiber/matrix interface or '
                'interphase — the CMC design variable: WEAK '
                'interfaces deflect cracks (toughness), strong ones '
                'embrittle.',
     'scenario_context': 'Set by fiber coatings (PyC/BN) and '
                         'processing; degrades under oxidation.',
     'aliases_json': '["tau_i"]',
     'scale_levels_json': '[1, 2]'},
    {'name': 'interfaceFractureEnergy',
     'display_name': 'Interface fracture energy',
     'units': 'J/m²',
     'meaning': 'Energy to debond the interface — governs crack '
                'deflection vs penetration at the fiber.',
     'scenario_context': 'The deflection criterion compares it to '
                         'the fiber fracture energy (relation '
                         'pending source pages).',
     'aliases_json': '[]',
     'scale_levels_json': '[2]'},
    {'name': 'matrixCrackDensity',
     'display_name': 'Matrix crack density',
     'units': '1/mm',
     'meaning': 'Cracks per unit length in the matrix — evolves '
                'under load; the CMC damage variable.',
     'scenario_context': 'Saturates with load; opens oxygen ingress '
                         'paths (stress-oxidation coupling).',
     'aliases_json': '[]',
     'scale_levels_json': '[1]'},
    {'name': 'fiberStrengthWeibullModulus',
     'display_name': 'Fiber strength Weibull modulus',
     'units': 'dimensionless',
     'meaning': 'Scatter parameter of the stochastic fiber strength '
                'distribution — low modulus = wide scatter.',
     'scenario_context': 'Drives pull-out statistics and rupture '
                         'lifetime models (equations pending).',
     'aliases_json': '["weibullModulus"]',
     'scale_levels_json': '[0, 1]'},
    {'name': 'coatingStack',
     'display_name': 'Fiber coating stack',
     'units': 'layers (material + thickness)',
     'meaning': 'The engineered interphase layers on the fiber '
                '(e.g. PyC, BN, SiC) with thicknesses.',
     'scenario_context': 'The processing knob that SETS interface '
                         'properties; environmental-barrier coatings '
                         'are the part-level analogue.',
     'aliases_json': '[]',
     'scale_levels_json': '[2]'},
    {'name': 'oxidationRecessionDepth',
     'display_name': 'Oxidation recession depth',
     'units': 'µm',
     'meaning': 'How far interphase/fiber oxidation has consumed '
                'material inward from cracks or surfaces.',
     'scenario_context': 'A STATE descriptor (grows in service) — '
                         'performance scenarios track it; rate laws '
                         'await cited sources.',
     'aliases_json': '[]',
     'scale_levels_json': '[0, 1]'},
]
for _row in SEED_CMC_PROPERTY_MEANINGS:
    _row.setdefault('provenance_id', _PROV)

#: ProcessingStage rows — the CMC route (family 'cmc').
SEED_CMC_PROCESSING_STAGES = [
    {'name': 'fiber-preform', 'display_name': 'Fiber preform',
     'material_family': 'cmc',
     'description': 'Woven/braided/laid-up reinforcement '
                    'architecture before any matrix.'},
    {'name': 'coated-preform', 'display_name': 'Coated preform',
     'material_family': 'cmc', 'typical_prior_stage': 'fiber-preform',
     'description': 'Preform after interphase coating (the '
                    'interface is MADE here).'},
    {'name': 'infiltrated-green', 'display_name': 'Infiltrated green',
     'material_family': 'cmc',
     'typical_prior_stage': 'coated-preform',
     'description': 'Matrix precursor in place, not yet converted.'},
    {'name': 'densified-composite',
     'display_name': 'Densified composite',
     'material_family': 'cmc',
     'typical_prior_stage': 'infiltrated-green',
     'description': 'After CVI/PIP cycles or melt infiltration — '
                    'residual matrix porosity is a state descriptor, '
                    'not a defect to hide.'},
]
for _row in SEED_CMC_PROCESSING_STAGES:
    _row.setdefault('provenance_id', _PROV)

#: MaterialProcessDefinition rows — the CMC structure-generating
#: processes (all TRANSFORMATIVE; engines attach later).
SEED_CMC_PROCESS_DEFINITIONS = [
    {'name': 'fiber-coating', 'process_type': 'interface',
     'material_family': 'cmc',
     'description': 'Deposit the interphase stack (PyC/BN/SiC) on '
                    'the preform — writes interfaceShearStrength / '
                    'coatingStack.'},
    {'name': 'cvi-infiltration', 'process_type': 'densification',
     'material_family': 'cmc',
     'description': 'Chemical vapor infiltration — slow, high '
                    'quality, leaves closed porosity.'},
    {'name': 'pip-cycle', 'process_type': 'densification',
     'material_family': 'cmc',
     'description': 'Polymer infiltration + pyrolysis; REPEATED '
                    'cycles (cycle count is a parameter, porosity '
                    'falls per cycle).'},
    {'name': 'melt-infiltration', 'process_type': 'densification',
     'material_family': 'cmc',
     'description': 'Liquid metal/alloy infiltration (e.g. Si for '
                    'SiC/SiC) — fast, risks fiber attack.'},
    {'name': 'hot-pressing', 'process_type': 'densification',
     'material_family': 'cmc',
     'description': 'Pressure + temperature consolidation.'},
    {'name': 'sintering', 'process_type': 'phase-evolution',
     'material_family': 'general',
     'description': 'Thermal consolidation of particulate compacts '
                    '(temperature-time-atmosphere schedule) — also '
                    'the Kriven geopolymer→leucite ceramic route.'},
]
for _row in SEED_CMC_PROCESS_DEFINITIONS:
    _row.setdefault('execution_effect', 'TRANSFORMATIVE')
    _row.setdefault('energy_deposition_model', '')
    _row.setdefault('provenance_id', _PROV)
