"""
@module materialsScience.standard_materials_seed

Five STANDARD material families as coherent materials-science
definitions (Dustin's directive 2026-07-07): sol-gel silica,
geopolymer, technical ceramic (alumina — THE reference ceramic),
carbon nanotube, and nitrogen-doped carbon nanotube.

Coherence rules honored ([[object-coherence]], piecemeal-first):
  - each family is a MaterialsScienceMaterial IDENTITY;
  - each scale level a family has honestly earned is a
    MaterialScaleDefinition row; absent levels are DATA (some carry
    'planned' rows whose notes say exactly what earning them takes);
  - levels our engines can genuinely compute are EXECUTABLE — backed
    by configured FEMModelDefinition / DFTModelDefinition rows
    (msci-15) through the definition_class bridge, so running the
    level IS running the configured model;
  - every number is LITERATURE-TYPICAL and labeled as such
    (provenance 'prov-claude-lit-2026-07-07' — entered by Claude from
    literature-typical ranges, Dustin can verify/veto, same convention
    as msci-11's prov-dustin-lit rows);
  - DFT levels use HONEST MOLECULAR STAND-INS (the propane-for-
    paraffin convention): benzene as the minimal sp2 aromatic fragment
    for a CNT wall, pyridine (one ring CH -> N) as the minimal
    N-DOPED fragment — the doping expressed at fragment level;
  - the doped tube's rows carry LINEAGE from the undoped tube
    (derived_from_name + derivation_method).

Anisotropy honesty: CNT scalar properties are AXIAL values of
individual tubes, not isotropic bulk values; the composite
homogenization model is a 2D circular-inclusion bound that ignores
anisotropy and percolation — order-of-magnitude only, said on the row.
"""

import json

PROV = 'prov-claude-lit-2026-07-07'

# ---------------------------------------------------------------------
# Identities.
# ---------------------------------------------------------------------

SEED_STANDARD_MATERIALS = [
    {
        'name': 'sol-gel-silica',
        'display_name': 'Sol-Gel Silica',
        'description': (
            'Silica from the standard sol-gel route (TEOS/TMOS '
            'hydrolysis -> condensation -> gelation -> drying): '
            'xerogel when ambient-dried, aerogel when supercritically '
            'dried. Porosity is THE structural knob — density and '
            'conductivity swing an order of magnitude with it.'
        ),
        'material_kind': 'pure',
        'element_symbols_json': '["Si", "O", "H"]',
        'provenance_id': PROV,
        'notes': 'Literature-typical property ranges; verify/veto.',
    },
    {
        'name': 'geopolymer',
        'display_name': 'Geopolymer (metakaolin-based)',
        'description': (
            'Alkali-activated aluminosilicate binder (metakaolin + '
            'NaOH/sodium-silicate activator) curing near-ambient to a '
            'cement-like solid — the low-CO2 concrete-binder family. '
            'The legacy module\'s GeopolymerConcreteMoldMaterial '
            'purpose points at this family.'
        ),
        'material_kind': 'mixture',
        'element_symbols_json': '["Si", "Al", "O", "Na", "H"]',
        'provenance_id': PROV,
        'notes': 'Metakaolin-based reference chemistry; fly-ash and '
                 'slag variants shift every number.',
    },
    {
        'name': 'alumina-ceramic',
        'display_name': 'Alumina Ceramic (Al2O3, ~99.5%)',
        'description': (
            'Sintered aluminum-oxide — THE reference technical '
            'ceramic: hard, stiff, refractory, electrically '
            'insulating. Values below are for dense ~99.5% alumina.'
        ),
        'material_kind': 'pure',
        'element_symbols_json': '["Al", "O"]',
        'provenance_id': PROV,
        'notes': 'Porosity and purity grade shift strength/conductivity '
                 'substantially.',
    },
    {
        'name': 'carbon-nanotube',
        'display_name': 'Carbon Nanotube (CNT)',
        'description': (
            'Rolled-graphene tube (SWCNT/MWCNT) — extreme axial '
            'stiffness, strength, and thermal conductivity. STRONGLY '
            'ANISOTROPIC: the famous numbers are along the tube axis '
            'of individual tubes, not isotropic bulk values.'
        ),
        'material_kind': 'pure',
        'element_symbols_json': '["C"]',
        'provenance_id': PROV,
        'notes': 'Chirality (n,m) sets metallic vs semiconducting '
                 'character — not modeled at any seeded level yet.',
    },
    {
        'name': 'n-doped-carbon-nanotube',
        'display_name': 'N-Doped Carbon Nanotube',
        'description': (
            'Carbon nanotube with substitutional nitrogen (typically '
            '1-5 at%): n-type electronic character, enhanced surface '
            'reactivity/catalytic activity vs the pristine tube. '
            'Derived from carbon-nanotube — the doping is expressed '
            'at every level as a delta on the parent.'
        ),
        'material_kind': 'pure',
        'element_symbols_json': '["C", "N"]',
        'provenance_id': PROV,
        'notes': 'Pyridinic vs graphitic vs pyrrolic N sites behave '
                 'differently; the seeded fragment is pyridinic-like.',
    },
]

