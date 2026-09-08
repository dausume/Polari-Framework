"""
@module motors.m2_composition_seed

m2-4: the M2 composition splice — the PM rung's joints as data,
read by the same wrap-not-port adapter (composition_splice).

WHAT M2's INTERFACES SAY that M1's could not:
- ONE designed non-contact interface, not two. A round rotor has
  no pole tips swinging past the coil bores, so the coil-clearance
  joint that M1 has to keep simply does not exist here. Fewer
  designed gaps is fewer things to get wrong, and it is a
  consequence of the ROTOR SHAPE, not of care.
- A BONDED joint that is already promoted: the magnet ring is
  adhesive-bonded to its carrier and never comes apart. Where M1's
  promotions happened in the MOLD (one pour, fused), M2's happens
  in the BOND — same conclusion (a non-separable interface), a
  different act, and the honest difference is that an adhesive
  line has its own failure modes where a fused casting has none.
- The stator side is REUSED WHOLE. The winding↔tooth fork M1 poses
  (bobbin vs sol-gel promotion) is M2's fork too, unchanged and
  not restated — M2 references M1's construction variants rather
  than seeding a second copy, because it is literally the same
  wound tooth.

THE M2-SPECIFIC OPERATION: op-m2-magnetize. The ring is
magnetised AFTER it is bonded and assembled, which is the gr-3
two-material lesson (magnetise after joining, never before) as an
arch-4 routing operation — and it is why the M2 assembly routing
ends on a physics op rather than a QA one.

@consumers motors.custom.composition_splice (interface_specs dispatch),
motors.m2_scene_seed (marker positions), motors.m2_views_seed,
polariServer seed pass (seed_m2_composition)
"""

import json

from composition.custom.seed_upsert import upsert_seed_pairs

M2_DESIGN = 'ferrite-pm-m2'
M1_DESIGN = 'reluctance-6s4p-m1'
PROV = 'm2-4'

#: The movement-level joints. Realization is theoretical until the
#: first build — M0's made-and-measured must not leak onto an
#: unbuilt machine.
M2_INTERFACES = [
    {'name': 'ifm2-ring-carrier', 'member_a': 'm2-magnet-ring',
     'member_b': 'm2-rotor-carrier', 'designed_separable': False,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry', 'rz'],
     'retention_scheme': 'adhesive',
     'failure_modes': ['fm-bond-line-shear',
                       'fm-thermal-mismatch-stress'],
     'realization_level': 'theoretical',
     'qualifying_act': 'bond one ring to one carrier, then try to '
                       'twist it off by hand on the shaft — the '
                       'bond either takes the rated torque or the '
                       'rotor is two objects pretending to be one',
     'note': 'ALREADY PROMOTED, but by BOND rather than by mold: '
             'the ring and carrier are one body in service and '
             'the interface is non-separable. Unlike M1\'s fused '
             'castings this promotion keeps a bond line, and a '
             'bond line has modes of its own — that is the price '
             'of joining two materials that cannot be poured '
             'together.'},
    {'name': 'ifm2-carrier-shaft', 'member_a': 'm2-rotor-carrier',
     'member_b': 'm1-shaft', 'designed_separable': True,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry'],
     'retention_scheme': 'press',
     'failure_modes': ['fm-preload-loss'],
     'realization_level': 'theoretical',
     'qualifying_act': 'press the carrier on the reused 8 mm '
                       'shaft, torque it off, re-press — the '
                       'mag-15 handling question again',
     'note': 'the service joint: the bearing and shaft are what '
             'wear out, so the rotor has to come off them. The '
             'SHAFT IS M1\'s row — reused, not copied.'},
    {'name': 'ifm2-working-gap', 'member_a': 'm1-stator-teeth',
     'member_b': 'm2-magnet-ring', 'designed_separable': True,
     'dof_removed': [], 'retention_scheme': 'none',
     'failure_modes': [],
     'realization_level': 'theoretical',
     'qualifying_act': 'spin the assembled rotor by hand: a full '
                       'turn with no scrape IS the measurement '
                       '(and on THIS rung the hand-spin also '
                       'produces the back-EMF the bench scopes)',
     'note': 'THE ONE designed non-contact interface — 0.4 mm, '
             'tighter than M1\'s 0.6 because a round rotor has no '
             'lumps to swing. M1 had TWO such gaps; the second '
             '(coil clearance) does not exist here at all, '
             'because there are no pole tips to pass the coil '
             'bores. The gap is the machine.'},
    {'name': 'ifm2-winding-tooth', 'member_a': 'm1-coils',
     'member_b': 'm1-stator-teeth', 'designed_separable': True,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry'],
     'retention_scheme': 'wound',
     'failure_modes': ['fm-turn-to-turn-abrasion', 'fm-fretting'],
     'realization_level': 'theoretical',
     'qualifying_act': 'the M1 act, unchanged: slide a wound '
                       'bobbin over a cast tooth, wiggle test',
     'note': 'REUSED FROM M1 INCLUDING ITS FORK: bobbin '
             '(cv-m1-tooth-bobbin) vs sol-gel promotion '
             '(cv-m1-tooth-promoted). Same wound tooth, same '
             'choice, referenced rather than restated — M2 does '
             'not get to re-litigate a decision it inherited.'},
]

