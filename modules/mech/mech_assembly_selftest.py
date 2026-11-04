"""
@module mech.mech_assembly_selftest

mxc-2 selftests. Everything asserted is HAND-COMPUTED first:

  mfx-1  beam (ground) + bracket-1 + bracket-2; fasteners are not
         bodies. Each bracket: 2 fixed point-joints at distinct
         positions -> tx ty tz rx ry from either, rz from the pair
         -> 0 free each -> mobility 0 with 4 valid joints.
         Remove screw-3: J3 loses its fastener -> invalid -> bracket-2
         has ONE fastener position -> rz friction-held -> free ['rz']
         -> under_constrained, NAMED bracket-2; mobility 1.
  mfx-2  bin on plate: 4 grid joints, dof '[]' (magnets) -> all six
         removed -> mobility 0; bin cells (2,2) == plate cells (2,2)
         -> 4 occupied, 0 free, no conflict. A 3x2 bin on the 2x2
         plate: cells x=2 overflow -> 2 cells outside -> grid_mismatch.
  M6 T-nut in slot-B6/20: SLOT_THREADS['slot-B6/20'] = M3 M4 M5 ->
         wrong_pairing (and the M5 screw does not match an M6 nut).
  Engagement, M4x10 through the 4.7 mm bracket into a 4.7 mm-high
         T-nut: available = min(10 - 4.7, 4.7) = 4.7 mm. The FEMALE
         thread is the steel T-nut: required 1.0 x 4 = 4 -> 4.7 >= 4
         OK. If the counter material were ALUMINIUM: 2.0 x 4 = 8 ->
         SHORT. Clearance: bracket hole 4.5 >= ISO 273 medium 4.5 OK.
         NEGATIVE, kept on purpose: M5 screws + M5 T-nuts in this
         bracket -> hole 4.5 < 5.5 (clearance_hole_small x4) and
         engagement min(10 - 4.7, 4.7) = 4.7 < 1.0 x 5 (short x4).
         The plan's literal M5 question "6 >= 2x5?" -> 6 < 10 SHORT.
  Interface for J1: free () -> dof_removed all six; one screw ->
         retention 'fastener'; members = the components.
  mfx-3 (real seeds): cabinet (ground) -fixed- slide-left/right;
         slide-left -slider tz- drawer-box -fixed- baseplate. Rigid
         groups {cabinet, slides}, {drawer-box, baseplate}; one tree
         edge with 1 free -> mobility 1, nothing under/over.
  Cantilever: 15 N over 2 slides, 300 mm, centroid 0.5:
         per slide 7.5 N, moment 7.5 x 0.3 x 0.5 = 1.125 Nm;
         rated 175 x 0.3 x 0.5 = 26.25 Nm -> OK. 600 N -> 300 N per
         slide > 175 -> slide_overload.

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m
mech.mech_assembly_selftest
"""

import copy
import json
import types

from composition.node_basis import derive_level
from composition.objects.interface._shared import (
    DOF_AXES as C_DOF_AXES, RETENTION_SCHEMES,
)
from mech.custom.dof_solver import dof_conflicts, solve_dof
from mech.custom.fit_checks import (
    ISO_273_CLEARANCE, SLOT_THREADS, cantilever_tip, check_assembly,
    clearance_hole, grid_occupancy, slot_pairing, thread_engagement,
    available_engagement,
)
from mech.custom.joint_interface import (
    consistency_check, interface_for_joint, joint_from_interface,
)
from mech.mech_assembly_basis import (
    DOF_AXES, JOINT_DOF, JOINT_KINDS, complement, joint_free_axes,
)
from mech.mech_assembly_seed import (
    CONTRACT_FEATURES, CONTRACT_VARIANTS, SEED_MECH_ASSEMBLIES,
    SEED_MECH_COMPOSITION_NODES, SEED_MECH_CONTACTS, SEED_MECH_INTERFACES,
    SEED_MECH_JOINTS, SEED_MECH_PART_COMPONENTS, SEED_MECH_PART_INSTANCES,
    seed_mech_assemblies,
)

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL}: {label}'
          + (f'  [{extra}]' if extra and not cond else ''))


def _table(seed):
    return {s['name']: types.SimpleNamespace(**copy.deepcopy(s))
            for s in seed}