# ---------------------------------------------------------------------
# Executable model definitions the scale rows reference (msci-15).
# Idealized fragment geometries (benzene D6h: C-C 1.397 A, C-H 1.084 A;
# pyridine as the same idealized hexagon with one CH -> N) — labeled
# idealized; adequate for stand-in SCF energies, not for spectroscopy.
# ---------------------------------------------------------------------

_BENZENE = ('C 1.397 0 0; C 0.6985 1.2098 0; C -0.6985 1.2098 0; '
            'C -1.397 0 0; C -0.6985 -1.2098 0; C 0.6985 -1.2098 0; '
            'H 2.481 0 0; H 1.2405 2.1486 0; H -1.2405 2.1486 0; '
            'H -2.481 0 0; H -1.2405 -2.1486 0; H 1.2405 -2.1486 0')
_PYRIDINE = ('N 1.397 0 0; C 0.6985 1.2098 0; C -0.6985 1.2098 0; '
             'C -1.397 0 0; C -0.6985 -1.2098 0; C 0.6985 -1.2098 0; '
             'H 1.2405 2.1486 0; H -1.2405 2.1486 0; H -2.481 0 0; '
             'H -1.2405 -2.1486 0; H 1.2405 -2.1486 0')

SEED_STANDARD_FEM_MODELS = [
    {
        'name': 'solgel-porous-silica',
        'display_name': 'Sol-gel silica — porous effective conductivity',
        'description': (
            'Xerogel as a 2-phase medium: fused-silica skeleton '
            '(k=1.38 W/m*K, literature) with air pores (k=0.026) at '
            '50% porosity. 2D circular-pore unit cell — a bound, not '
            'the real pore network.'
        ),
        'physics_ref': 'fem-effective-conductivity',
        'domain_json': json.dumps({
            'shape': 'unit-square',
            'inclusion': {'shape': 'circle', 'volumeFraction': 0.5},
        }),
        'materials_json': json.dumps({
            'matrix': {'thermalConductivity': 1.38},
            'inclusion': {'thermalConductivity': 0.026},
        }),
        'boundary_conditions_json': json.dumps([
            {'boundary': 'x-faces', 'type': 'dirichlet',
             'value': 'unit temperature difference'}]),
        'source_terms_json': '{}',
        'mesh_json': json.dumps({'refine': 5}),
        'solver_json': '{}',
        'notes': f'{PROV}: literature-order conductivities; porosity '
                 'is the knob to sweep.',
        'enabled': True,
    },
    {
        'name': 'geopolymer-porous-gel',
        'display_name': 'Geopolymer — porous gel effective conductivity',
        'description': (
            'Aluminosilicate gel skeleton (k=0.95 W/m*K, literature-'
            'typical for dense geopolymer paste) with 25% air '
            'porosity. Same 2D unit-cell bound as the silica model.'
        ),
        'physics_ref': 'fem-effective-conductivity',
        'domain_json': json.dumps({
            'shape': 'unit-square',
            'inclusion': {'shape': 'circle', 'volumeFraction': 0.25},
        }),
        'materials_json': json.dumps({
            'matrix': {'thermalConductivity': 0.95},
            'inclusion': {'thermalConductivity': 0.026},
        }),
        'boundary_conditions_json': json.dumps([
            {'boundary': 'x-faces', 'type': 'dirichlet',
             'value': 'unit temperature difference'}]),
        'source_terms_json': '{}',
        'mesh_json': json.dumps({'refine': 5}),
        'solver_json': '{}',
        'notes': f'{PROV}: literature-order values.',
        'enabled': True,
    },
    {
        'name': 'alumina-slab-conduction',
        'display_name': 'Alumina — steady conduction (unit slab)',
        'description': (
            'Steady conduction through dense alumina (k=30 W/m*K, '
            'literature-typical for 99.5% Al2O3) on the engine\'s '
            'unit-square demo slab — proves the ceramic\'s level-1 '
            'engine path, not a part geometry.'
        ),
        'physics_ref': 'fem-steady-conduction',
        'domain_json': json.dumps({'shape': 'unit-square'}),
        'materials_json': json.dumps({
            'domain': {'thermalConductivity': 30.0}}),
        'boundary_conditions_json': json.dumps([
            {'boundary': 'all', 'type': 'dirichlet', 'value': 0}]),
        'source_terms_json': json.dumps({'heatSource': 1.0}),
        'mesh_json': json.dumps({'refine': 4}),
        'solver_json': '{}',
        'notes': f'{PROV}.',
        'enabled': True,
    },
    {
        'name': 'cnt-epoxy-composite',
        'display_name': 'CNT/epoxy composite — effective conductivity '
                        '(isotropic bound)',
        'description': (
            'Epoxy matrix (k=0.2 W/m*K) with 5 vol% CNT inclusions '
            'using the AXIAL tube conductivity (k=3000 W/m*K). LOUD '
            'ASSUMPTION: the 2D circular-inclusion cell treats the '
            'tubes as isotropic discs and ignores percolation and '
            'interface resistance — an order-of-magnitude BOUND, in '
            'practice measured composites fall far below it.'
        ),
        'physics_ref': 'fem-effective-conductivity',
        'domain_json': json.dumps({
            'shape': 'unit-square',
            'inclusion': {'shape': 'circle', 'volumeFraction': 0.05},
        }),
        'materials_json': json.dumps({
            'matrix': {'thermalConductivity': 0.2},
            'inclusion': {'thermalConductivity': 3000.0},
        }),
        'boundary_conditions_json': json.dumps([
            {'boundary': 'x-faces', 'type': 'dirichlet',
             'value': 'unit temperature difference'}]),
        'source_terms_json': '{}',
        'mesh_json': json.dumps({'refine': 5}),
        'solver_json': '{}',
        'notes': f'{PROV}: axial k for individual tubes; see the '
                 'anisotropy caveat on the CNT identity.',
        'enabled': True,
    },
]

