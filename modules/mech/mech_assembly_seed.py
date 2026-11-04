"""
@module mech.mech_assembly_seed

mxc-2 fixtures (MECH_FREECAD_INTERCHANGE_PLAN §4, row mxc-2):

  mfx-1  one 2020 beam L300 (ground) + 2 inner brackets, each held
         by 2 × (sliding T-nut M4 + ISO 4762 M4x10) — four FIXED
         joints realised by fasteners. M4, because the catalogue's
         bracket-inner-20 is drilled for M4 (screw_d 4.0, hole ≈ 4.5)
         and the 20-series sliding T-nut is 4.7 mm high: M5 in this
         bracket fails BOTH the clearance and the engagement check,
         and the selftest keeps that as a negative case. A fit-check
         fixture, not a real corner: both legs of each bracket go to
         the ONE beam (+y and +x slots). Hand count: 2 brackets × 2
         fastener positions → every bracket fixed in all six →
         mobility 0.
  mfx-2  a 2×2 Gridfinity bin seated on a 2×2 baseplate, four
         magnet seats as 'grid' joints with dof_json '[]' (the
         magnets hold tz). Bin cells == plate cells; mobility 0.

Composition rows the splice writes (D-mxc-8): one
PartComponentDefinition per catalogue variant used (material_ref
'' = UNSTATED until the material slice names its rows), one
CompositionNode per fixture carrying the members (= the BOM), and
one InterfaceDefinition per joint, derived by
custom/joint_interface.interface_spec — the ONE writer.

NAMING CONTRACT with the catalogue slice (mxc-1): the variant and
feature NAMES below are the catalogue's own (verified against
mech_catalog_seed 2026-11-03: '<variant>:slot:+y:0', ':leg:0',
':thread', ':magnet:0,0:sw' ...). CONTRACT_VARIANTS /
CONTRACT_FEATURES are a STAND-IN carrying only the numbers the fit
checks read (see fit_checks.variant_params); they are not seeded,
and the selftest runs the same fixtures against the real seeds too.
This module never imports mech.mech_catalog_seed.

@consumers polariServer seed passes, mech.mech_assembly_selftest
"""

import json

from mech.custom.joint_interface import interface_spec
from mech.mech_assembly_basis import (
    MechAssembly, MechContact, MechJoint, MechPartInstance,
)

PROV = 'mxc-2'


def _j(obj):
    return json.dumps(obj)


# ---------------------------------------------------------------
# catalogue stand-in (contract names; NOT seeded)
# ---------------------------------------------------------------

def _variant(name, family, **params):
    return {'name': name, 'family_ref': family,
            'parameters_json': _j(params)}


CONTRACT_VARIANTS = [
    _variant('extrusion-2020-L300', 'extrusion', slot='slot-B6/20',
             series=20, length=300),
    _variant('bracket-inner-20', 'bracket-inner', thickness=4.7,
             hole_d=4.5, holes=2, material_class='aluminium'),
    _variant('tnut-sliding-slot6-M4', 'tnut-sliding', thread='M4x0.7',
             slot='slot-B6/20', thread_depth=4.7, material_class='steel'),
    _variant('tnut-sliding-slot6-M5', 'tnut-sliding', thread='M5x0.8',
             slot='slot-B6/20', thread_depth=4.7, material_class='steel'),
    _variant('iso4762-M4x10', 'iso4762', thread='M4x0.7', length=10.0,
             head_d=7.0),
    _variant('iso4762-M5x10', 'iso4762', thread='M5x0.8', length=10.0,
             head_d=8.5),
    _variant('gridfinity-baseplate-2x2', 'gridfinity-baseplate',
             grid_x=2, grid_y=2, grid_role='plate'),
    _variant('gridfinity-bin-2x2x6', 'gridfinity-bin', grid_x=2, grid_y=2,
             height_u=6),
    _variant('gridfinity-bin-3x2x6', 'gridfinity-bin', grid_x=3, grid_y=2,
             height_u=6),
    _variant('drawer-slide-L300', 'drawer-slide', length=300,
             extension_mm=300,
             load_rating={'dynamic_load_n': 175, 'rated_extension_mm': 300,
                          'basis': 'knob: 45 mm ball-bearing side-mount '
                                   'slides are catalogued ~35 kg per '
                                   'pair at full extension — cited '
                                   'order of magnitude, not measured'}),
]