def _mgr():
    """Fake manager over the seeds + the contract catalogue stand-in
    (the gears pattern). idList lets REAL composition rows register
    when the live interface writer runs."""
    m = types.SimpleNamespace(objectTables={
        'MechAssembly': _table(SEED_MECH_ASSEMBLIES),
        'MechPartInstance': _table(SEED_MECH_PART_INSTANCES),
        'MechJoint': _table(SEED_MECH_JOINTS),
        'MechContact': _table(SEED_MECH_CONTACTS),
        'MechConflict': {},
        'MechPartVariant': _table(CONTRACT_VARIANTS),
        'MechFeature': _table(CONTRACT_FEATURES),
        'PartComponentDefinition': _table(SEED_MECH_PART_COMPONENTS),
        'CompositionNode': _table(SEED_MECH_COMPOSITION_NODES),
        'InterfaceDefinition': _table(SEED_MECH_INTERFACES),
    }, idList=[])
    m.objectTypingDict = {k: object() for k in m.objectTables}
    return m


def _asm(m, name):
    return m.objectTables['MechAssembly'][name]


def _kinds(conflicts):
    return sorted(c['kind'] for c in conflicts)


print('== suite: constants and the joint-frame contract ==')
check('DOF_AXES are composition\'s, verbatim', DOF_AXES == C_DOF_AXES)
check('every joint kind has a free-DOF entry',
      all(k in JOINT_DOF for k in JOINT_KINDS), extra=str(JOINT_KINDS))
check('13 FreeCAD kinds + grid', len(JOINT_KINDS) == 14
      and JOINT_KINDS[-1] == 'grid')
check('complement is exact: free + removed == all six, disjoint',
      all(set(JOINT_DOF[k]) | set(complement(JOINT_DOF[k])) == set(DOF_AXES)
          and not set(JOINT_DOF[k]) & set(complement(JOINT_DOF[k]))
          for k in JOINT_KINDS))
check("'monolithic' and 'magnetic' are now in RETENTION_SCHEMES",
      'monolithic' in RETENTION_SCHEMES and 'magnetic' in RETENTION_SCHEMES)
check('dof_json "" = kind default, "[]" = explicit none',
      joint_free_axes(types.SimpleNamespace(kind='slider', dof_json=''))
      == ('tz',)
      and joint_free_axes(types.SimpleNamespace(kind='grid', dof_json='[]'))
      == ())

print('\n== suite: mfx-1 DOF count (hand: 0 free, 4 valid joints) ==')
m = _mgr()
r1 = solve_dof(_asm(m, 'mfx-1'), m)
check('mfx-1 solves', r1['ok'], extra=str(r1))
check('4 valid joints', r1['valid_joint_count'] == 4
      and not r1['invalid_joints'], extra=str(r1.get('invalid_joints')))
check('mobility 0', r1['assembly_mobility'] == 0,
      extra=str(r1['assembly_mobility']))
check('both brackets have 0 free DOF; fasteners are not bodies',
      r1['instances']['bracket-1']['free'] == []
      and r1['instances']['bracket-2']['free'] == []
      and 'screw-1' not in r1['instances']
      and 'tnut-1' not in r1['instances'])
check('ground beam is 0 by definition',
      r1['instances']['beam']['ground'] is True
      and r1['instances']['beam']['free_count'] == 0)
check('nothing under- or over-constrained',
      not r1['under_constrained'] and not r1['over_constrained'])
check('the honest note says COUNT, not rank test',
      'COUNT' in r1['note'] and 'rank' in r1['note'])
check('check_assembly(mfx-1) -> 0 conflicts',
      check_assembly(_asm(m, 'mfx-1'), m) == [],
      extra=str(check_assembly(_asm(m, 'mfx-1'), m)))

print('\n== suite: remove one screw -> bracket-2 under-constrained, NAMED ==')
m2 = _mgr()
del m2.objectTables['MechPartInstance']['screw-3']
r2 = solve_dof(_asm(m2, 'mfx-1'), m2)
check('J3 is invalid: its fastener is gone',
      [i['joint'] for i in r2['invalid_joints']] == ['mfx-1:J3']
      and 'screw-3' in r2['invalid_joints'][0]['why'],
      extra=str(r2['invalid_joints']))
check('bracket-2 free = [rz] (one fastener = a pivot, rz friction-held)',
      r2['instances']['bracket-2']['free'] == ['rz'],
      extra=str(r2['instances']['bracket-2']))
check('bracket-2 is NAMED under-constrained, bracket-1 is not',
      [u['instance'] for u in r2['under_constrained']] == ['bracket-2']
      and 'friction' in r2['under_constrained'][0]['why'])
