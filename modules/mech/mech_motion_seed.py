"""
@module mech.mech_motion_seed

mxc-4 seeds: the mfx-3 drawer cassette's load cases, motion cases, the
one SimulationDefinition every polari motion run rides, and the legacy
wooden-runner contact the comparison variant names. Names follow the
mxc-2 naming contract: assembly `mfx-3-drawer-cassette`, joint
`mfx-3-slide` (slider, 0–250 mm, dof ['tz']), instances `drawer-box`,
`slide-left`, `slide-right`.

Hand-checkable numbers (mech_motion_selftest pins them):
  box 1.2 kg + 8 bins × 0.180 kg = 2.64 kg → W = 25.89 N
  bins on a 4 × 2 grid of 42 mm cells behind the front edge:
    x = −21, −63, −105, −147 mm (two bins each, y = ±21)
  moment about the front edge at full extension (250 mm):
    box: 11.768 N × 0.125 m = 1.471 N·m
    bins: 3.532 N × (0.229 + 0.187 + 0.145 + 0.103) = 2.345 N·m  → 3.816 N·m

Every μ and rating is a KNOB (basis says so) until a measured run lands.

@consumers polariServer (seed_pairs), mech.mech_motion_selftest
"""
import json

from mech.mech_motion_basis import MOTION_SIM_DEF

PROV = 'mxc-4'
ASSEMBLY = 'mfx-3-drawer-cassette'
JOINT = 'mfx-3-slide'
LEGACY_CONTACT = 'mfx-3-wooden-runner'

BOX_MASS_KG = 1.2
BIN_MASS_KG = 0.180
CELL_MM = 42.0
DRAWER_DEPTH_MM = 300.0

#: Knobs the drawer runs read (motion_runs.DEFAULT_KNOBS overridden here).
MOTION_KNOBS = {
    'hand_effort_n': 20.0,
    'detent_hold_n': 2.0,
    'smooth_jerk_m_s3': 500.0,
    'detent': {'force': 3.0, 'width': 4.0,
               'basis': 'knob — typical ball-slide self-close detent, unmeasured'},
    'drawer_depth_mm': DRAWER_DEPTH_MM,
}

#: Friction knobs by running gear (plan §4: ball slide 0.01–0.03,
#: wood-on-wood 0.25–0.5; all knobs until measured).
BALL_SLIDE_MU = {'static': 0.03, 'kinetic': 0.02, 'basis': 'knob — steel ball slide, plan §4 band 0.01–0.03'}
WOOD_RUNNER_MU = {'static': 0.50, 'kinetic': 0.35, 'basis': 'knob — wood-on-wood, plan §4 band 0.25–0.5'}


def _bins():
    out = []
    n = 0
    for col in range(4):
        for row in (-1, 1):
            n += 1
            out.append({
                'instance': f'bin-{n}', 'kind': 'mass', 'value': BIN_MASS_KG,
                'point_json': {'x_mm': -(CELL_MM / 2 + col * CELL_MM), 'y_mm': row * CELL_MM / 2, 'z_mm': 20.0},
                'basis': 'knob — 180 g contents per Gridfinity bin, cell centre',
            })
    return out


_BOX = {'instance': 'drawer-box', 'kind': 'mass', 'value': BOX_MASS_KG,
        'point_json': {'x_mm': -125.0, 'y_mm': 0.0, 'z_mm': 10.0},
        'basis': 'knob — printed box + front + baseplate, COM mid-depth'}

SEED_MECH_LOAD_CASES = [
    {
        'name': 'mfx-3-empty', 'assembly_ref': ASSEMBLY,
        'loads_json': json.dumps([_BOX]), 'resultant_json': '{}',
        'notes': 'the drawer box alone (unloaded case)',
    },
    {
        'name': 'mfx-3-8-bins', 'assembly_ref': ASSEMBLY,
        'loads_json': json.dumps([_BOX] + _bins()), 'resultant_json': '{}',
        'notes': '8 Gridfinity bins × 180 g on a 4 × 2 grid behind the front edge + the box',
    },
]