def _feature(variant, feat, kind, key, role, origin=(0, 0, 0),
             axis=(0, 0, 1), dof_free=(), load=None):
    return {'name': f'{variant}:{feat}', 'variant_ref': variant,
            'kind': kind, 'key': key, 'role': role,
            'origin_json': _j(list(origin)), 'axis_json': _j(list(axis)),
            'dof_free_json': _j(list(dof_free)),
            'load_rating_json': _j(load or {'axial_n': -1, 'shear_n': -1,
                                            'moment_nm': -1,
                                            'basis': 'undetermined'})}


#: Gridfinity magnet sockets: one per cell corner, named
#: '<variant>:magnet:<cx>,<cy>:<ne|nw|sw|se>' as the catalogue does.
#: mfx-2 seats the bin on the four OUTER corners of its 2x2 cells.
_BIN_MAGNETS = [('0,0', 'sw', (-21, -21)), ('1,0', 'se', (21, -21)),
                ('0,1', 'nw', (-21, 21)), ('1,1', 'ne', (21, 21))]


def _thread_feats(variant, key):
    return [_feature(variant, 'thread', 'thread', key,
                     'female' if 'tnut' in variant else 'male',
                     axis=(0, 0, 1), dof_free=('rz',))]


CONTRACT_FEATURES = [
    _feature('extrusion-2020-L300', 'slot:+y:0', 'slot', 'slot-B6/20',
             'channel', (0, 10, 0), (1, 0, 0), ('tz',),
             {'axial_n': -1, 'shear_n': 500, 'moment_nm': -1,
              'basis': 'knob: T-nut slip load, 20-series'}),
    _feature('extrusion-2020-L300', 'slot:+x:0', 'slot', 'slot-B6/20',
             'channel', (10, 0, 0), (0, 1, 0), ('tz',)),
    # the catalogue models an inner bracket's LEG as a slot rider (it
    # sits inside the slot) and its hole as an M4 bore socket
    _feature('bracket-inner-20', 'leg:0', 'slot', 'slot-B6/20', 'rider',
             (0, 0, 0), (1, 0, 0), ('tz',)),
    _feature('bracket-inner-20', 'leg:1', 'slot', 'slot-B6/20', 'rider',
             (0, 0, 0), (0, 1, 0), ('tz',)),
    _feature('bracket-inner-20', 'hole:0', 'bore', 'M4x0.7', 'socket',
             (7, 0, 0), (0, 0, 1), ('tz', 'rz')),
    _feature('bracket-inner-20', 'hole:1', 'bore', 'M4x0.7', 'socket',
             (0, 6, 0), (0, 0, 1), ('tz', 'rz')),
    _feature('tnut-sliding-slot6-M4', 'slot', 'slot', 'slot-B6/20',
             'rider', (0, 0, 0), (1, 0, 0), ('tz',)),
    _feature('tnut-sliding-slot6-M5', 'slot', 'slot', 'slot-B6/20',
             'rider', (0, 0, 0), (1, 0, 0), ('tz',)),
    _feature('iso4762-M4x10', 'head-seat', 'face', 'plane', 'plane',
             (0, 0, 10), (0, 0, 1), ('tx', 'ty', 'rz')),
    _feature('drawer-slide-L300', 'cabinet', 'rail', 'slide-45-ball',
             'channel', (0, 0, 0), (1, 0, 0), ('tz',)),
    _feature('drawer-slide-L300', 'drawer', 'rail', 'slide-45-ball',
             'rider', (0, 0, 0), (1, 0, 0), ('tz',)),
    _feature('drawer-slide-L300', 'face:cabinet', 'face', 'plane', 'plane',
             (0, 0, 0), (0, 1, 0), ('tx', 'ty', 'rz')),
] + _thread_feats('tnut-sliding-slot6-M4', 'M4x0.7') \
  + _thread_feats('tnut-sliding-slot6-M5', 'M5x0.8') \
  + _thread_feats('iso4762-M4x10', 'M4x0.7') \
  + _thread_feats('iso4762-M5x10', 'M5x0.8') + [
    _feature(v, f'cell:{c}', 'grid_cell', 'grid-42', 'cell',
             (x, y, 0), (0, 0, 1), ())
    for v in ('gridfinity-baseplate-2x2', 'gridfinity-bin-2x2x6')
    for c, _corner, (x, y) in _BIN_MAGNETS
] + [
    _feature(v, f'magnet:{c}:{corner}', 'magnet', 'magnet-6.5x2', 'socket',
             (x, y, 0), (0, 0, 1), ())
    for v in ('gridfinity-baseplate-2x2', 'gridfinity-bin-2x2x6',
              'gridfinity-bin-3x2x6')
    for c, corner, (x, y) in _BIN_MAGNETS
]


