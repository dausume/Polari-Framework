"""
@module electrodevice.photo_basis

CNT / sol-gel PHOTO devices (Dustin 2026-07-10): (A) a photo-sensor
TUNED to a target wavelength via nanoparticle shape+composition (the
acene fragment ladder — size closes the pi gap; doping shifts it) and
orientation (aligned absorbers couple to polarization); (B) a
thin-film SOLAR STACK from common/community materials, its layers as
rows with structured property records and honest gaps.

@consumers
  - electrodevice.custom.photo_derive (tuning + stack optimization)
  - electrodevice.device_api (knob surface)
  - polariServer (registration + seed)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PhotoAbsorberDefinition(treeObject):
    """One tunable absorber: candidates (fragment sims and/or
    literature-gap records) + the target-wavelength knob + the
    orientation knob. Tuning EXECUTES the candidate sims and picks
    the best absorption-edge match."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # THE TUNING KNOB: what light this sensor is for.
        target_wavelength_nm: float = 450.0,
        # JSON list of candidates: {name, simModel} (executed) or
        # {name, gapRecord: {value_ev, ...structured record}}.
        candidates_json: str = '[]',
        # Orientation knob: 'aligned' absorbers (drawn CNT films /
        # rubbed acenes) couple ~cos^2(theta) to the polarization;
        # 'random' averages to 1/3.
        orientation: str = 'aligned',
        polarization_angle_deg: float = 0.0,
        # Derived by the tune act:
        chosen_candidate: str = '',
        chosen_gap_ev: float = 0.0,
        absorption_edge_nm: float = 0.0,
        match_error_nm: float = 0.0,
        orientation_factor: float = 0.0,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.target_wavelength_nm = target_wavelength_nm
        self.candidates_json = candidates_json
        self.orientation = orientation
        self.polarization_angle_deg = polarization_angle_deg
        self.chosen_candidate = chosen_candidate
        self.chosen_gap_ev = chosen_gap_ev
        self.absorption_edge_nm = absorption_edge_nm
        self.match_error_nm = match_error_nm
        self.orientation_factor = orientation_factor
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes


class SolarLayerDefinition(treeObject):
    """One layer of the thin-film stack — a knob row: role, material,
    thickness, and the property this layer is chosen FOR (structured
    record or an honest named gap)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        stack_name: str = '',
        position: int = 0,
        role: str = '',
        material: str = '',
        thickness_m: float = 0.0,
        # The property that justifies the layer (structured record) —
        # or {} with the gap named in notes.
        key_property_json: str = '{}',
        community_source: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.stack_name = stack_name
        self.position = position
        self.role = role
        self.material = material
        self.thickness_m = thickness_m
        self.key_property_json = key_property_json
        self.community_source = community_source
        self.notes = notes


class SolarStackDefinition(treeObject):
    """The panel: ordered layers + the absorber-selection knob.
    The optimize act ranks candidate absorbers by blackbody ultimate
    efficiency and stamps the choice + honest loss notes."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # JSON list of absorber candidates:
        # {name, gapRecord | simModel, demonstrated?, caveats?}.
        absorber_candidates_json: str = '[]',
        # KNOB: what picks the absorber — 'sq-limit' (the physics
        # ceiling) | 'demonstrated' (what has actually produced
        # power in someone's hands). Disagreement -> a suggestion.
        selection_policy: str = 'sq-limit',
        chosen_absorber: str = '',
        chosen_gap_ev: float = 0.0,
        ultimate_efficiency: float = 0.0,
        derived_at: str = '',
        provenance_json: str = '{}',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.absorber_candidates_json = absorber_candidates_json
        self.selection_policy = selection_policy
        self.chosen_absorber = chosen_absorber
        self.chosen_gap_ev = chosen_gap_ev
        self.ultimate_efficiency = ultimate_efficiency
        self.derived_at = derived_at
        self.provenance_json = provenance_json
        self.notes = notes


import json as _json