_CHECKS_PULL = [
    {'name': 'opens fully', 'criterion': 'q_max ≥ length_max', 'knob': None},
    {'name': 'smooth', 'criterion': 'peak jerk < knob', 'knob': 500.0},
    {'name': 'no bind', 'criterion': 'side force < slide dynamic rating', 'knob': None},
    {'name': 'hand effort', 'criterion': 'minimum pull to open fully within duration < knob', 'knob': 20.0},
    {'name': 'stays closed', 'criterion': 'detent force > knob', 'knob': 2.0},
]

SEED_MECH_MOTION_CASES = [
    {
        'name': 'open-position-100t', 'assembly_ref': ASSEMBLY, 'joint_ref': JOINT,
        'drive': 'position', 'formula': '100*time', 'force_n': -1.0, 'torque_nm': -1.0,
        'duration_s': 1.5, 'step_s': 0.1,
        'checks_json': json.dumps([
            {'name': 'hand effort', 'criterion': 'force to follow the formula < knob', 'knob': 20.0},
            {'name': 'no bind', 'criterion': 'side force < slide dynamic rating', 'knob': None},
        ]),
        'contact_ref': '', 'running_gear': 'slide',
        'notes': 'the FreeCAD Motion probe (custom/reference/mfx0_motion_econ.csv): 100 mm/s for 1.5 s, 0.1 s frames',
    },
    {
        'name': 'open-pull-5n', 'assembly_ref': ASSEMBLY, 'joint_ref': JOINT,
        'drive': 'force', 'formula': '', 'force_n': 5.0, 'torque_nm': -1.0,
        'duration_s': 1.5, 'step_s': 0.01, 'checks_json': json.dumps(_CHECKS_PULL),
        'contact_ref': '', 'running_gear': 'slide',
        'notes': 'unloaded drawer, 5 N constant pull on the ball slides',
    },
    {
        'name': 'open-pull-loaded', 'assembly_ref': ASSEMBLY, 'joint_ref': JOINT,
        'drive': 'force', 'formula': '', 'force_n': 20.0, 'torque_nm': -1.0,
        'duration_s': 1.5, 'step_s': 0.01, 'checks_json': json.dumps(_CHECKS_PULL),
        'contact_ref': '', 'running_gear': 'slide',
        'notes': 'loaded drawer (mfx-3-8-bins) at the 20 N hand-effort knob; the report states the minimum pull',
    },
    {
        'name': 'legacy-wooden-runner', 'assembly_ref': ASSEMBLY, 'joint_ref': JOINT,
        'drive': 'force', 'formula': '', 'force_n': 20.0, 'torque_nm': -1.0,
        'duration_s': 1.5, 'step_s': 0.01, 'checks_json': json.dumps(_CHECKS_PULL),
        'contact_ref': LEGACY_CONTACT, 'running_gear': 'runner',
        'notes': ('no slide: the box rides fixed wooden runners (μ 0.35 contact); the cantilever moment '
                  'becomes a couple at the cabinet edge, so friction grows with extension'),
    },
]

#: The one MechContact this slice adds (kind sliding, the wood-on-wood μ)
#: — the legacy variant's contact. The ball-slide contacts come from the
#: mxc-2 assembly seed.
SEED_MECH_MOTION_CONTACTS = [
    {
        'name': LEGACY_CONTACT, 'assembly_ref': ASSEMBLY,
        'kind': 'sliding', 'instance_a': 'drawer-box', 'instance_b': 'cabinet',
        'mu_json': json.dumps(WOOD_RUNNER_MU),
        'notes': 'legacy variant: wooden runner, no slide (D-mxc-5)',
    },
]

#: The SimulationDefinition every polari motion run is a SimulationRun of.
SEED_MECH_SIM_DEFINITIONS = [
    {
        'name': MOTION_SIM_DEF,
        'description': ('mech 1-DOF rigid-body motion (linear or rotary): M·q̈ = F_drive − F_friction − c·q̇ '
                        '− F_detent − F_load. Steps are landed by mech.custom.motion_engine (Python), not by '
                        'the no-code step runner; this row names the class the series reader walks.'),
        'intent': 'validate',
        'participating_sim_state_classes_json': json.dumps(['MechMotionSimState']),
        'time_step_seconds': 0.01, 'duration_seconds': 1.5, 'recording_interval_steps': 1,
        'initial_conditions_overrides_json': '{}',
        'parameters_json': json.dumps({'g': 9.80665}),
        'termination_predicate': '', 'time_unit': 'second',
    },
]