SEED_STANDARD_DFT_MODELS = [
    {
        'name': 'cnt-fragment-energy',
        'display_name': 'CNT wall fragment — molecular SCF energy',
        'description': (
            'Benzene (C6H6, idealized D6h geometry) as the MINIMAL '
            'sp2 aromatic stand-in for a CNT wall patch — the honest-'
            'fragment convention (propane stood in for paraffin). '
            'Real tube-section fragments (pyrene, coronene, capped '
            'tube stubs) come once a basis-set strategy is chosen.'
        ),
        'calculation_ref': 'dft-molecular-energy',
        'structure_json': json.dumps({'kind': 'molecule',
                                      'atoms': _BENZENE}),
        'method_json': json.dumps({'basis': '6-31g', 'xc': 'b3lyp',
                                   'charge': 0, 'spin': 0}),
        'accuracy_json': '{}',
        'notes': f'{PROV}: idealized geometry, stand-in energy only.',
        'enabled': True,
    },
    {
        'name': 'doped-cnt-fragment-energy',
        'display_name': 'N-doped CNT fragment — molecular SCF energy',
        'description': (
            'Pyridine (C5H5N — the benzene fragment with one ring CH '
            'substituted by N) as the minimal PYRIDINIC-NITROGEN-doped '
            'stand-in: the doping expressed at fragment level, '
            'directly comparable against cnt-fragment-energy.'
        ),
        'calculation_ref': 'dft-molecular-energy',
        'structure_json': json.dumps({'kind': 'molecule',
                                      'atoms': _PYRIDINE}),
        'method_json': json.dumps({'basis': '6-31g', 'xc': 'b3lyp',
                                   'charge': 0, 'spin': 0}),
        'accuracy_json': '{}',
        'notes': f'{PROV}: idealized hexagon geometry (real pyridine '
                 'ring is slightly distorted) — stand-in energy only.',
        'enabled': True,
    },
]

# ---------------------------------------------------------------------
# Scale rows (levels 0-4, piecemeal + honest).
# ---------------------------------------------------------------------