check('mobility 1', r2['assembly_mobility'] == 1)
c2 = dof_conflicts(r2)
check('conflicts: under_constrained + the invalid joint as wrong_pairing',
      _kinds(c2) == ['under_constrained', 'wrong_pairing']
      and any(json.loads(c['detail_json']).get('instance') == 'bracket-2'
              for c in c2), extra=str(c2))

print('\n== suite: parallel fixed joints -> over_constrained, not hidden ==')
m3 = _mgr()
m3.objectTables['MechJoint']['mfx-1:JX'] = types.SimpleNamespace(
    name='mfx-1:JX', assembly_ref='mfx-1', kind='fixed',
    instance_a='bracket-1', feature_a='bracket-inner-20:plane:leg-a',
    instance_b='beam', feature_b='extrusion-2020-L300:plane:+y',
    interface_ref='', dof_json='', limits_json='{}', ratio=0.0,
    preload_json='{}', fastener_refs_json='[]', valid=True,
    invalid_reason='', notes='a full fix glued on top of two screws')
r3 = solve_dof(_asm(m3, 'mfx-1'), m3)
check('bracket-1 + beam reported over_constrained, JX named',
      len(r3['over_constrained']) == 1
      and r3['over_constrained'][0]['instances'] == ['beam', 'bracket-1']
      and 'mfx-1:JX' in r3['over_constrained'][0]['joints'],
      extra=str(r3['over_constrained']))
check('a floating body is named too',
      (lambda r: [u['instance'] for u in r['under_constrained']] == ['loose']
       and 'floating' in r['under_constrained'][0]['why'])(
          (lambda mm: (mm.objectTables['MechPartInstance'].__setitem__(
              'loose', types.SimpleNamespace(
                  name='loose', assembly_ref='mfx-1',
                  variant_ref='bracket-inner-20', component_ref='',
                  placement_json='{}', quantity_role='body')),
              solve_dof(_asm(mm, 'mfx-1'), mm))[1])(_mgr())))

print('\n== suite: mfx-2 grid seating ==')
m4 = _mgr()
r4 = solve_dof(_asm(m4, 'mfx-2'), m4)
check('4 grid joints with magnets: bin fixed in six, mobility 0',
      r4['valid_joint_count'] == 4 and r4['assembly_mobility'] == 0
      and not r4['under_constrained'] and not r4['over_constrained'],
      extra=str(r4))
m5 = _mgr()
for j in m5.objectTables['MechJoint'].values():
    if j.kind == 'grid':
        j.dof_json = ''        # no magnets: the kind default, tz free
r5 = solve_dof(_asm(m5, 'mfx-2'), m5)
check('without magnets: tz (lift-off) free, DESIGNED, not a conflict',
      r5['assembly_mobility'] == 1 and r5['instances']['bin']['free'] == ['tz']
      and not r5['under_constrained'], extra=str(r5['instances']['bin']))
check('check_assembly(mfx-2) -> 0 conflicts: bin cells == plate cells',
      check_assembly(_asm(m4, 'mfx-2'), m4) == [],
      extra=str(check_assembly(_asm(m4, 'mfx-2'), m4)))
occ = grid_occupancy((2, 2), [{'name': 'bin', 'origin': (0, 0),
                               'cells': (2, 2)}])
check('occupancy: 4 occupied, 0 free', occ['ok'] and occ['occupied'] == 4
      and occ['free'] == 0)
m6 = _mgr()
m6.objectTables['MechPartInstance']['bin'].variant_ref = 'gridfinity-bin-3x2x6'
m6.objectTables['MechPartInstance']['bin'].component_ref = \
    'pc-mech-gridfinity-bin-3x2x6'
for j in m6.objectTables['MechJoint'].values():
    if j.kind == 'grid':
        j.feature_a = j.feature_a.replace('2x2x6', '3x2x6')
c6 = check_assembly(_asm(m6, 'mfx-2'), m6)
check('a 3x2 bin on a 2x2 plate -> grid_mismatch (2 cells overflow)',
      _kinds(c6) == ['grid_mismatch']
      and json.loads(c6[0]['detail_json'])['outside'] == 2,
      extra=str(c6))
occ2 = grid_occupancy((2, 2), [{'name': 'a', 'origin': (0, 0),
                                'cells': (2, 1)},
                               {'name': 'b', 'origin': (1, 0),
                                'cells': (1, 2)}])
check('two bins claiming cell (1,0) -> overlap',
      not occ2['ok'] and occ2['overlap'][0]['cell'] == (1, 0))

print('\n== suite: fit checks — pairing ==')
check('M5 T-nut in slot-B6/20 pairs',
      slot_pairing('slot-B6/20', 'slot-B6/20', 'M5x0.8')['ok'] is True)