#: Runs are never seeded — they are made by motion_runs.run_polari.
SEED_MECH_MOTION_RUNS = []


# ---------------------------------------------------------------
# the mfx-3 fixture itself (plan §4 mxc-4: one drawer cassette — 2 slides,
# drawer box, front, handle, a 2×3 baseplate inside). Catalogue variants
# from mxc-1; the drawer box / front / handle are GENERATED parts (mxc-5)
# and carry no variant yet. Ground = the cabinet frame member.
# ---------------------------------------------------------------

def _j(o):
    return json.dumps(o)


def _inst(name, variant, origin, role='body', notes=''):
    return {'name': name, 'assembly_ref': ASSEMBLY, 'variant_ref': variant,
            'component_ref': f'pc-mech-{variant or name}',
            'placement_json': _j({'origin': list(origin), 'rotation': [1, 0, 0, 0],
                                  'placement_basis': 'given'}),
            'material_option_ref': '', 'quantity_role': role, 'quantity': 1,
            'notes': notes, 'is_prior': True, 'provenance_id': PROV}


SEED_MECH_MOTION_ASSEMBLIES = [
    {'name': ASSEMBLY, 'display_name': 'mfx-3: drawer cassette (2 slides, box, 2x3 baseplate)',
     'kind': 'drawer_cassette', 'system_ref': '', 'node_ref': 'node-mfx-3',
     'ground_instance': 'cabinet',
     'parameters_json': _j({'drawer_load_n': 25.89, 'extension_mm': 250, 'n_slides': 2,
                            'grid_x': 3, 'grid_y': 2, 'depth_mm': DRAWER_DEPTH_MM}),
     'generator': '', 'generator_version': '',
     'notes': 'the mxc-4 fixture: the drawer rides ONE slider joint (dof tz, 0-250 mm) on the '
              'left slide; the right slide is fixed to the cabinet (one rigid group with it) and '
              'touches the drawer through a contact row only. DOF count: mobility 1 (the slider), '
              'drawer-box + baseplate one rigid group. drawer_load_n = box + 8 bins.',
     'provenance': 'MECH_FREECAD_INTERCHANGE_PLAN §4 mxc-4', 'is_prior': True, 'provenance_id': PROV},
]

SEED_MECH_MOTION_INSTANCES = [
    _inst('cabinet', 'extrusion-2040-L300', (0, 0, 0), role='frame',
          notes='stand-in cabinet side member (a 2040 profile); the full cabinet comes with the mxc-5 generator'),
    _inst('slide-left', 'drawer-slide-L300', (0, -45, 0)),
    _inst('slide-right', 'drawer-slide-L300', (0, 45, 0)),
    _inst('drawer-box', '', (0, 0, 0),
          notes='GENERATED part (mxc-5 drawer box, 3 mm PLA or 6 mm plywood bottom) — no catalogue variant'),
    _inst('baseplate', 'gridfinity-baseplate-2x2', (0, 0, 5),
          notes='2x2 stand-in until the catalogue carries a 3x2 baseplate variant'),
]