SEED_STANDARD_SCALE_DEFINITIONS = [
    # ---- sol-gel silica -------------------------------------------------
    {
        'name': 'sol-gel-silica@L0',
        'material_name': 'sol-gel-silica',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'route': 'TEOS hydrolysis -> condensation -> gel -> dry',
            'densityXerogel_gcm3': [1.8, 2.0],
            'densityAerogel_gcm3': [0.1, 0.3],
            'thermalConductivityXerogel_WmK': [0.3, 0.5],
            'thermalConductivityAerogel_WmK': [0.013, 0.02],
            'typicalGelationTime_h': [1, 48],
        }),
        'provenance_id': PROV,
        'notes': 'Literature-typical ranges; porosity is the master '
                 'variable. Partial until measured samples exist.',
    },
    {
        'name': 'sol-gel-silica@L1',
        'material_name': 'sol-gel-silica',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'FEMModelDefinition',
        'definition_ref': 'solgel-porous-silica',
        'status': 'partial',
        'derived_from_name': 'sol-gel-silica@L0',
        'derivation_method': 'homogenized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Executable: runs the configured porous-silica '
                 'homogenization (partial until executed).',
    },
    {
        'name': 'sol-gel-silica@L4',
        'material_name': 'sol-gel-silica',
        'scale_level': 4, 'scale_category': 'quantum',
        'definition_class': 'Planned', 'definition_ref': '',
        'status': 'planned', 'derivation_method': 'dft-parameterized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Amorphous SiO2 needs PERIODIC DFT (dft-total-energy '
                 'with a WITH_QE engine build + Si/O pseudopotentials) '
                 '— the honest gap; the template exists, the build '
                 'knob does not yet.',
    },
    # ---- geopolymer -----------------------------------------------------
    {
        'name': 'geopolymer@L0',
        'material_name': 'geopolymer',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'binder': 'metakaolin + NaOH/waterglass activator',
            'compressiveStrength_MPa': [20, 80],
            'density_gcm3': [1.6, 1.9],
            'thermalConductivity_WmK': [0.8, 1.0],
            'cureTemperature_C': [20, 80],
            'cureTime_h': [24, 168],
            'siAlRatioTypical': [1.5, 3.0],
        }),
        'provenance_id': PROV,
        'notes': 'Literature-typical for metakaolin geopolymer paste; '
                 'fly-ash/slag variants differ. Partial until '
                 'Dustin\'s own mixes are measured.',
    },
    {
        'name': 'geopolymer@L1',
        'material_name': 'geopolymer',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'FEMModelDefinition',
        'definition_ref': 'geopolymer-porous-gel',
        'status': 'partial',
        'derived_from_name': 'geopolymer@L0',
        'derivation_method': 'homogenized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Executable porous-gel homogenization (partial until '
                 'executed).',
    },
    {
        'name': 'geopolymer@L2',
        'material_name': 'geopolymer',
        'scale_level': 2, 'scale_category': 'mesoscale',
        'definition_class': 'Planned', 'definition_ref': '',
        'status': 'planned', 'derivation_method': 'coarse-grained',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'The N-A-S-H gel network is the interesting mesoscale '
                 'object (CGMD) — planned; no engine rung exists yet.',
    },
    # ---- alumina ceramic ------------------------------------------------
    {
        'name': 'alumina-ceramic@L0',
        'material_name': 'alumina-ceramic',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'density_gcm3': 3.95,
            'thermalConductivity_WmK': 30.0,
            'meltingPoint_C': 2072,
            'vickersHardness_GPa': [15, 20],
            'flexuralStrength_MPa': [300, 400],
            'youngsModulus_GPa': [350, 400],
            'dielectricStrength_kVmm': [10, 20],
        }),
        'provenance_id': PROV,
        'notes': 'Dense ~99.5% alumina, literature-typical; porosity/'
                 'purity move everything.',
    },
    {
        'name': 'alumina-ceramic@L1',
        'material_name': 'alumina-ceramic',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'FEMModelDefinition',
        'definition_ref': 'alumina-slab-conduction',
        'status': 'partial',
        'derived_from_name': 'alumina-ceramic@L0',
        'derivation_method': 'homogenized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Executable unit-slab conduction — the level-1 engine '
                 'path, not a part geometry (partial until executed).',
    },
    {
        'name': 'alumina-ceramic@L4',
        'material_name': 'alumina-ceramic',
        'scale_level': 4, 'scale_category': 'quantum',
        'definition_class': 'Planned', 'definition_ref': '',
        'status': 'planned', 'derivation_method': 'dft-parameterized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Corundum (R-3c) needs periodic DFT — dft-total-energy '
                 'once the WITH_QE build + pseudopotentials exist.',
    },
    # ---- carbon nanotube ------------------------------------------------
    {
        'name': 'carbon-nanotube@L0',
        'material_name': 'carbon-nanotube',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'density_gcm3': [1.3, 1.4],
            'axialThermalConductivity_WmK': [2000, 3500],
            'axialTensileStrength_GPa': [11, 63],
            'axialYoungsModulus_TPa': [0.27, 1.0],
            'anisotropy': 'ALL values are AXIAL, single-tube — bulk '
                          'mats/films fall orders of magnitude lower',
        }),
        'provenance_id': PROV,
        'notes': 'Single-tube literature values; chirality and defects '
                 'dominate the spread.',
    },
    {
        'name': 'carbon-nanotube@L1',
        'material_name': 'carbon-nanotube',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'FEMModelDefinition',
        'definition_ref': 'cnt-epoxy-composite',
        'status': 'partial',
        'derived_from_name': 'carbon-nanotube@L0',
        'derivation_method': 'homogenized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Executable composite BOUND — isotropic-disc '
                 'assumption stated on the model; real CNT composites '
                 'need anisotropic homogenization (sfepy, later).',
    },
    {
        'name': 'carbon-nanotube@L4',
        'material_name': 'carbon-nanotube',
        'scale_level': 4, 'scale_category': 'quantum',
        'definition_class': 'DFTModelDefinition',
        'definition_ref': 'cnt-fragment-energy',
        'status': 'partial',
        'derivation_method': 'dft-parameterized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Executable: benzene wall-patch stand-in (partial '
                 'until executed; the honest-fragment convention).',
    },
    # ---- N-doped carbon nanotube (lineage from the pristine tube) -------
    {
        'name': 'n-doped-carbon-nanotube@L0',
        'material_name': 'n-doped-carbon-nanotube',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial',
        'derived_from_name': 'carbon-nanotube@L0',
        'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'nitrogenContent_atPct': [1, 5],
            'electronicCharacter': 'n-type vs pristine (donor states '
                                   'near the Fermi level)',
            'effectOnConductivity': 'work-function decrease, improved '
                                    'electron transfer; magnitude '
                                    'site-type dependent',
            'siteTypes': ['pyridinic', 'pyrrolic', 'graphitic'],
        }),
        'provenance_id': PROV,
        'notes': 'Deltas on the pristine tube (see lineage); largely '
                 'qualitative in the literature — quantify per '
                 'synthesis route when samples exist.',
    },
    {
        'name': 'n-doped-carbon-nanotube@L4',
        'material_name': 'n-doped-carbon-nanotube',
        'scale_level': 4, 'scale_category': 'quantum',
        'definition_class': 'DFTModelDefinition',
        'definition_ref': 'doped-cnt-fragment-energy',
        'status': 'partial',
        'derived_from_name': 'carbon-nanotube@L4',
        'derivation_method': 'dft-parameterized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Executable: pyridine as the pyridinic-N-doped '
                 'fragment, directly comparable to the pristine '
                 'benzene fragment (partial until executed).',
    },
]