#: Boothroyd-Dewhurst answers for the SEPARABLE interfaces. The
#: bonded one is not a candidate — it is already promoted.
M2_PROMOTION_ANSWERS = {
    'ifm2-carrier-shaft': {
        'moves_relative': False, 'separable_for_service': True,
        'why': 'the bearing and shaft are the service parts — pot '
               'the rotor on and the machine dies with its first '
               'bearing (M1\'s answer, and it did not change '
               'because the rotor did)'},
    'ifm2-working-gap': {
        'moves_relative': True, 'separable_for_service': True,
        'why': 'the rotor TURNS — this gap IS the machine, and '
               'the gate refusing to promote it is the model '
               'working'},
    'ifm2-winding-tooth': {
        'moves_relative': False, 'separable_for_service': False,
        'why': 'inherited from M1 unchanged: promotion deletes '
               'fretting and spends repairability six times, and '
               'the phase-imbalance finding is only actionable '
               'while coils still swap'},
}

#: With one bonded (non-separable) boundary in the set, the flat
#: movement derives the same level M1 does — the machine still
#: comes apart at the shaft, the coils and the gap, while the
#: rotor never does.
M2_DECLARED_LEVEL = 'part-with-separable-sub-parts'


def _j(o):
    return json.dumps(o)


# ---------------------------------------------------------------
# mq-3 style: M2's inter-part correlations as no-code rows over
# the mq-1 emitted quadrics. Nothing here restates a dimension.
# ---------------------------------------------------------------

_Q_TOOTH_FACE = 'motor-m1-stator-tooth--Q--arc-face'
_Q_RING_OUTER = 'motor-m2-magnet-ring-outer--Q--lateral'
_Q_RING_BORE = 'motor-m2-magnet-ring-bore--Q--lateral'


def _rel(name, latex, expr, operands, agrees_with, description):
    return {
        'name': name,
        'description': description + ' | AGREES WITH: '
        + agrees_with,
        'latex': latex,
        'operation_json': json.dumps({'kind': 'expr',
                                      'expr': expr}),
        'operands_json': json.dumps(operands),
    }


SEED_M2_RELATIONS = [
    _rel('m2-rel-working-gap',
         r'g = \sqrt{Q_t[3,3]} - \sqrt{-Q_r[3,3]}',
         'np.sqrt(Qt[3, 3]) - np.sqrt(-Qr[3, 3])',
         {'Qt': {'kind': 'matrix', 'ref': _Q_TOOTH_FACE},
          'Qr': {'kind': 'matrix', 'ref': _Q_RING_OUTER}},
         'MotorDesignDefinition.gap_base_m (x1000, mm) = 0.4',
         'THE AIR GAP as a correlation between two parts\' '
         'equations — and this time the two parts belong to '
         'different RUNGS: M1\'s ground tooth face against M2\'s '
         'magnet ring. If either row moves, the gap moves with '
         'it, live.'),
    _rel('m2-rel-magnet-thickness',
         r't = \sqrt{-Q_o[3,3]} - \sqrt{-Q_i[3,3]}',
         'np.sqrt(-Qo[3, 3]) - np.sqrt(-Qi[3, 3])',
         {'Qo': {'kind': 'matrix', 'ref': _Q_RING_OUTER},
          'Qi': {'kind': 'matrix', 'ref': _Q_RING_BORE}},
         'MotorDesignDefinition.magnet_length_m (x1000, mm) = 4.0',
         'The ring\'s radial thickness OUT of its own two '
         'cylinders — which is the magnet length the solver drives '
         'the MMF from. The design row and the shape row are one '
         'fact, and this is the row that catches them drifting.'),
]

