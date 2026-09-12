"""
@module motors.m1_composition_seed

m1-4: the M1 composition splice — M1's joints stated as data, the
same wrap-not-port adapter (composition_splice) reading them.

WHAT M1's INTERFACES SAY that M0's could not:
- TWO designed NON-CONTACT interfaces (the working gap tooth↔pole
  AND the coil clearance the pole tips swing past) — zero DOF
  removed, never mortared; a rub at either one is a failure with a
  name, not a surprise.
- TWO MOLD-FUSED boundaries (poles↔core, teeth↔yoke): the castings
  deliver multi-part regions ALREADY PROMOTED — promotion happened
  in the mold, recorded as non-separable interfaces, so the flat
  movement honestly derives part-with-separable-sub-parts: the
  machine still comes apart at the shaft, the coils and the gaps,
  while the cast regions never do.
- Every M1 interface is THEORETICAL (nothing is built) — the
  realization level rides the spec, because M0's made-and-measured
  must not leak onto an unbuilt machine.

THE PROMOTION FORK M1 actually poses (the mag-26 family, next
rung): are the six phase coils wound on REMOVABLE BOBBINS slid
over the teeth (assembly — a bad coil is a swapped coil, and the
m1-7 imbalance finding stays actionable per phase), or WOUND IN
PLACE and sol-gel PROMOTED into the tooth (part — fretting deleted
over ~1e8 steps, repairability spent, and the brittle crack-IS-a-
short bulk mode taken on)? Both constructions are first-class
ConstructionVariantDefinition rows of ONE functional part; levels
DERIVE live from their interface rows.

@consumers motors.custom.composition_splice (interface_specs dispatch),
motors.m1_views_seed (m1-construction-fork section), motors.clock_scene_basis
(markers), polariServer seed pass (seed_m1_composition)
"""

import json

from moduleService.seed_upsert import upsert_seed_pairs

M1_DESIGN = 'reluctance-6s4p-m1'
PROV = 'm1-4'

#: The movement-level joints. Non-separable rows are the MOLD
#: boundaries; realization is theoretical until the first build.
M1_INTERFACES = [
    {'name': 'ifm1-rotor-shaft', 'member_a': 'm1-rotor-core',
     'member_b': 'm1-shaft', 'designed_separable': True,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry'],
     'retention_scheme': 'press',
     'failure_modes': ['fm-preload-loss'],
     'realization_level': 'theoretical',
     'qualifying_act': 'press the first cast rotor on an 8 mm '
                       'shaft, then torque it off and re-press — '
                       'the mag-15 handling question, asked of M1',
     'note': 'press fit onto the 608-bearing shaft (mag-1 cited)'},
    {'name': 'ifm1-winding-tooth', 'member_a': 'm1-coils',
     'member_b': 'm1-stator-teeth', 'designed_separable': True,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry'],
     'retention_scheme': 'wound',
     'failure_modes': ['fm-turn-to-turn-abrasion', 'fm-fretting'],
     'realization_level': 'theoretical',
     'qualifying_act': 'slide a wound bobbin over a cast tooth; '
                       'wiggle test after 100 phase pulses',
     'note': 'THE promotion candidate — the fork is stated as '
             'cv-m1-tooth-bobbin vs cv-m1-tooth-promoted'},
    {'name': 'ifm1-poles-core', 'member_a': 'm1-rotor-poles',
     'member_b': 'm1-rotor-core', 'designed_separable': False,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry', 'rz'],
     'retention_scheme': 'monolithic',
     'failure_modes': [],
     'realization_level': 'theoretical',
     'qualifying_act': 'one rotor pour fills poles and core '
                       'together without a cold joint at the roots',
     'note': 'MOLD-FUSED: the salient rotor casts as one pour — '
             'promotion happened in the mold; the pole root is '
             'bulk material, and its modes are bulk modes'},
    {'name': 'ifm1-teeth-yoke', 'member_a': 'm1-stator-teeth',
     'member_b': 'm1-stator-yoke', 'designed_separable': False,
     'dof_removed': ['tx', 'ty', 'tz', 'rx', 'ry', 'rz'],
     'retention_scheme': 'monolithic',
     'failure_modes': [],
     'realization_level': 'theoretical',
     'qualifying_act': 'one stator pour fills six teeth and the '
                       'ring without cold joints',
     'note': 'MOLD-FUSED, same argument as the rotor — and the '
             'reason coils must SLIDE ON: the teeth cannot come '
             'to the winder'},
    {'name': 'ifm1-working-gap', 'member_a': 'm1-stator-teeth',
     'member_b': 'm1-rotor-poles', 'designed_separable': True,
     'dof_removed': [], 'retention_scheme': 'none',
     'failure_modes': [],
     'realization_level': 'theoretical',
     'qualifying_act': 'spin the assembled rotor by hand: a full '
                       'turn with no scrape IS the measurement',
     'note': 'designed non-contact #1: the 0.6 mm WORKING gap — '
             'zero DOF removed, never mortared, and the entire '
             'torque mechanism (saliency across this gap)'},
    {'name': 'ifm1-coil-clearance', 'member_a': 'm1-coils',
     'member_b': 'm1-rotor-poles', 'designed_separable': True,
     'dof_removed': [], 'retention_scheme': 'none',
     'failure_modes': ['fm-turn-to-turn-abrasion'],
     'realization_level': 'theoretical',
     'qualifying_act': 'same hand-spin: pole tips must clear the '
                       'coil overhang at every angle',
     'note': 'designed non-contact #2: the pole tips swing past '
             'the coil bores every revolution — a rub here '
             'abrades enamel, and abraded enamel is a short'},
]