sp = slot_pairing('slot-B6/20', 'slot-B6/20', 'M6x1')
check('M6 T-nut in slot-B6/20 REFUSED (that opening takes M3 M4 M5)',
      sp['ok'] is False and 'M6' in sp['why']
      and SLOT_THREADS['slot-B6/20'] == ('M3', 'M4', 'M5'), extra=str(sp))
check('slot key mismatch refused',
      slot_pairing('slot-B8/30', 'slot-B6/20', 'M5x0.8')['ok'] is False)
m7 = _mgr()
m7.objectTables['MechPartVariant']['tnut-M6'] = types.SimpleNamespace(
    name='tnut-M6', family_ref='tnut-sliding',
    parameters_json=json.dumps({'thread': 'M6x1', 'slot': 'slot-B6/20',
                                'thread_depth': 8.0,
                                'material_class': 'steel'}))
m7.objectTables['MechFeature']['tnut-M6:slot:rider'] = types.SimpleNamespace(
    name='tnut-M6:slot:rider', variant_ref='tnut-M6', kind='slot',
    key='slot-B6/20', role='rider')
m7.objectTables['MechFeature']['tnut-M6:thread'] = types.SimpleNamespace(
    name='tnut-M6:thread', variant_ref='tnut-M6', kind='thread',
    key='M6x1', role='female')
m7.objectTables['MechPartInstance']['tnut-1'].variant_ref = 'tnut-M6'
c7 = check_assembly(_asm(m7, 'mfx-1'), m7)
check('an M6 T-nut on J1 -> wrong_pairing (slot refuses M6; M5 screw != '
      'M6 nut)', 'wrong_pairing' in _kinds(c7)
      and {json.loads(c['detail_json']).get('why', '')[:12] for c in c7}
      and any('M6' in json.loads(c['detail_json'])['why'] for c in c7),
      extra=str(c7))

print('\n== suite: fit checks — thread engagement (knobs by material class) ==')
avail = available_engagement(10.0, 4.7, 4.7)
check('M4x10 through the 4.7 mm bracket into a 4.7 mm T-nut: available = '
      'min(10-4.7, 4.7) = 4.7 mm', abs(avail - 4.7) < 1e-9, extra=str(avail))
e_steel = thread_engagement(4.0, avail, 'steel')
check('steel T-nut carries the female thread: required 1.0 x 4 = 4; '
      '4.7 >= 4 -> OK',
      e_steel['ok'] is True and e_steel['required'] == 4.0
      and abs(e_steel['actual'] - 4.7) < 1e-9, extra=str(e_steel))
e_al = thread_engagement(4.0, avail, 'aluminium')
check('if the counter material were aluminium: required 2.0 x 4 = 8; '
      '4.7 < 8 -> SHORT', e_al['ok'] is False and e_al['required'] == 8.0)
e_plan = thread_engagement(5.0, 6.0, 'aluminium')
check("the plan's literal M5 question, 6 >= 2x5?: 6 < 10 -> SHORT",
      e_plan['ok'] is False and e_plan['actual'] == 6.0)
check('plastic 2.5·d; brass/zinc 1.5·d; unknown class is UNASSESSED '
      '(None), never a pass',
      thread_engagement(5.0, 12.5, 'plastic')['ok'] is True
      and thread_engagement(5.0, 12.4, 'plastic')['ok'] is False
      and thread_engagement(4.0, 6.0, 'brass')['ok'] is True
      and thread_engagement(5.0, 100.0, 'unobtainium')['ok'] is None)
m8 = _mgr()
m8.objectTables['MechPartVariant']['tnut-sliding-slot6-M4'].parameters_json = \
    json.dumps({'thread': 'M4x0.7', 'slot': 'slot-B6/20', 'thread_depth': 4.7,
                'material_class': 'aluminium'})
c8 = check_assembly(_asm(m8, 'mfx-1'), m8)
check('aluminium T-nuts -> 4 thread_engagement_short conflicts with the '
      'numbers in detail',
      _kinds(c8) == ['thread_engagement_short'] * 4
      and json.loads(c8[0]['detail_json'])['required'] == 8.0
      and abs(json.loads(c8[0]['detail_json'])['actual'] - 4.7) < 1e-9,
      extra=str(c8))

print('\n== suite: NEGATIVE — M5 screws in the M4 bracket are flagged ==')
m8b = _mgr()
for n in range(1, 5):
    m8b.objectTables['MechPartInstance'][f'screw-{n}'].variant_ref = 'iso4762-M5x10'
    m8b.objectTables['MechPartInstance'][f'tnut-{n}'].variant_ref = 'tnut-sliding-slot6-M5'