# ---------------------------------------------------------------------
# msci-20b: silicon + the Bombastic-Laser-CNC nanoparticle family
# (Dustin's notebook, 06-Bombastic-Laser-CNC — provenance = the pages).
# ---------------------------------------------------------------------

PROV_BLCNC = 'prov-notebook-blcnc-04-05'   # 04-Nanoparticle-Wax-Composites
                                           # + 05-Synthesis-And-Filtration

SEED_STANDARD_MATERIALS += [
    {
        'name': 'silicon',
        'display_name': 'Silicon (crystalline)',
        'description': (
            'Single-crystal silicon — the reference semiconductor and '
            'a Si source/target in the laser-CNC context (SiOx '
            'nanoparticles ablate from it).'
        ),
        'material_kind': 'pure',
        'element_symbols_json': '["Si"]',
        'provenance_id': PROV,
        'notes': 'Literature-typical values for (100) c-Si.',
    },
    {
        'name': 'feox-nanoparticle',
        'display_name': 'FeOx (Ferrite) Nanoparticles',
        'description': (
            'Iron-oxide (ferrite, FexOx) nanoparticles — THE workhorse '
            'absorber of the Bombastic-Laser-CNC composites: created '
            'by LASiS (Laser Ablation in a Solution) with the BLA in '
            'PURE WATER; spherical with a (r_min, r_max) size range '
            'the LASiS analysis is to determine; "minimalistic '
            'self-structuring" in the layer recipes.'
        ),
        'material_kind': 'pure',
        'element_symbols_json': '["Fe", "O"]',
        'provenance_id': PROV_BLCNC,
        'notes': 'Notebook: IMG_2987 (synthesis route), IMG_2991 '
                 '(layer roles), IMG_2992 (size-range definition '
                 '2*r_max-FeOx = D_FeOx). Bulk-phase numbers below are '
                 'literature magnetite (Fe3O4) stand-ins until LASiS '
                 'batches are measured.',
    },
    {
        'name': 'siox-nanoparticle',
        'display_name': 'SiOx Nanoparticles',
        'description': (
            'Silica nanoparticles — a wavelength-tuned constituent of '
            'the generic composite recipe (option 7): (N%) SiOx '
            'alongside FeOx and CuOx.'
        ),
        'material_kind': 'pure',
        'element_symbols_json': '["Si", "O"]',
        'provenance_id': PROV_BLCNC,
        'notes': 'Notebook: IMG_2991 option 7, IMG_2992 size-range '
                 'definition. LASiS-produced, spherical assumption.',
    },
    {
        'name': 'cuox-nanoparticle',
        'display_name': 'CuOx Nanoparticles',
        'description': (
            'Copper-oxide nanoparticles — a wavelength-tuned '
            'constituent of the generic composite recipe (option 7); '
            'strong visible/NIR absorption makes CuOx a natural '
            'λ-tuning candidate.'
        ),
        'material_kind': 'pure',
        'element_symbols_json': '["Cu", "O"]',
        'provenance_id': PROV_BLCNC,
        'notes': 'Notebook: IMG_2991 option 7, IMG_2992 size-range '
                 'definition (2*r_max-CuOx = D_CuOx).',
    },
    {
        'name': 'c-nanoparticle',
        'display_name': 'Carbon Nanoparticles',
        'description': (
            'Carbon nanoparticles — the (r_min-C, r_max-C) type in the '
            'notebook size analysis; broadband absorber candidate in '
            'the λ-tuned layer recipes.'
        ),
        'material_kind': 'pure',
        'element_symbols_json': '["C"]',
        'provenance_id': PROV_BLCNC,
        'notes': 'Notebook: IMG_2992. Distinct from carbon-nanotube: '
                 'spherical LASiS particles, not tubes.',
    },
    {
        'name': 'nanoparticle-wax-composite',
        'display_name': 'Nanoparticle Wax Composite (BLCNC layers)',
        'description': (
            'The thin-film wax + nanoparticle composite family for '
            'precision laser melts: layer recipes 1-7 from the '
            'notebook (pure wax; 100% FeOx; 10/90, 30/60, 60/30 '
            'FeOx/λ-tuned; 100% λ-tuned unstructured; dynamically '
            'tuned generic FeOx+SiOx+CuOx+C). Controlling the layers '
            'controls the CONTROL SPACE and PROBABILITY SPACE of the '
            'response to particular laser wavelengths.'
        ),
        'material_kind': 'composite',
        'element_symbols_json': '["C", "H", "O", "Fe", "Si", "Cu"]',
        'provenance_id': PROV_BLCNC,
        'notes': 'Notebook: IMG_2990 (control/probability space), '
                 'IMG_2991 (recipes), IMG_2992 (min layer depth = wax '
                 'crystallization ~1 um; rosin/wax-rosin shifts it).',
    },
]