SEED_PHOTO_ABSORBERS = [
    {'name': 'blue-laser-sensor-absorber',
     'target_wavelength_nm': 450.0,
     'orientation': 'aligned', 'polarization_angle_deg': 0.0,
     'candidates_json': _json.dumps([
         {'name': 'benzene-1ring', 'simModel': 'cnt-fragment-energy'},
         {'name': 'naphthalene-2ring',
          'simModel': 'cnt-fragment-energy-l2'},
         {'name': 'anthracene-3ring',
          'simModel': 'acene3-fragment-energy'},
         {'name': 'tetracene-4ring',
          'simModel': 'acene4-fragment-energy'},
         {'name': 'b-doped-ring',
          'simModel': 'p-doped-cnt-fragment-energy'},
     ]),
     'notes': 'Blue laser (~450 nm) sensor: acene length is the '
              'shape knob, doping the composition knob.'},
]

#: The community thin-film stack, front to back. Property records
#: are structured (value + context + confidence); absent data is an
#: honestly named gap, not a silent default.
SEED_SOLAR_LAYERS = [
    {'name': 'community-panel-L0-cover', 'stack_name':
     'community-thin-film-panel', 'position': 0,
     'role': 'front cover glass', 'material': 'bio-fused-silica',
     'thickness_m': 2e-3,
     'key_property_json': _json.dumps({'refractiveIndex': {
         'value': 1.46, 'wavelength_nm': 550,
         'measurement_method': 'literature',
         'confidence': 'high'}}),
     'community_source': 'rice-husk / diatom silica glass',
     'notes': 'Weather barrier; n 1.46 sets the first reflection.'},
    {'name': 'community-panel-L1-ar', 'stack_name':
     'community-thin-film-panel', 'position': 1,
     'role': 'anti-reflection coating',
     'material': 'sol-gel-silica (porous)', 'thickness_m': 1e-7,
     'key_property_json': _json.dumps({'refractiveIndex': {
         'value': 1.22, 'wavelength_nm': 550,
         'measurement_method': 'literature',
         'confidence': 'medium'}}),
     'community_source': 'the SAME sol-gel, dried porous — porosity '
                         'is the index knob',
     'notes': 'Quarter-wave at ~550 nm: t = 550/(4*1.22) ~ 113 nm; '
              'n_ideal = sqrt(1.46) ~ 1.21 — porous silica IS the '
              'classic AR coating.'},
    {'name': 'community-panel-L2-tco', 'stack_name':
     'community-thin-film-panel', 'position': 2,
     'role': 'transparent electrode',
     'material': 'sparse CNT network in sol-gel binder',
     'thickness_m': 5e-8,
     'key_property_json': _json.dumps({'sheetTransparency': {
         'value': 0.85, 'wavelength_nm': 550,
         'measurement_method': 'literature (sparse CNT films)',
         'confidence': 'medium'}}),
     'community_source': 'the SAME percolation system near '
                         'threshold: barely-connected network = '
                         'conductive AND transparent',
     'notes': 'vf just above 0.5 vol% — the percolation model gives '
              'the conductivity side; transparency needs a new '
              'measured/derived record (named gap).'},
    {'name': 'community-panel-L3-etl', 'stack_name':
     'community-thin-film-panel', 'position': 3,
     'role': 'electron transport / buffer',
     'material': 'bio-zinc-oxide', 'thickness_m': 5e-8,
     'key_property_json': _json.dumps({'bandGap': {
         'value': 3.3, 'unit': 'eV',
         'measurement_method': 'literature',
         'confidence': 'high'}}),
     'community_source': 'bio-synthesized ZnO (published routes)',
     'notes': 'Gap 3.3 eV: transparent to visible, passes electrons '
              '- the standard ETL.'},
    {'name': 'community-panel-L4-absorber', 'stack_name':
     'community-thin-film-panel', 'position': 4,
     'role': 'absorber', 'material': 'chosen by the optimize act',
     'thickness_m': 2e-6, 'key_property_json': '{}',
     'community_source': 'see absorber candidates on the stack row',
     'notes': 'The optimize act stamps the choice + ultimate '
              'efficiency.'},
    {'name': 'community-panel-L5-htl', 'stack_name':
     'community-thin-film-panel', 'position': 5,
     'role': 'hole transport / back contact',
     'material': 'dense CNT/graphite paste + copper',
     'thickness_m': 1e-5,
     'key_property_json': _json.dumps({'sheetConductivity': {
         'value': 227.27, 'unit': 'S/m',
         'measurement_method': 'derived '
                               '(cnt-solgel-percolation @2vol%)',
         'confidence': 'medium'}}),
     'community_source': 'the SAME CNT composite, dense; copper '
                         'foil/wire back bus',
     'notes': 'The 2 vol% percolation conductivity, reused.'},
]