# ---------------------------------------------------------------
# mech rows
# ---------------------------------------------------------------

SEED_MECH_ASSEMBLIES = [
    {'name': 'mfx-1', 'display_name': 'mfx-1: 2020 beam + 2 inner brackets',
     'kind': 'frame', 'system_ref': '', 'node_ref': 'node-mfx-1',
     'ground_instance': 'beam',
     'parameters_json': _j({'beam_length_mm': 300, 'brackets': 2,
                            'fasteners_per_bracket': 2}),
     'generator': '', 'generator_version': '',
     'notes': 'fit-check fixture: both legs of each bracket fastened to '
              'the ONE beam (+y and +z slots). Hand count: 2 fastener '
              'positions per bracket -> fixed in six -> mobility 0.',
     'provenance': 'MECH_FREECAD_INTERCHANGE_PLAN §4 mxc-2',
     'is_prior': True, 'provenance_id': PROV},
    {'name': 'mfx-2', 'display_name': 'mfx-2: 2x2 bin on a 2x2 baseplate',
     'kind': 'generic', 'system_ref': '', 'node_ref': 'node-mfx-2',
     'ground_instance': 'plate',
     'parameters_json': _j({'grid_x': 2, 'grid_y': 2, 'magnets': 4}),
     'generator': '', 'generator_version': '',
     'notes': 'four magnet seats as grid joints; magnets hold tz, so '
              'the bin is fixed in six -> mobility 0.',
     'provenance': 'MECH_FREECAD_INTERCHANGE_PLAN §4 mxc-2',
     'is_prior': True, 'provenance_id': PROV},
]


def _inst(name, assembly, variant, origin, role='body', notes=''):
    return {'name': name, 'assembly_ref': assembly, 'variant_ref': variant,
            'component_ref': f'pc-mech-{variant}',
            'placement_json': _j({'origin': list(origin),
                                  'rotation': [1, 0, 0, 0],
                                  'placement_basis': 'given'}),
            'material_option_ref': '', 'quantity_role': role,
            'quantity': 1, 'notes': notes, 'is_prior': True,
            'provenance_id': PROV}


_BRACKET_X = {'bracket-1': 50.0, 'bracket-2': 250.0}

SEED_MECH_PART_INSTANCES = [
    _inst('beam', 'mfx-1', 'extrusion-2020-L300', (0, 0, 0),
          notes='ground'),
    _inst('bracket-1', 'mfx-1', 'bracket-inner-20', (50, 10, 10)),
    _inst('bracket-2', 'mfx-1', 'bracket-inner-20', (250, 10, 10)),
] + [
    _inst(f'tnut-{n}', 'mfx-1', 'tnut-sliding-slot6-M4',
          (_BRACKET_X[b], 10 if leg == 'a' else 0, 0 if leg == 'a' else 10),
          role='fastener')
    for n, (b, leg) in enumerate([('bracket-1', 'a'), ('bracket-1', 'b'),
                                  ('bracket-2', 'a'), ('bracket-2', 'b')], 1)
] + [
    _inst(f'screw-{n}', 'mfx-1', 'iso4762-M4x10',
          (_BRACKET_X[b], 15 if leg == 'a' else 0, 0 if leg == 'a' else 15),
          role='fastener')
    for n, (b, leg) in enumerate([('bracket-1', 'a'), ('bracket-1', 'b'),
                                  ('bracket-2', 'a'), ('bracket-2', 'b')], 1)
] + [
    _inst('plate', 'mfx-2', 'gridfinity-baseplate-2x2', (0, 0, 0),
          notes='ground'),
    _inst('bin', 'mfx-2', 'gridfinity-bin-2x2x6', (0, 0, 0)),
]