SEED_STANDARD_FEM_MODELS += [
    {
        'name': 'silicon-slab-conduction',
        'display_name': 'Silicon — steady conduction (unit slab)',
        'description': (
            'Steady conduction through crystalline silicon (k=149 '
            'W/m*K at 300 K, literature) on the unit demo slab — the '
            'level-1 engine path.'
        ),
        'physics_ref': 'fem-steady-conduction',
        'domain_json': json.dumps({'shape': 'unit-square'}),
        'materials_json': json.dumps({
            'domain': {'thermalConductivity': 149.0}}),
        'boundary_conditions_json': json.dumps([
            {'boundary': 'all', 'type': 'dirichlet', 'value': 0}]),
        'source_terms_json': json.dumps({'heatSource': 1.0}),
        'mesh_json': json.dumps({'refine': 4}),
        'solver_json': '{}',
        'notes': f'{PROV}.',
        'enabled': True,
    },
    {
        'name': 'feox-wax-composite',
        'display_name': 'FeOx/wax composite — effective conductivity '
                        '(recipe option 3 fraction)',
        'description': (
            'Beeswax-order matrix (k=0.25 W/m*K) with 10 vol% FeOx '
            'nanoparticle inclusions (magnetite literature k~=6 '
            'W/m*K) — the notebook\'s option-3 minimal-FeOx recipe as '
            'a thermal bound. Same isotropic 2D unit-cell caveats as '
            'every homogenization here; the REAL interest (laser '
            'absorption / melt probability space) needs an optical '
            'model the engines do not have yet — stated, not faked.'
        ),
        'physics_ref': 'fem-effective-conductivity',
        'domain_json': json.dumps({
            'shape': 'unit-square',
            'inclusion': {'shape': 'circle', 'volumeFraction': 0.10},
        }),
        'materials_json': json.dumps({
            'matrix': {'thermalConductivity': 0.25},
            'inclusion': {'thermalConductivity': 6.0},
        }),
        'boundary_conditions_json': json.dumps([
            {'boundary': 'x-faces', 'type': 'dirichlet',
             'value': 'unit temperature difference'}]),
        'source_terms_json': '{}',
        'mesh_json': json.dumps({'refine': 5}),
        'solver_json': '{}',
        'notes': f'{PROV_BLCNC} + {PROV} for the magnetite k.',
        'enabled': True,
    },
]