SEED_MECH_MOTION_JOINTS = [
    {'name': 'mfx-3-slide-left-mount', 'assembly_ref': ASSEMBLY, 'kind': 'fixed',
     'instance_a': 'cabinet', 'feature_a': 'extrusion-2040-L300:slot:+y:0',
     'instance_b': 'slide-left', 'feature_b': '',
     'interface_ref': 'if-mfx-3-slide-left-mount', 'dof_json': '[]',
     'limits_json': '{"positions": 4}',
     'ratio': 0.0, 'preload_json': '{}', 'fastener_refs_json': '[]', 'valid': True,
     'invalid_reason': '', 'notes': 'slide screwed to the cabinet through drawer-slide-L300:holes:cabinet '
     'with 4 x M4 T-nuts in the slot (positions: 4 -> a full fix); the fasteners are not instanced here '
     'and the slide face has no extrusion-face counterpart in the catalogue, so feature_b is HONESTLY '
     'empty rather than a slot<->face pair that cannot match',
     'is_prior': True, 'provenance_id': PROV},
    {'name': 'mfx-3-slide-right-mount', 'assembly_ref': ASSEMBLY, 'kind': 'fixed',
     'instance_a': 'cabinet', 'feature_a': 'extrusion-2040-L300:slot:-y:0',
     'instance_b': 'slide-right', 'feature_b': '',
     'interface_ref': 'if-mfx-3-slide-right-mount', 'dof_json': '[]',
     'limits_json': '{"positions": 4}',
     'ratio': 0.0, 'preload_json': '{}', 'fastener_refs_json': '[]', 'valid': True,
     'invalid_reason': '', 'notes': 'as left', 'is_prior': True, 'provenance_id': PROV},
    {'name': JOINT, 'assembly_ref': ASSEMBLY, 'kind': 'slider',
     'instance_a': 'slide-left', 'feature_a': 'drawer-slide-L300:drawer',
     'instance_b': 'drawer-box', 'feature_b': '',
     'interface_ref': f'if-{JOINT}', 'dof_json': _j(['tz']),
     'limits_json': _j({'length_min': 0, 'length_max': 250}),
     'ratio': 0.0, 'preload_json': '{}', 'fastener_refs_json': '[]', 'valid': True,
     'invalid_reason': '', 'notes': 'the drawer travel: 250 mm open on a 300 mm full-extension slide '
     '(the plan\'s acceptance distance); FreeCAD Motion does NOT honour length_max — Polari\'s hard stop does',
     'is_prior': True, 'provenance_id': PROV},
    {'name': 'mfx-3-baseplate-seat', 'assembly_ref': ASSEMBLY, 'kind': 'fixed',
     'instance_a': 'drawer-box', 'feature_a': '',
     'instance_b': 'baseplate', 'feature_b': 'gridfinity-baseplate-2x2:cell:0,0',
     'interface_ref': 'if-mfx-3-baseplate-seat', 'dof_json': '[]', 'limits_json': '{}',
     'ratio': 0.0, 'preload_json': '{}', 'fastener_refs_json': '[]', 'valid': True,
     'invalid_reason': '', 'notes': 'baseplate screwed into the drawer bottom (M3 counterbores)',
     'is_prior': True, 'provenance_id': PROV},
]

#: The ball-slide contacts (one per slide) — the loaded/unloaded runs read these.
SEED_MECH_MOTION_CONTACTS = [
    {'name': 'mfx-3-slide-left-contact', 'assembly_ref': ASSEMBLY, 'kind': 'sliding',
     'instance_a': 'drawer-box', 'instance_b': 'slide-left', 'mu_json': json.dumps(BALL_SLIDE_MU),
     'normal_axis_json': '[0, 0, 1]', 'notes': 'ball-bearing slide, rolling contact modelled as low-μ sliding',
     'is_prior': True, 'provenance_id': PROV},
    {'name': 'mfx-3-slide-right-contact', 'assembly_ref': ASSEMBLY, 'kind': 'sliding',
     'instance_a': 'drawer-box', 'instance_b': 'slide-right', 'mu_json': json.dumps(BALL_SLIDE_MU),
     'normal_axis_json': '[0, 0, 1]', 'notes': 'as left', 'is_prior': True, 'provenance_id': PROV},
] + [dict(c, normal_axis_json='[0, 0, 1]', is_prior=True, provenance_id=PROV)
     for c in SEED_MECH_MOTION_CONTACTS]