_EXPECTATIONS = {
    'm2-rel-working-gap': 'gap_base_m',
    'm2-rel-magnet-thickness': 'magnet_length_m',
}


def m2_relation_report(manager, design_name=M2_DESIGN):
    """Evaluate M2's relations THROUGH the matrix executor and
    judge each against the design row — the drift alarm, live."""
    try:
        from matrices.matrix_equation_executor import (
            evaluate_equation,
        )
    except ImportError:
        return {'ok': False,
                'refusal': 'the matrices module (numpy) is not '
                           'importable here — relations evaluate '
                           'in-container'}
    from magnetics.custom.magnet_analysis import _named
    design = _named(manager, 'MotorDesignDefinition', design_name)
    if design is None:
        return {'ok': False,
                'refusal': f'no design "{design_name}"'}
    try:
        params = json.loads(design.params_json)
    except (TypeError, ValueError, AttributeError):
        return {'ok': False, 'refusal': 'design params unreadable'}
    eq_table = (getattr(manager, 'objectTables', None)
                or {}).get('MatrixEquationDefinition', {})
    eq_rows = (list(eq_table.values())
               if isinstance(eq_table, dict) else list(eq_table))
    # live tables key by id, fixtures by name.
    by_name = {getattr(r, 'name', ''): r for r in eq_rows}
    out = []
    for seed in SEED_M2_RELATIONS:
        row = by_name.get(seed['name'])
        if row is None:
            out.append({'relation': seed['name'], 'ok': False,
                        'refusal': 'relation row not booted '
                                   '(seed_m2_composition delivers '
                                   'it)'})
            continue
        try:
            value = float(evaluate_equation(row, {},
                                            manager=manager))
        except Exception as e:
            out.append({'relation': seed['name'], 'ok': False,
                        'refusal': f'executor: {e}'})
            continue
        key = _EXPECTATIONS[seed['name']]
        expected = float(params.get(key, 0.0)) * 1000.0
        out.append({'relation': seed['name'], 'ok': True,
                    'valueMm': value, 'expected': expected,
                    'expectedFrom': f'design row {key} x1000',
                    'consistent': abs(value - expected) < 1e-6})
    return {
        'ok': True, 'design': design_name, 'relations': out,
        'allConsistent': all(r.get('consistent') for r in out
                             if r.get('ok')),
        'note': 'both values come OUT of the parts\' emitted '
                'quadrics through the no-code executor — and the '
                'gap relation spans two RUNGS, so M2 cannot drift '
                'away from the stator it claims to reuse'}


def derived_m2_marker_positions():
    """Scene marker positions DERIVED from the same shape rows the
    renderer draws — no seeded approximations (the mq-3 rule)."""
    from motors.motor_shapes_seed import (
        SEED_M1_PART_SHAPES, SEED_M2_PART_SHAPES,
    )
    p = {s['name']: json.loads(s['parameters_json'])
         for s in SEED_M1_PART_SHAPES + SEED_M2_PART_SHAPES
         if s.get('parameters_json')}
    tooth = p['motor-m1-stator-tooth']
    ring_o = p['motor-m2-magnet-ring-outer']
    ring_i = p['motor-m2-magnet-ring-bore']
    shaft = p['motor-m1-shaft']
    coil_bore = p['motor-m1-coil-bore']
    z_top = tooth['height'] / 2.0 + 2.0
    return {
        'ifm2-ring-carrier': [ring_i['radius'], 0.0, z_top],
        'ifm2-carrier-shaft': [0.0, 0.0, shaft['height'] / 4.0],
        'ifm2-working-gap': [
            (tooth['r_face'] + ring_o['radius']) / 2.0, 0.0,
            z_top],
        'ifm2-winding-tooth': [coil_bore['center'][0], 3.0, z_top],
    }


# ---------------------------------------------------------------
# The M2 assembly routing — and THE op that ends it
# ---------------------------------------------------------------