c8b = check_assembly(_asm(m8b, 'mfx-1'), m8b)
check('M5 x4 in bracket-inner-20: 4 clearance_hole_small (4.5 < 5.5) + 4 '
      'thread_engagement_short (4.7 < 5.0)',
      _kinds(c8b) == ['clearance_hole_small'] * 4
      + ['thread_engagement_short'] * 4, extra=str(_kinds(c8b)))
d8b = [json.loads(c['detail_json']) for c in c8b]
check('the numbers are in the detail: hole required 5.5 actual 4.5; '
      'engagement required 5.0 actual 4.7',
      any(d.get('required') == 5.5 and d.get('actual') == 4.5 for d in d8b)
      and any(d.get('required') == 5.0 and abs(d.get('actual', 0) - 4.7) < 1e-9
              for d in d8b))

print('\n== suite: material class from ROWS (no import of the material slice) ==')
from mech.custom.fit_checks import material_class_for, option_engagement_class
check('option name -> class: steel_carbon, al_diecast, petg(polymer), '
      'zinc_trivalent(coating) -> steel, aluminium, plastic, none',
      option_engagement_class('steel_carbon') == 'steel'
      and option_engagement_class('al_diecast') == 'aluminium'
      and option_engagement_class('petg', 'polymer') == 'plastic'
      and option_engagement_class('zinc_trivalent', 'coating') == '')
m8c = _mgr()
m8c.objectTables['MechPartVariant']['tnut-sliding-slot6-M4'].parameters_json = \
    json.dumps({'thread': 'M4x0.7', 'slot': 'slot-B6/20', 'thread_depth': 4.7})
m8c.objectTables['MechPartFamily'] = {'tnut-sliding': types.SimpleNamespace(
    name='tnut-sliding',
    material_default_ids_json=json.dumps(['steel_carbon', 'zinc_trivalent']))}
m8c.objectTables['MechMaterialOption'] = {
    n: types.SimpleNamespace(name=n, material_class=c)
    for n, c in (('steel_carbon', 'metal'), ('zinc_trivalent', 'coating'),
                 ('petg', 'polymer'))}
cls, basis = material_class_for(
    m8c, m8c.objectTables['MechPartInstance']['tnut-1'],
    m8c.objectTables['MechPartVariant']['tnut-sliding-slot6-M4'])
check('no material_class on the variant -> the family default steel_carbon '
      '-> steel, basis names the family',
      cls == 'steel' and 'tnut-sliding' in basis, extra=f'{cls} {basis}')
check('with the family default, check_assembly(mfx-1) is still clean',
      check_assembly(_asm(m8c, 'mfx-1'), m8c) == [])
m8c.objectTables['MechPartInstance']['tnut-1'].material_option_ref = 'petg'
c8c = check_assembly(_asm(m8c, 'mfx-1'), m8c)
check('a PETG T-nut on J1 -> plastic 2.5·d = 10 > 4.7 -> short, J1 only',
      _kinds(c8c) == ['thread_engagement_short']
      and json.loads(c8c[0]['detail_json'])['joint'] == 'mfx-1:J1'
      and 'petg' in json.loads(c8c[0]['detail_json'])['class_basis'],
      extra=str(c8c))
m8d = _mgr()
m8d.objectTables['MechPartVariant']['tnut-sliding-slot6-M4'].parameters_json = \
    json.dumps({'thread': 'M4x0.7', 'slot': 'slot-B6/20', 'thread_depth': 4.7})
c8d = check_assembly(_asm(m8d, 'mfx-1'), m8d)
check('no class anywhere -> UNASSESSED warnings, not silence and not a pass',
      _kinds(c8d) == ['thread_engagement_short'] * 4
      and all(c['severity'] == 'warning' for c in c8d))

print('\n== suite: fit checks — ISO 273 clearance ==')
check('table medium series: M2 2.4, M2.5 2.9, M3 3.4, M4 4.5, M5 5.5, '
      'M6 6.6, M8 9',
      [ISO_273_CLEARANCE[d][1] for d in (2, 2.5, 3, 4, 5, 6, 8)]
      == [2.4, 2.9, 3.4, 4.5, 5.5, 6.6, 9.0])
check('5.5 mm hole for M5 passes; 5.3 (fine) is clearance_hole_small',
      clearance_hole(5, 5.5)['ok'] is True
      and clearance_hole(5, 5.3)['ok'] is False)