SEED_STANDARD_DFT_MODELS += [
    {
        'name': 'silicon-bulk-structure',
        'display_name': 'Silicon — bulk diamond-cubic structure (ASE)',
        'description': (
            'Crystalline silicon bulk structure: diamond cubic, '
            'a=5.431 A — structural facts via the ASE structure layer '
            '(available in-image; no SCF needed).'
        ),
        'calculation_ref': 'dft-bulk-structure',
        'structure_json': json.dumps({
            'kind': 'bulk', 'symbol': 'Si', 'crystal': 'diamond',
            'latticeA': 5.431}),
        'method_json': '{}',
        'accuracy_json': '{}',
        'notes': f'{PROV}: textbook lattice constant.',
        'enabled': True,
    },
]

SEED_STANDARD_SCALE_DEFINITIONS += [
    # ---- silicon ----------------------------------------------------
    {
        'name': 'silicon@L0',
        'material_name': 'silicon',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'density_gcm3': 2.329,
            'thermalConductivity_WmK': 149.0,
            'meltingPoint_C': 1414,
            'bandgap_eV': 1.12,
            'bandgapType': 'indirect',
            'youngsModulus_GPa': [130, 188],
            'modulusNote': 'orientation-dependent (100)-(111)',
        }),
        'provenance_id': PROV,
        'notes': 'c-Si literature values at 300 K.',
    },
    {
        'name': 'silicon@L1',
        'material_name': 'silicon',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'FEMModelDefinition',
        'definition_ref': 'silicon-slab-conduction',
        'status': 'partial',
        'derived_from_name': 'silicon@L0',
        'derivation_method': 'homogenized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Executable unit-slab conduction (partial until run).',
    },
    {
        'name': 'silicon@L4',
        'material_name': 'silicon',
        'scale_level': 4, 'scale_category': 'quantum',
        'definition_class': 'DFTModelDefinition',
        'definition_ref': 'silicon-bulk-structure',
        'status': 'partial',
        'derivation_method': 'dft-parameterized',
        'parameters_json': '{}',
        'provenance_id': PROV,
        'notes': 'Executable NOW via the ASE structure layer '
                 '(structural facts); the SCF total energy upgrades '
                 'this row once the WITH_QE build exists '
                 '(dft-total-energy).',
    },
    # ---- FeOx nanoparticles ------------------------------------------
    {
        'name': 'feox-nanoparticle@L0',
        'material_name': 'feox-nanoparticle',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'synthesisRoute': 'LASiS via BLA in pure water '
                              '(notebook IMG_2987)',
            'shapeAssumption': 'spherical',
            'sizeRange_nm': None,
            'sizeRangeNote': '(r_min-FeOx, r_max-FeOx) TO BE MEASURED '
                             'from LASiS batches; 2*r_max = D_FeOx '
                             'bounds the min layer depth (IMG_2992)',
            'bulkPhaseStandIn': 'magnetite Fe3O4',
            'densityBulk_gcm3': 5.17,
            'thermalConductivityBulk_WmK': 6.0,
            'curieTemperature_C': 585,
            'opticalRole': 'broadband absorber; "minimalistic '
                           'self-structuring" layer constituent',
        }),
        'provenance_id': PROV_BLCNC,
        'notes': 'The size range is the KEY unmeasured quantity — the '
                 'notes define its shape, the LASiS analysis fills it.',
    },
    # ---- SiOx / CuOx / C nanoparticles (size-range rows) --------------
    {
        'name': 'siox-nanoparticle@L0',
        'material_name': 'siox-nanoparticle',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'synthesisRoute': 'LASiS (planned, per notebook)',
            'shapeAssumption': 'spherical',
            'sizeRange_nm': None,
            'sizeRangeNote': '(r_min-SiOx, r_max-SiOx) to be measured; '
                             '2*r_max = D_SiOx',
            'bulkPhaseStandIn': 'amorphous silica',
            'densityBulk_gcm3': 2.2,
            'opticalRole': 'wavelength-tuned constituent (option 7)',
        }),
        'provenance_id': PROV_BLCNC,
        'notes': '',
    },
    {
        'name': 'cuox-nanoparticle@L0',
        'material_name': 'cuox-nanoparticle',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'synthesisRoute': 'LASiS (planned, per notebook)',
            'shapeAssumption': 'spherical',
            'sizeRange_nm': None,
            'sizeRangeNote': '(r_min-CuOx, r_max-CuOx) to be measured; '
                             '2*r_max = D_CuOx',
            'bulkPhaseStandIn': 'tenorite CuO',
            'densityBulk_gcm3': 6.31,
            'opticalRole': 'wavelength-tuned constituent; strong '
                           'visible/NIR absorption',
        }),
        'provenance_id': PROV_BLCNC,
        'notes': '',
    },
    {
        'name': 'c-nanoparticle@L0',
        'material_name': 'c-nanoparticle',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'MeasuredProperties', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'synthesisRoute': 'LASiS (planned, per notebook)',
            'shapeAssumption': 'spherical',
            'sizeRange_nm': None,
            'sizeRangeNote': '(r_min-C, r_max-C) to be measured',
            'bulkPhaseStandIn': 'amorphous carbon',
            'densityBulk_gcm3': [1.8, 2.1],
            'opticalRole': 'broadband absorber candidate',
        }),
        'provenance_id': PROV_BLCNC,
        'notes': '',
    },
    # ---- the composite family (recipes + executable thermal bound) ----
    {
        'name': 'nanoparticle-wax-composite@L0',
        'material_name': 'nanoparticle-wax-composite',
        'scale_level': 0, 'scale_category': 'experimental',
        'definition_class': 'LayerRecipes', 'definition_ref': '',
        'status': 'partial', 'derivation_method': 'literature',
        'parameters_json': json.dumps({
            'purpose': 'precision laser melts — tune the control/'
                       'probability space of heating+melting per '
                       'thin-film layer',
            'minLayerDepth_um': 1.0,
            'minLayerDepthNote': 'wax crystallization size; varies by '
                                 'wax, shifts for rosin / wax-rosin '
                                 'macro composites (IMG_2992)',
            'layerOptions': [
                {'id': 1, 'recipe': 'pure wax'},
                {'id': 2, 'recipe': '100% FeOx nanoparticle composite',
                 'character': 'minimalistic self-structuring'},
                {'id': 3, 'recipe': '10% FeOx / 90% single-type '
                                    'wavelength-tuned nanoparticle'},
                {'id': 4, 'recipe': '30% FeOx / 60% single-type '
                                    'wavelength-tuned',
                 'character': 'moderately packed structure'},
                {'id': 5, 'recipe': '60% FeOx / 30% wavelength-tuned',
                 'character': 'heavily packed structured'},
                {'id': 6, 'recipe': '100% wavelength-tuned '
                                    'nanoparticle, unstructured/random',
                 'character': 'unstructured nano composite'},
                {'id': 7, 'recipe': '(10-100%) FeOx + (N%) SiOx + '
                                    '(N%) CuOx + (N%) C',
                 'character': 'dynamically tuned (generic) — the form '
                              'simulations analyze for realistic melt '
                              'profiles'},
            ],
            'baseLayerStrategies': [
                'catch-all: all nanoparticle types in even proportions '
                '(absorbs everything, for speed)',
                'absolute precision: pure-wax base, single-nanoparticle '
                'tuned layers above',
            ],
        }),
        'provenance_id': PROV_BLCNC,
        'notes': 'Recipes transcribed from IMG_2990/2991/2992.',
    },
    {
        'name': 'nanoparticle-wax-composite@L1',
        'material_name': 'nanoparticle-wax-composite',
        'scale_level': 1, 'scale_category': 'continuum',
        'definition_class': 'FEMModelDefinition',
        'definition_ref': 'feox-wax-composite',
        'status': 'partial',
        'derived_from_name': 'nanoparticle-wax-composite@L0',
        'derivation_method': 'homogenized',
        'parameters_json': '{}',
        'provenance_id': PROV_BLCNC,
        'notes': 'Executable THERMAL bound for the option-3 FeOx '
                 'fraction; the optical/melt-probability model the '
                 'notes actually want needs an absorption engine — an '
                 'honest gap for the BLCNC work.',
    },
]