SEED_M2_PART_COMPONENTS = [
    {'name': 'pc-m2-sintered-ring',
     'display_name': 'Sintered hexaferrite ring (unmagnetised)',
     'material_ref': 'opt-sintered-hexaferrite',
     'material_condition': 'sintered',
     'shape_ref': 'motor-m2-magnet-ring', 'shape_units': 'mm',
     'coating_ref': '', 'coating_build_mm': 0.0,
     'process_state_ref': '', 'quantity': 1,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'UNMAGNETISED is the point of the row: a sintered '
              'ferrite ring is magnetically inert until it is '
              'pulsed, which is what makes assembling it '
              'possible at all.'},
    {'name': 'pc-m2-carrier-blank',
     'display_name': 'Cast non-magnetic carrier hub',
     'material_ref': 'opt-plain-geopolymer',
     'material_condition': 'cast',
     'shape_ref': 'motor-m2-rotor-carrier', 'shape_units': 'mm',
     'coating_ref': '', 'coating_build_mm': 0.0,
     'process_state_ref': '', 'quantity': 1,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'magnetically useless ON PURPOSE — see the part '
              'row\'s why-this-material.'},
]

SEED_M2_COMPOSITION_NODES = [
    {'name': 'm2-rotor-bonded',
     'display_name': 'M2 rotor — ring bonded to carrier',
     'declared_level': 'part',
     'members_json': _j([
         {'ref': 'pc-m2-sintered-ring', 'kind': 'component',
          'quantity': 1},
         {'ref': 'pc-m2-carrier-blank', 'kind': 'component',
          'quantity': 1}]),
     'functional_ref': 'fp-m2-rotor', 'genealogy_ref': '',
     'bulk_failure_mode_refs_json': _j([
         'fm-bond-line-shear', 'fm-thermal-mismatch-stress',
         'fm-brittle-fracture']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'a PART, not an assembly: bonded and magnetised, it '
              'never comes apart again. The bulk modes listed are '
              'what the bond bought in exchange for the interface '
              'modes it deleted.'},
]

SEED_M2_FUNCTIONAL_PARTS = [
    {'name': 'fp-m2-rotor',
     'display_name': 'M2 rotor (functional)',
     'purpose': 'present a four-pole magnetic field to the gap at '
                'every angle, and carry the resulting torque to '
                'the shaft',
     'allocated_role_refs_json': _j(['torque-magnet-active',
                                     'static-structural']),
     'archetype_ref': 'at-rotating-shaft-member',
     'tunable_toward': 'flux across the gap per unit of rotor '
                       'inertia, at a magnet grade we can '
                       'actually make or buy',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'ONE engineering-BOM row; the pure-local and '
              'commercial ROUTES realize it from different '
              'magnets (m2-6), not different constructions.'},
]

SEED_M2_CONSTRUCTION_VARIANTS = [
    {'name': 'cv-m2-rotor-bonded',
     'display_name': 'Bonded ring on cast carrier, magnetised '
                     'after assembly',
     'functional_ref': 'fp-m2-rotor',
     'node_ref': 'm2-rotor-bonded',
     'routing_ref': 'rt-m2-rotor-bonded',
     'fill_factor_class': 'n/a',
     'selection_rationale': 'the only construction offered, and '
                            'the reason is the ORDER: magnetise '
                            'last. A magnetised ring grabs every '
                            'ferrous tool, jumps out of '
                            'alignment, and collects swarf in the '
                            'gap it is about to run in — so the '
                            'assembly has to happen while the '
                            'ring is still inert.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]

SEED_M2_ROUTINGS = [
    {'name': 'rt-m2-rotor-bonded',
     'display_name': 'Bond, cure, press, THEN magnetise',
     'variant_ref': 'cv-m2-rotor-bonded', 'per_unit': 'rotor',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'one rotor per machine — and the last op is the '
              'one that makes it a magnet.'},
]

SEED_M2_ROUTING_OPS = [
    {'name': 'op-m2-bond',
     'display_name': 'Bond ring to carrier',
     'routing_ref': 'rt-m2-rotor-bonded', 'sequence': 1,
     'kind': 'join',
     'summary': 'adhesive-bond the inert ring onto the cast '
                'carrier, concentric within the gap budget',
     'capability_rung_ref': 'T0', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'concentricity here spends the 0.4 mm gap — the '
              'tightest tolerance on the rung.'},
    {'name': 'op-m2-press-shaft',
     'display_name': 'Press rotor onto the shaft',
     'routing_ref': 'rt-m2-rotor-bonded', 'sequence': 2,
     'kind': 'join',
     'summary': 'press the bonded rotor onto the reused 8 mm '
                'shaft',
     'capability_rung_ref': 'T0', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'op-m2-magnetize',
     'display_name': 'Magnetise — LAST, after assembly',
     'routing_ref': 'rt-m2-rotor-bonded', 'sequence': 3,
     'kind': 'join',
     'summary': 'pulse the assembled rotor in a four-pole '
                'magnetising fixture: the ring goes in inert and '
                'comes out a rotor',
     'capability_rung_ref': 'W2', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'THE gr-3 TWO-MATERIAL LESSON as an operation. The '
              'gear module learned it about a two-material rotor '
              '(no welding, magnetise after joining) and it is '
              'the same fact here: every earlier op is easier '
              'because the magnet is not a magnet yet. It is '
              'kind "join" rather than a new kind, deliberately '
              '— it joins a field to a body, and inventing a '
              'kind for one op is how vocabularies rot.'},
]


def m2_promotion_story(manager):
    """What M2's joints answer about promotion, live — the bonded
    rotor is already promoted, the gap refuses to be, and the
    winding fork is M1's, referenced."""
    from composition.node_basis import derive_level
    return {
        'ok': True, 'design': M2_DESIGN,
        'alreadyPromoted': {
            'interface': 'ifm2-ring-carrier',
            'by': 'adhesive bond, cured before magnetising',
            'level': derive_level(manager, 'm2-rotor-bonded'),
            'note': 'M1 promoted in the MOLD (one pour, no bond '
                    'line); M2 promotes in the BOND. Same '
                    'non-separable answer, different act — and '
                    'the bond line keeps failure modes a fused '
                    'casting never has.'},
        'refusesPromotion': {
            'interface': 'ifm2-working-gap',
            'why': 'the rotor turns: the gap IS the machine'},
        'inheritedFork': {
            'interface': 'ifm2-winding-tooth',
            'variants': ['cv-m1-tooth-bobbin',
                         'cv-m1-tooth-promoted'],
            'why': 'the same wound tooth as M1, so the same fork '
                   '— referenced, not re-seeded. M2 does not get '
                   'to re-litigate a decision it inherited.'},
        'gapCount': {
            'm2': 1, 'm1': 2,
            'note': 'ONE designed non-contact interface where M1 '
                    'had two: a round rotor has no pole tips to '
                    'swing past the coil bores. Fewer designed '
                    'gaps is a consequence of the rotor shape, '
                    'not of care.'},
    }


def seed_m2_composition(manager):
    """m2-4 rows via the upsert path. Same classes, more rows —
    plus the M2 relations, which need the matrices module."""
    from composition.component_basis import PartComponentDefinition
    from composition.functional_basis import (
        ConstructionVariantDefinition, FunctionalPartDefinition,
    )
    from composition.node_basis import CompositionNode
    from composition.routing_basis import (
        RoutingDefinition, RoutingOperation,
    )
    pairs = [
        ('PartComponentDefinition', PartComponentDefinition,
         SEED_M2_PART_COMPONENTS),
        ('CompositionNode', CompositionNode,
         SEED_M2_COMPOSITION_NODES),
        ('FunctionalPartDefinition', FunctionalPartDefinition,
         SEED_M2_FUNCTIONAL_PARTS),
        ('ConstructionVariantDefinition',
         ConstructionVariantDefinition,
         SEED_M2_CONSTRUCTION_VARIANTS),
        ('RoutingDefinition', RoutingDefinition, SEED_M2_ROUTINGS),
        ('RoutingOperation', RoutingOperation,
         SEED_M2_ROUTING_OPS),
    ]
    try:
        from matrices.matrix_equation_definition import (
            MatrixEquationDefinition,
        )
        pairs.append(('MatrixEquationDefinition',
                      MatrixEquationDefinition,
                      SEED_M2_RELATIONS))
    except ImportError:
        pass
    return upsert_seed_pairs(manager, pairs,
                             tag='M2CompositionSeed')