check('M4 medium 4.5: the bracket\'s 4.5 hole passes; 4.3 (fine) does not',
      clearance_hole(4, 4.5)['ok'] is True and clearance_hole(4, 4.3)['ok'] is False)
m9 = _mgr()
m9.objectTables['MechPartVariant']['bracket-inner-20'].parameters_json = \
    json.dumps({'thickness': 4.7, 'hole_d': 4.3, 'material_class': 'aluminium'})
c9 = check_assembly(_asm(m9, 'mfx-1'), m9)
check('a 4.3 mm hole in the bracket -> clearance_hole_small on all 4 joints',
      _kinds(c9) == ['clearance_hole_small'] * 4, extra=str(_kinds(c9)))

print('\n== suite: fit checks — drawer cantilever ==')
rating = json.loads(next(v['parameters_json'] for v in CONTRACT_VARIANTS
                         if v['name'] == 'drawer-slide-L300'))['load_rating']
ct = cantilever_tip(15.0, 300.0, rating, n_slides=2)
check('15 N, 300 mm, 2 slides: 1.125 Nm vs rated 26.25 Nm -> OK',
      ct['ok'] is True and abs(ct['moment_nm'] - 1.125) < 1e-9
      and abs(ct['rated_nm'] - 26.25) < 1e-9, extra=str(ct))
ct2 = cantilever_tip(600.0, 300.0, rating, n_slides=2)
check('600 N: 300 N per slide > 175 N rated -> overload',
      ct2['ok'] is False and ct2['overload'] is True)
check('a rating without numbers is unassessed, not a pass',
      cantilever_tip(15.0, 300.0, {'basis': 'tbd'})['ok'] is None)

print('\n== suite: the joint <-> InterfaceDefinition splice (D-mxc-8) ==')
m10 = _mgr()
del m10.objectTables['InterfaceDefinition']['if-mfx-1:J1']   # let the writer CREATE it
j1 = m10.objectTables['MechJoint']['mfx-1:J1']
name = interface_for_joint(j1, m10)
iface = next(i for i in m10.objectTables['InterfaceDefinition'].values()
             if getattr(i, 'name', '') == name)
check('interface named if-<joint>, joint.interface_ref set',
      name == 'if-mfx-1:J1' and j1.interface_ref == name)
check('live writer makes a REAL composition row',
      type(iface).__name__ == 'InterfaceDefinition')
check('fixed screw joint: dof_removed = all six',
      json.loads(iface.dof_removed_json) == list(DOF_AXES))
check("retention 'fastener'", iface.retention_scheme == 'fastener')
check('members are the COMPONENT refs, node is the assembly\'s node',
      iface.member_a == 'pc-mech-bracket-inner-20'
      and iface.member_b == 'pc-mech-extrusion-2020-L300'
      and iface.node_ref == 'node-mfx-1'
      and iface.designed_separable is True)
g0 = next(i for i in SEED_MECH_INTERFACES if i['name'] == 'if-mfx-2:G0')
check("grid joint with a magnet socket -> retention 'magnetic'",
      g0['retention_scheme'] == 'magnetic'
      and json.loads(g0['dof_removed_json']) == list(DOF_AXES))
check("grid without a magnet feature -> 'none'",
      (lambda s: s['retention_scheme'] == 'none'
       and json.loads(s['dof_removed_json']) == ['tx', 'ty', 'rx', 'ry', 'rz'])(
          __import__('mech.custom.joint_interface', fromlist=['x'])
          .interface_spec({'name': 'g', 'kind': 'grid', 'instance_a': 'bin',
                           'instance_b': 'plate', 'feature_a': 'x',
                           'feature_b': 'y', 'dof_json': ''})))
back = joint_from_interface(iface, m10)
check('round trip joint -> interface -> joint is identity (name, kind, '
      'dof, instances, interface_ref, fastener presence)',
      back['name'] == j1.name and back['kind'] == j1.kind
      and json.loads(back['dof_json']) == list(joint_free_axes(j1))
      and back['instance_a'] == 'bracket-1' and back['instance_b'] == 'beam'
      and back['interface_ref'] == j1.interface_ref
      and back['has_fastener'] is True, extra=str(back))
check('the reverse map names what it CANNOT recover',
      'limits_json' in back['missing'] and 'fastener_refs_json' in back['missing'])
inst = m10.objectTables['MechPartInstance']
check('consistency: joint and interface agree',
      consistency_check(j1, iface, inst)['ok'])