def seed_mech_motion(manager):
    """All mxc-4 rows through the upsert path: the fixture (assembly,
    instances, joints, contacts), then the cases and the SimulationDefinition.
    Runs are never seeded."""
    from moduleService.seed_upsert import upsert_seed_pairs
    from mech.mech_assembly_basis import (
        MechAssembly, MechContact, MechJoint, MechPartInstance,
    )
    from mech.mech_motion_basis import MechLoadCase, MechMotionCase
    pairs = [
        ('MechAssembly', MechAssembly, SEED_MECH_MOTION_ASSEMBLIES),
        ('MechPartInstance', MechPartInstance, SEED_MECH_MOTION_INSTANCES),
        ('MechJoint', MechJoint, SEED_MECH_MOTION_JOINTS),
        ('MechContact', MechContact, SEED_MECH_MOTION_CONTACTS),
        ('MechLoadCase', MechLoadCase, SEED_MECH_LOAD_CASES),
        ('MechMotionCase', MechMotionCase, SEED_MECH_MOTION_CASES),
    ]
    try:
        from simulations.simulation_definition import SimulationDefinition
        pairs.append(('SimulationDefinition', SimulationDefinition, SEED_MECH_SIM_DEFINITIONS))
    except ImportError:
        print('[MechMotionSeed] core simulations not importable — SimulationDefinition not seeded', flush=True)
    return upsert_seed_pairs(manager, pairs, tag='MechMotionSeed')


#: polari-app.json `seedPairs` target (mxc-1/2/4 together, in dependency order).
def mech_seed_pairs():
    from mech.mech_assembly_basis import MechAssembly, MechContact, MechJoint, MechPartInstance
    from mech.mech_assembly_seed import (
        SEED_MECH_ASSEMBLIES, SEED_MECH_CONTACTS, SEED_MECH_JOINTS, SEED_MECH_PART_INSTANCES,
    )
    from mech.mech_catalog_basis import DimensionSource, MechFeature, MechPartFamily, MechPartVariant
    from mech.mech_catalog_seed import (
        SEED_DIMENSION_SOURCES, SEED_FEATURES, SEED_PART_FAMILIES, SEED_PART_VARIANTS,
    )
    from mech.mech_material_basis import MechMaterialOption, MechMaterialPreference
    from mech.mech_material_seed import SEED_MECH_MATERIAL_OPTIONS, SEED_MECH_MATERIAL_PREFERENCES
    from mech.mech_motion_basis import MechLoadCase, MechMotionCase, MechMotionRun, MechMotionSimState, MechMotionVector
    from mech.mech_analysis_seed import mech_analysis_seed_pairs
    return [
        ('DimensionSource', DimensionSource, SEED_DIMENSION_SOURCES),
        ('MechPartFamily', MechPartFamily, SEED_PART_FAMILIES),
        ('MechPartVariant', MechPartVariant, SEED_PART_VARIANTS),
        ('MechFeature', MechFeature, SEED_FEATURES),
        ('MechMaterialOption', MechMaterialOption, SEED_MECH_MATERIAL_OPTIONS),
        ('MechMaterialPreference', MechMaterialPreference, SEED_MECH_MATERIAL_PREFERENCES),
        ('MechAssembly', MechAssembly, SEED_MECH_ASSEMBLIES + SEED_MECH_MOTION_ASSEMBLIES),
        ('MechPartInstance', MechPartInstance, SEED_MECH_PART_INSTANCES + SEED_MECH_MOTION_INSTANCES),
        ('MechJoint', MechJoint, SEED_MECH_JOINTS + SEED_MECH_MOTION_JOINTS),
        ('MechContact', MechContact, SEED_MECH_CONTACTS + SEED_MECH_MOTION_CONTACTS),
        ('MechLoadCase', MechLoadCase, SEED_MECH_LOAD_CASES),
        ('MechMotionCase', MechMotionCase, SEED_MECH_MOTION_CASES),
        ('MechMotionRun', MechMotionRun, []),            # made by run_polari, never seeded
        ('MechMotionSimState', MechMotionSimState, []),
        ('MechMotionVector', MechMotionVector, []),
    ] + mech_analysis_seed_pairs()   # the engines as rows, last (they read everything above)


class _LazySeedPairs(list):
    def _fill(self):
        if not list.__len__(self):
            self.extend(mech_seed_pairs())

    def __iter__(self):
        self._fill(); return list.__iter__(self)

    def __len__(self):
        self._fill(); return list.__len__(self)


MECH_SEED_PAIRS = _LazySeedPairs()