def _joint(name, assembly, kind, a, fa, b, fb, dof='', fasteners=(),
           origin=None, preload=None, notes=''):
    return {'name': name, 'assembly_ref': assembly, 'kind': kind,
            'instance_a': a, 'feature_a': fa, 'instance_b': b,
            'feature_b': fb, 'interface_ref': f'if-{name}',
            'dof_json': dof,
            'limits_json': _j({'origin': list(origin)} if origin else {}),
            'ratio': 0.0,
            'preload_json': _j(preload or {}),
            'fastener_refs_json': _j(list(fasteners)),
            'valid': True, 'invalid_reason': '', 'notes': notes,
            'is_prior': True, 'provenance_id': PROV}


_M4_PRELOAD = {'torque_nm': 2.0, 'clamp_n': 2600,
               'basis': 'knob: M4 8.8 dry, K=0.2, ~65% proof'}

SEED_MECH_JOINTS = [
    _joint('mfx-1:J1', 'mfx-1', 'fixed', 'bracket-1',
           'bracket-inner-20:leg:0', 'beam',
           'extrusion-2020-L300:slot:+y:0', fasteners=('screw-1', 'tnut-1'),
           origin=(50, 10, 0), preload=_M4_PRELOAD),
    _joint('mfx-1:J2', 'mfx-1', 'fixed', 'bracket-1',
           'bracket-inner-20:leg:1', 'beam',
           'extrusion-2020-L300:slot:+x:0', fasteners=('screw-2', 'tnut-2'),
           origin=(50, 0, 10), preload=_M4_PRELOAD),
    _joint('mfx-1:J3', 'mfx-1', 'fixed', 'bracket-2',
           'bracket-inner-20:leg:0', 'beam',
           'extrusion-2020-L300:slot:+y:0', fasteners=('screw-3', 'tnut-3'),
           origin=(250, 10, 0), preload=_M4_PRELOAD),
    _joint('mfx-1:J4', 'mfx-1', 'fixed', 'bracket-2',
           'bracket-inner-20:leg:1', 'beam',
           'extrusion-2020-L300:slot:+x:0', fasteners=('screw-4', 'tnut-4'),
           origin=(250, 0, 10), preload=_M4_PRELOAD),
] + [
    _joint(f'mfx-2:G{i}', 'mfx-2', 'grid', 'bin',
           f'gridfinity-bin-2x2x6:magnet:{c}:{corner}', 'plate',
           f'gridfinity-baseplate-2x2:magnet:{c}:{corner}', dof='[]',
           origin=(x, y, 0),
           notes='magnet seat: tx/ty/rz by the cell profile, tz by the '
                 'magnet')
    for i, (c, corner, (x, y)) in enumerate(_BIN_MAGNETS)
]

SEED_MECH_CONTACTS = [
    {'name': 'mfx-1:C1', 'assembly_ref': 'mfx-1', 'instance_a': 'bracket-1',
     'instance_b': 'beam', 'kind': 'static',
     'mu_json': _j({'static': 1.2, 'kinetic': 1.0,
                    'basis': 'knob: aluminium on aluminium, dry, '
                             'engineering-toolbox order of magnitude'}),
     'normal_axis_json': _j([0, 1, 0]), 'notes': '', 'is_prior': True,
     'provenance_id': PROV},
    {'name': 'mfx-2:C1', 'assembly_ref': 'mfx-2', 'instance_a': 'bin',
     'instance_b': 'plate', 'kind': 'static',
     'mu_json': _j({'static': 0.35, 'kinetic': 0.3,
                    'basis': 'knob: PLA on PLA, printed, dry'}),
     'normal_axis_json': _j([0, 0, 1]), 'notes': 'bin resting on the '
     'plate; the magnets add normal force, not friction', 'is_prior': True,
     'provenance_id': PROV},
]