iface.dof_removed_json = json.dumps(['tx', 'ty', 'tz', 'rx', 'ry'])
cc = consistency_check(j1, iface, inst)
check('tampered dof_removed -> mismatch named',
      not cc['ok'] and cc['mismatches'][0]['field'] == 'dof')
check('the seed precomputed the same 8 interface rows',
      len(SEED_MECH_INTERFACES) == 8
      and all(i['retention_scheme'] == 'fastener'
              for i in SEED_MECH_INTERFACES if i['name'].startswith('if-mfx-1'))
      and all(i['retention_scheme'] == 'magnetic'
              for i in SEED_MECH_INTERFACES if i['name'].startswith('if-mfx-2')))
check('untagged interface: kind inferred from the DOF set, ambiguity stated',
      (lambda b: b['kind'] == 'cylindrical' and b['ambiguous_kinds'] == ['screw'])(
          joint_from_interface(types.SimpleNamespace(
              name='if-x', member_a='a', member_b='b',
              dof_removed_json=json.dumps(['tx', 'ty', 'rx', 'ry']),
              retention_scheme='none', notes=''))))

print('\n== suite: composition derives the fixtures as ASSEMBLY ==')
m11 = _mgr()
lv1 = derive_level(m11, 'node-mfx-1')
lv2 = derive_level(m11, 'node-mfx-2')
check('node-mfx-1 derives assembly from its 4 separable interfaces',
      lv1.get('ok') and lv1['derived'] == 'assembly'
      and len(lv1['separableSet']) == 4, extra=str(lv1))
check('node-mfx-2 derives assembly (magnetic seats are separable)',
      lv2.get('ok') and lv2['derived'] == 'assembly', extra=str(lv2))
members = json.loads(m11.objectTables['CompositionNode']['node-mfx-1']
                     .members_json)
check('the BOM is the node\'s members: beam 1, bracket 2, T-nut 4, screw 4',
      {mm['ref']: mm['quantity'] for mm in members} == {
          'pc-mech-extrusion-2020-L300': 1, 'pc-mech-bracket-inner-20': 2,
          'pc-mech-tnut-sliding-slot6-M4': 4, 'pc-mech-iso4762-M4x10': 4},
      extra=str(members))
check('component material_ref is UNSTATED (""), not a guess',
      all(c['material_ref'] == '' for c in SEED_MECH_PART_COMPONENTS))

print('\n== suite: the seed converges through the arch-1 upsert path ==')
m12 = types.SimpleNamespace(objectTables={}, idList=[])
m12.objectTypingDict = {k: object() for k in (
    'MechAssembly', 'MechPartInstance', 'MechJoint', 'MechContact',
    'PartComponentDefinition', 'CompositionNode', 'InterfaceDefinition')}
reps = seed_mech_assemblies(m12)
ins = {r['class']: len(r.get('inserted', [])) for r in reps}
check('rows inserted: 2 assemblies, 13 instances, 8 joints, 2 contacts, '
      '6 components, 2 nodes, 8 interfaces',
      ins == {'MechAssembly': 2, 'MechPartInstance': 13, 'MechJoint': 8,
              'MechContact': 2, 'PartComponentDefinition': 6,
              'CompositionNode': 2, 'InterfaceDefinition': 8}, extra=str(ins))
reps2 = seed_mech_assemblies(m12)
check('second pass: everything unchanged, nothing re-inserted',
      all(not r.get('inserted') and not r.get('updated') for r in reps2))
r12 = solve_dof(next(iter(m12.objectTables['MechAssembly'].values())), m12)
check('the real rows solve the same: mfx-1 mobility 0',
      r12['ok'] and r12['assembly_mobility'] == 0)

print('\n== suite: the REAL seeds (catalogue mxc-1 + materials + mfx-3) ==')
try:
    from mech.mech_motion_seed import mech_seed_pairs
    _pairs = mech_seed_pairs()
except Exception as e:      # the sibling slices are not in this checkout
    _pairs = None
    print(f'   (skipped: {e})')