SEED_SOLAR_STACKS = [
    {'name': 'community-thin-film-panel',
     'selection_policy': 'sq-limit',
     'absorber_candidates_json': "[{\"name\": \"cuprous-oxide\", \"gapRecord\": {\"value\": 2.1, \"unit\": \"eV\", \"measurement_method\": \"literature\", \"confidence\": \"high\"}, \"source\": \"Cu2O: torched copper sheet \\u2014 THE classic homemade cell\", \"demonstrated\": {\"value\": 0.081, \"context\": \"lab record ~8.1% (Minami et al. 2016, engineered stack); homemade torched-copper cells ~1%\", \"confidence\": \"high\"}}, {\"name\": \"pyrite-FeS2\", \"gapRecord\": {\"value\": 0.95, \"unit\": \"eV\", \"measurement_method\": \"literature\", \"confidence\": \"high\"}, \"source\": \"iron + sulfur, earth-abundant; films by sulfurizing iron foil (low-tech)\", \"demonstrated\": {\"value\": 0.028, \"context\": \"record ~2.8% photoelectrochemical (Hahn-Meitner, 1990s); solid-state thin films <1% \\u2014 no commercial cell exists\", \"confidence\": \"high\"}, \"caveats\": [{\"kind\": \"voc-deficit\", \"note\": \"open-circuit voltage stalls ~0.2 V where ~0.5+ V is expected \\u2014 the famous unsolved pyrite puzzle (sulfur vacancies / surface inversion / phase impurities); absorption and gap are superb, photoVOLTAGE is the research problem\"}, {\"kind\": \"phase-purity\", \"note\": \"sulfur-poor phases (marcasite, pyrrhotite, troilite) are metallic recombination shorts \\u2014 needs sulfur-rich atmosphere and >~400 C\"}, {\"kind\": \"recommended-use\", \"note\": \"today: photodetector/photoconductor (the voltage deficit does not kill photoconductivity) and a research absorber; NOT a working community power cell yet\"}]}, {\"name\": \"zinc-oxide\", \"gapRecord\": {\"value\": 3.3, \"unit\": \"eV\", \"measurement_method\": \"literature\", \"confidence\": \"high\"}, \"source\": \"bio-ZnO (UV-only \\u2014 expected to rank poorly)\"}, {\"name\": \"tetracene-organic\", \"simModel\": \"acene4-fragment-energy\", \"source\": \"the acene-4 fragment \\u2014 organic thin film\", \"demonstrated\": {\"value\": 0.01, \"context\": \"single-junction acene organics: low single digits at best\", \"confidence\": \"low\"}}, {\"name\": \"anthocyanin-dye-tio2\", \"gapRecord\": {\"value\": 2.2, \"unit\": \"eV\", \"measurement_method\": \"literature (DSSC berry dyes)\", \"confidence\": \"low\"}, \"source\": \"berry-dye sensitized route (community DSSC)\", \"demonstrated\": {\"value\": 0.01, \"context\": \"berry-dye community DSSCs ~0.5-1%; engineered dyes reach ~13%\", \"confidence\": \"medium\"}}]",
     'notes': 'Optimize ranks by the detailed-balance (SQ) limit and reports demonstrated efficiencies + caveats; the selection_policy knob chooses which one picks.'},
]