# ---------------------------------------------------------------
# composition rows (what the splice writes)
# ---------------------------------------------------------------

def _components():
    seen = {}
    for i in SEED_MECH_PART_INSTANCES:
        v = i['variant_ref']
        seen.setdefault(v, {
            'name': f'pc-mech-{v}', 'display_name': v,
            'material_ref': '', 'material_condition': '',
            'shape_ref': '', 'shape_units': 'mm', 'coating_ref': '',
            'coating_build_mm': 0.0, 'process_state_ref': '',
            'quantity': 1, 'is_prior': True, 'provenance_id': PROV,
            'notes': f'mech catalogue variant {v}; material_ref is '
                     f'UNSTATED until MechMaterialOption rows land '
                     f'(mxc-1) — resolve via the instance\'s '
                     f'material_option_ref or the family preference'})
    return list(seen.values())


SEED_MECH_PART_COMPONENTS = _components()


def _nodes():
    out = []
    for a in SEED_MECH_ASSEMBLIES:
        counts = {}
        for i in SEED_MECH_PART_INSTANCES:
            if i['assembly_ref'] == a['name']:
                counts[i['component_ref']] = counts.get(
                    i['component_ref'], 0) + i['quantity']
        out.append({
            'name': a['node_ref'], 'display_name': a['display_name'],
            'declared_level': 'assembly',
            'members_json': _j([{'ref': c, 'kind': 'component',
                                 'quantity': n} for c, n in counts.items()]),
            'functional_ref': '', 'genealogy_ref': '',
            'bulk_failure_mode_refs_json': _j([]),
            'is_prior': True, 'provenance_id': PROV,
            'notes': f'members = the BOM of {a["name"]} (no BOM row in '
                     f'mech, D-mxc-8); quantities summed from the '
                     f'instances'})
    return out


SEED_MECH_COMPOSITION_NODES = _nodes()

_INST_BY_NAME = {i['name']: i for i in SEED_MECH_PART_INSTANCES}
_ASM_BY_NAME = {a['name']: a for a in SEED_MECH_ASSEMBLIES}
_FEAT_BY_NAME = {f['name']: f for f in CONTRACT_FEATURES}

SEED_MECH_INTERFACES = [
    interface_spec(j, _ASM_BY_NAME[j['assembly_ref']], _INST_BY_NAME,
                   _FEAT_BY_NAME)
    for j in SEED_MECH_JOINTS
]


def seed_mech_assemblies(manager):
    """All mxc-2 fixture rows through the arch-1 upsert path: the
    mech rows, then the composition rows the splice owns. Classes
    not in objectTypingDict are skipped loudly by upsert_seed_pairs
    (composition gated off = no interface rows, stated)."""
    from moduleService.seed_upsert import upsert_seed_pairs
    pairs = [
        ('MechAssembly', MechAssembly, SEED_MECH_ASSEMBLIES),
        ('MechPartInstance', MechPartInstance, SEED_MECH_PART_INSTANCES),
        ('MechJoint', MechJoint, SEED_MECH_JOINTS),
        ('MechContact', MechContact, SEED_MECH_CONTACTS),
    ]
    try:
        from composition.component_basis import PartComponentDefinition
        from composition.interface_basis import InterfaceDefinition
        from composition.node_basis import CompositionNode
        pairs += [
            ('PartComponentDefinition', PartComponentDefinition,
             SEED_MECH_PART_COMPONENTS),
            ('CompositionNode', CompositionNode,
             SEED_MECH_COMPOSITION_NODES),
            ('InterfaceDefinition', InterfaceDefinition,
             SEED_MECH_INTERFACES),
        ]
    except ImportError:
        print('[MechAssemblySeed] composition not importable — the '
              'splice rows are not written', flush=True)
    return upsert_seed_pairs(manager, pairs, tag='MechAssemblySeed')