#: Boothroyd-Dewhurst answers for the SEPARABLE interfaces (the
#: fused ones are not candidates — they are already promoted, and
#: promotion_candidates lists them as such).
M1_PROMOTION_ANSWERS = {
    'ifm1-winding-tooth': {
        'moves_relative': False, 'separable_for_service': False,
        'why': 'the mag-26 argument at the next rung: fusing '
               'deletes fretting over ~1e8 steps outright; '
               'service = rewind from new. BUT six coils, not one '
               '— promoting them all makes the whole stator one '
               'scrap unit, and the m1-7 imbalance finding stops '
               'being actionable per phase. The fork is a knowing '
               'choice, stated as construction variants.'},
    'ifm1-rotor-shaft': {
        'moves_relative': False, 'separable_for_service': True,
        'why': 'the bearing and shaft are the service parts — '
               'pot the rotor on and the movement dies with its '
               'first bearing'},
    'ifm1-working-gap': {
        'moves_relative': True, 'separable_for_service': True,
        'why': 'the rotor TURNS — this gap is the machine; the '
               'gate refusing it is the model working'},
    'ifm1-coil-clearance': {
        'moves_relative': True, 'separable_for_service': True,
        'why': 'same: clearance is the design intent, filling it '
               'is the failure'},
}

#: What the flat movement honestly derives with two mold-fused
#: boundaries in the set (composition_splice declares this).
M1_DECLARED_LEVEL = 'part-with-separable-sub-parts'


def _j(o):
    return json.dumps(o)


# ---------------------------------------------------------------
# The wound-tooth construction fork — one functional part, two
# constructions, levels DERIVED live from interface rows
# ---------------------------------------------------------------

SEED_M1_PART_COMPONENTS = [
    {'name': 'pc-magnet-wire-26awg',
     'display_name': 'Magnet wire, 26 AWG enamelled',
     'material_ref': 'opt-copper-magnet-wire',
     'material_condition': 'drawn-annealed',
     'shape_ref': '', 'shape_units': 'mm',
     'coating_ref': 'enamel-polyurethane',
     'coating_build_mm': 0.025,
     'process_state_ref': '', 'quantity': 1,
     'is_prior': True, 'provenance_id': PROV,
     'notes': '26 AWG per the M1 design row: 0.5 A phase current '
              'wants copper area, not cell-voltage finesse — '
              'coarse wire, W2-easy.'},
    {'name': 'pc-m1-cast-tooth',
     'display_name': 'Cast stator tooth (region of the one pour)',
     'material_ref': 'opt-geopolymer-ferrite',
     'material_condition': 'cast',
     'shape_ref': 'motor-m1-stator-tooth', 'shape_units': 'mm',
     'coating_ref': '', 'coating_build_mm': 0.0,
     'process_state_ref': '', 'quantity': 1,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'mu~2 and honest about it — the tooth the winding '
              'lives on, mold-fused into the yoke (ifm1-teeth-'
              'yoke).'},
    {'name': 'pc-m1-bobbin-former',
     'display_name': 'Removable bobbin former, fired ceramic',
     'material_ref': 'opt-fired-ceramic',
     'material_condition': 'fired',
     'shape_ref': '', 'shape_units': 'mm',
     'coating_ref': '', 'coating_build_mm': 0.0,
     'process_state_ref': '', 'quantity': 1,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'field-inert sleeve the coil is wound on AWAY from '
              'the machine, then slid over the tooth — the same '
              'role pc-spool-core plays for M0.'},
]