if _pairs is not None:
    mr = types.SimpleNamespace(objectTables={
        cls_name: _table(seed) for cls_name, _cls, seed in _pairs}, idList=[])
    mr.objectTables.setdefault('MechConflict', {})
    mr.objectTypingDict = {k: object() for k in mr.objectTables}
    rr1 = solve_dof(_asm(mr, 'mfx-1'), mr)
    check('real seeds: mfx-1 mobility 0, 4 valid joints',
          rr1['ok'] and rr1['assembly_mobility'] == 0
          and rr1['valid_joint_count'] == 4, extra=str(rr1))
    cr1 = check_assembly(_asm(mr, 'mfx-1'), mr)
    check('real seeds: check_assembly(mfx-1) -> 0 conflicts (M4 in the M4 '
          'bracket, steel T-nut from the family default)',
          cr1 == [], extra=str(cr1))
    cr2 = check_assembly(_asm(mr, 'mfx-2'), mr)
    check('real seeds: check_assembly(mfx-2) -> 0 conflicts',
          cr2 == [], extra=str(cr2))
    rr3 = solve_dof(_asm(mr, 'mfx-3-drawer-cassette'), mr)
    check('real seeds: mfx-3 mobility 1 (the drawer slider), 4 valid joints',
          rr3['ok'] and rr3['assembly_mobility'] == 1
          and rr3['valid_joint_count'] == 4, extra=str(rr3))
    check('mfx-3 rigid groups: {cabinet, slides} and {drawer-box, baseplate}; '
          'drawer-box free [tz], baseplate rides with it',
          sorted(map(tuple, rr3['groups'])) == [
              ('baseplate', 'drawer-box'),
              ('cabinet', 'slide-left', 'slide-right')]
          and rr3['instances']['drawer-box']['free'] == ['tz']
          and rr3['instances']['baseplate']['free'] == ['tz']
          and not rr3['under_constrained'] and not rr3['over_constrained'],
          extra=str(rr3))
    check('mfx-3 is a tree: no loops listed', rr3['loops'] == [],
          extra=str(rr3['loops']))
    mr_loop = types.SimpleNamespace(objectTables=dict(mr.objectTables), idList=[])
    mr_loop.objectTables['MechJoint'] = dict(mr.objectTables['MechJoint'])
    mr_loop.objectTables['MechJoint']['mfx-3-slide-2'] = types.SimpleNamespace(
        name='mfx-3-slide-2', assembly_ref='mfx-3-drawer-cassette',
        kind='slider', instance_a='slide-right',
        feature_a='drawer-slide-L300:drawer', instance_b='drawer-box',
        feature_b='', interface_ref='', dof_json='["tz"]',
        limits_json='{}', ratio=0.0, preload_json='{}',
        fastener_refs_json='[]', valid=True, invalid_reason='', notes='')
    rr3l = solve_dof(_asm(mr_loop, 'mfx-3-drawer-cassette'), mr_loop)
    check('a second slider (right slide -> drawer) closes a LOOP: listed, '
          'not counted, mobility still 1',
          rr3l['assembly_mobility'] == 1 and len(rr3l['loops']) == 1
          and rr3l['loops'][0]['joints'] == ['mfx-3-slide-2'],
          extra=str(rr3l['loops']))
    cr3 = check_assembly(_asm(mr, 'mfx-3-drawer-cassette'), mr)
    check('real seeds: check_assembly(mfx-3) -> 0 conflicts (tip moment under '
          'the slide rating, no spurious pairing)', cr3 == [], extra=str(cr3))
    mr.objectTables['MechJoint']['mfx-3-slide-left-mount'].feature_b = \
        'drawer-slide-L300:face:cabinet'
    cr3b = check_assembly(_asm(mr, 'mfx-3-drawer-cassette'), mr)
    check('a slot<->face pair on the mount IS caught as wrong_pairing',
          _kinds(cr3b) == ['wrong_pairing']
          and 'key mismatch' in json.loads(cr3b[0]['detail_json'])['why'],
          extra=str(cr3b))
    mr.objectTables['MechJoint']['mfx-3-slide-left-mount'].feature_b = \
        'drawer-slide-L300:face:nope'
    cr3c = check_assembly(_asm(mr, 'mfx-3-drawer-cassette'), mr)
    check('a feature NAME that does not resolve is a warning, not silence',
          _kinds(cr3c) == ['wrong_pairing'] and cr3c[0]['severity'] == 'warning')
    mr.objectTables['MechAssembly']['mfx-3-drawer-cassette'].parameters_json = \
        json.dumps({'drawer_load_n': 600.0, 'extension_mm': 250})
    mr.objectTables['MechJoint']['mfx-3-slide-left-mount'].feature_b = ''
    cr3d = check_assembly(_asm(mr, 'mfx-3-drawer-cassette'), mr)
    check('600 N in the drawer -> slide_overload against the catalogue '
          'rating (45 kg/pair -> 220.7 N per slide)',
          _kinds(cr3d) == ['slide_overload']
          and abs(json.loads(cr3d[0]['detail_json'])['rated_load_n'] - 220.66) < 0.1,
          extra=str(cr3d))

failed = _results.count(False)
print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
raise SystemExit(1 if failed else 0)