SEED_M1_COMPOSITION_NODES = [
    {'name': 'm1-tooth-bobbin',
     'display_name': 'Wound tooth — separable bobbin',
     'declared_level': 'assembly',
     'members_json': _j([
         {'ref': 'pc-magnet-wire-26awg', 'kind': 'component',
          'quantity': 1},
         {'ref': 'pc-m1-bobbin-former', 'kind': 'component',
          'quantity': 1},
         {'ref': 'pc-m1-cast-tooth', 'kind': 'component',
          'quantity': 1}]),
     'functional_ref': 'fp-m1-wound-tooth', 'genealogy_ref': '',
     'bulk_failure_mode_refs_json': _j([]),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'a bad coil is a SWAPPED coil; the m1-7 imbalance '
              'finding stays actionable per phase.'},
    {'name': 'm1-tooth-promoted',
     'display_name': 'Wound tooth — sol-gel promoted into the '
                     'stator',
     'declared_level': 'part',
     'members_json': _j([
         {'ref': 'pc-magnet-wire-26awg', 'kind': 'component',
          'quantity': 1},
         {'ref': 'pc-m1-cast-tooth', 'kind': 'component',
          'quantity': 1},
         {'ref': 'pc-sol-gel-binder', 'kind': 'component',
          'quantity': 1}]),
     'functional_ref': 'fp-m1-wound-tooth',
     'genealogy_ref': 'm1-tooth-bobbin',
     'bulk_failure_mode_refs_json': _j([
         'fm-potted-winding-crack-short',
         'fm-thermal-mismatch-stress',
         'fm-brittle-fracture']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'what promotion buys: fretting deleted over ~1e8 '
              'steps. What it spends: repairability x6. What it '
              'owes: a crack in the potting IS a short — the same '
              'bulk mode that blocks the sol-gel stator route.'},
]

SEED_M1_INTERFACES = [
    {'name': 'if-m1tb-wire-former',
     'display_name': 'Winding on former (unwindable)',
     'node_ref': 'm1-tooth-bobbin',
     'member_a': 'pc-magnet-wire-26awg',
     'member_b': 'pc-m1-bobbin-former',
     'designed_separable': True,
     'dof_removed_json': _j(['tx', 'ty', 'tz', 'rx', 'ry']),
     'retention_scheme': 'wound',
     'retention_material_requirements_json': '{}',
     'failure_mode_refs_json': _j(['fm-turn-to-turn-abrasion',
                                   'fm-fretting']),
     'equation_refs_json': _j(['eq-archard-wear-volume']),
     'realization_level': 'theoretical',
     'qualifying_act': 'wind and unwind one 300-turn coil on a '
                       'former, recover the wire',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'wound off the machine — the whole point of the '
              'former.'},
    {'name': 'if-m1tb-former-tooth',
     'display_name': 'Bobbin slid over tooth',
     'node_ref': 'm1-tooth-bobbin',
     'member_a': 'pc-m1-bobbin-former',
     'member_b': 'pc-m1-cast-tooth',
     'designed_separable': True,
     'dof_removed_json': _j(['tx', 'ty', 'rx', 'ry', 'rz']),
     'retention_scheme': 'press',
     'retention_material_requirements_json': '{}',
     'failure_mode_refs_json': _j(['fm-preload-loss',
                                   'fm-fretting']),
     'equation_refs_json': _j([]),
     'realization_level': 'theoretical',
     'qualifying_act': 'slide fit on a cast tooth: seats by hand, '
                       'stays put through 100 pulses',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the slide-on constraint EXISTS because the teeth '
              'are mold-fused into the yoke (ifm1-teeth-yoke).'},
    {'name': 'if-m1tp-wire-tooth',
     'display_name': 'Winding fused onto tooth (sol-gel)',
     'node_ref': 'm1-tooth-promoted',
     'member_a': 'pc-magnet-wire-26awg',
     'member_b': 'pc-m1-cast-tooth',
     'designed_separable': False,
     'dof_removed_json': _j(['tx', 'ty', 'tz', 'rx', 'ry', 'rz']),
     'retention_scheme': 'adhesive',
     'retention_material_requirements_json': '{}',
     'failure_mode_refs_json': _j([]),
     'equation_refs_json': _j([]),
     'realization_level': 'theoretical',
     'qualifying_act': 'the mag-24 test at M1 scale: bend a dipped '
                       'winding sample round a 3 mm former '
                       'without crazing',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'interface modes DELETED outright; the bulk modes '
              'the node lists are the price.'},
]

SEED_M1_FUNCTIONAL_PARTS = [
    {'name': 'fp-m1-wound-tooth',
     'display_name': 'M1 wound tooth (functional)',
     'purpose': 'carry one phase\'s MMF into the working gap from '
                'a coil that fits the slot',
     'allocated_role_refs_json': _j(['static-structural',
                                     'flux-carrying']),
     'archetype_ref': 'at-coil-winding',
     'tunable_toward': 'flux linkage per amp within the slot '
                       'window, six times over, with the phases '
                       'matched',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'ONE engineering-BOM row; two constructions realize '
              'it — the EBOM/MBOM split doing its job.'},
]

SEED_M1_CONSTRUCTION_VARIANTS = [
    {'name': 'cv-m1-tooth-bobbin',
     'display_name': 'Separable bobbin — wound off-machine, slid '
                     'on',
     'functional_ref': 'fp-m1-wound-tooth',
     'node_ref': 'm1-tooth-bobbin',
     'routing_ref': 'rt-m1-tooth-bobbin',
     'fill_factor_class': 'scramble',
     'selection_rationale': 'choose it for REPAIRABILITY x6 and '
                            'for the bench: a bad or imbalanced '
                            'phase (m1-7 measures all six) is a '
                            'swapped coil, not a scrapped stator. '
                            'It keeps the fretting modes the '
                            'promoted variant deletes.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'cv-m1-tooth-promoted',
     'display_name': 'Promoted — wound in place, sol-gel bound',
     'functional_ref': 'fp-m1-wound-tooth',
     'node_ref': 'm1-tooth-promoted',
     'routing_ref': 'rt-m1-tooth-promoted',
     'fill_factor_class': 'scramble',
     'selection_rationale': 'choose it to DELETE fretting and '
                            'crossover abrasion over ~1e8 steps '
                            'and make six coils structural; it '
                            'spends repairability SIX TIMES and '
                            'takes on crack-IS-a-short — the '
                            'op-bound-cure trade at the next '
                            'rung.',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
]

SEED_M1_ROUTINGS = [
    {'name': 'rt-m1-tooth-bobbin',
     'display_name': 'Wind on former, slide over tooth',
     'variant_ref': 'cv-m1-tooth-bobbin', 'per_unit': 'coil',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'x6 per machine — the first batch-shaped routing.'},
    {'name': 'rt-m1-tooth-promoted',
     'display_name': 'Wind in place, impregnate, cure',
     'variant_ref': 'cv-m1-tooth-promoted', 'per_unit': 'coil',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the promotion routing; cure is the op that ends '
              'the assembly.'},
]

SEED_M1_ROUTING_OPS = [
    {'name': 'op-m1tb-wind',
     'display_name': 'Wind coil on former',
     'routing_ref': 'rt-m1-tooth-bobbin', 'sequence': 1,
     'kind': 'join',
     'summary': 'scramble-wind 300 turns of 26 AWG on the former',
     'capability_rung_ref': 'W2', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': PROV,
     'notes': '26 AWG is W2-easy; the winder never touches the '
              'machine.'},
    {'name': 'op-m1tb-slide',
     'display_name': 'Slide bobbin over tooth',
     'routing_ref': 'rt-m1-tooth-bobbin', 'sequence': 2,
     'kind': 'join',
     'summary': 'seat the wound bobbin on its cast tooth',
     'capability_rung_ref': 'T0', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'op-m1tp-wind',
     'display_name': 'Wind coil in place',
     'routing_ref': 'rt-m1-tooth-promoted', 'sequence': 1,
     'kind': 'join',
     'summary': 'wind 300 turns directly on the tooth, in the '
                'slot — slower per coil than a former',
     'capability_rung_ref': 'W2', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'op-m1tp-impregnate',
     'display_name': 'Impregnate winding with sol-gel',
     'routing_ref': 'rt-m1-tooth-promoted', 'sequence': 2,
     'kind': 'join',
     'summary': 'wick sol-gel silica through the wound tooth',
     'capability_rung_ref': 'T0', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': PROV, 'notes': ''},
    {'name': 'op-m1tp-cure',
     'display_name': 'Cure — the promotion',
     'routing_ref': 'rt-m1-tooth-promoted', 'sequence': 3,
     'kind': 'promote',
     'summary': 'cure fuses winding and tooth into one body; the '
                'assembly stops existing and a part begins',
     'capability_rung_ref': 'T0', 'purpose_class': 'physics',
     'consumes_interface_refs_json': _j(['if-m1tb-wire-former',
                                         'if-m1tb-former-tooth']),
     'fused_interface_refs_json': _j(['if-m1tp-wire-tooth']),
     'emits_node_ref': 'm1-tooth-promoted',
     'modes_deleted_refs_json': _j(['fm-turn-to-turn-abrasion',
                                    'fm-fretting']),
     'modes_introduced_refs_json': _j([
         'fm-potted-winding-crack-short',
         'fm-thermal-mismatch-stress',
         'fm-brittle-fracture']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'same op shape as op-bound-cure — the arch-4 '
              'PROMOTE record, at the M1 rung.'},
]


def m1_construction_fork(manager):
    """The fork as a report: both variants with their LIVE derived
    levels, what promotion buys/spends/owes, and the batch fact
    (x6) that makes the choice different from M0's."""
    from composition.custom.data_refs import resolve_named
    from composition.node_basis import derive_level
    out = []
    for cv_name in ('cv-m1-tooth-bobbin', 'cv-m1-tooth-promoted'):
        cv, refusal = resolve_named(
            manager, 'ConstructionVariantDefinition', cv_name)
        if refusal:
            return {'ok': False,
                    'refusal': f'variant "{cv_name}" not booted — '
                               f'{refusal["refusal"]}',
                    'suggestion': {'knob': 'seed_m1_composition',
                                   'action': 'boot the m1-4 seeds '
                                             '(composition module '
                                             'enabled)'}}
        node_ref = getattr(cv, 'node_ref', '')
        out.append({
            'variant': cv_name,
            'displayName': getattr(cv, 'display_name', ''),
            'node': node_ref,
            'level': derive_level(manager, node_ref),
            'rationale': getattr(cv, 'selection_rationale', ''),
            'fillClass': getattr(cv, 'fill_factor_class', '')})
    return {
        'ok': True, 'functionalPart': 'fp-m1-wound-tooth',
        'variants': out,
        'batchFact': 'SIX coils per machine, FOUR machines per '
                     'printer (m1-6): the promoted variant spends '
                     'repairability 24 times per printer, and the '
                     'm1-7 imbalance finding is only actionable '
                     'while coils still swap',
        'note': 'one functional part, two constructions, levels '
                'DERIVED from interface rows — choosing is a human '
                'act recorded as the arch-4 PROMOTE op '
                '(op-m1tp-cure), never automatic'}


def seed_m1_composition(manager):
    """m1-4 rows via the upsert path. Class objects come from
    composition's own modules — same classes, more rows."""
    from composition.component_basis import PartComponentDefinition
    from composition.functional_basis import (
        ConstructionVariantDefinition, FunctionalPartDefinition,
    )
    from composition.interface_basis import InterfaceDefinition
    from composition.node_basis import CompositionNode
    from composition.routing_basis import (
        RoutingDefinition, RoutingOperation,
    )
    return upsert_seed_pairs(manager, [
        ('PartComponentDefinition', PartComponentDefinition,
         SEED_M1_PART_COMPONENTS),
        ('CompositionNode', CompositionNode,
         SEED_M1_COMPOSITION_NODES),
        ('InterfaceDefinition', InterfaceDefinition,
         SEED_M1_INTERFACES),
        ('FunctionalPartDefinition', FunctionalPartDefinition,
         SEED_M1_FUNCTIONAL_PARTS),
        ('ConstructionVariantDefinition',
         ConstructionVariantDefinition,
         SEED_M1_CONSTRUCTION_VARIANTS),
        ('RoutingDefinition', RoutingDefinition, SEED_M1_ROUTINGS),
        ('RoutingOperation', RoutingOperation,
         SEED_M1_ROUTING_OPS),
    ], tag='M1CompositionSeed')
