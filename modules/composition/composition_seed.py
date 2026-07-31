"""
@module composition.composition_seed

arch-2 seeds: the mag-26 worked example — three constructions of ONE
functional stator, expressed as composition rows so the level
derivation is exercised by real geometry, not toy fixtures:

  stator-simple    enamelled wire on a spool     -> assembly
  stator-bound     wound, then sol-gel over      -> part
  stator-layered   grooved layers bound per      -> part-with-
                   layer, snapped concentrically    separable-sub-parts

Material refs point at LIVE MagneticMaterialOption catalog names
(data references, §3.2). All seeding goes through seed_upsert — the
arch-1 path — so a changed seed field reaches live rows.

@consumers polariServer seed passes, composition.selftest_composition
"""

import json

from composition.component_basis import PartComponentDefinition
from composition.failure_modes import (
    FailureModeDefinition, SEED_FAILURE_MODES,
)
from composition.functional_basis import (
    ConstructionVariantDefinition, FunctionalPartDefinition,
)
from composition.interface_basis import InterfaceDefinition
from composition.node_basis import CompositionNode
from composition.routing_basis import (
    RoutingDefinition, RoutingOperation,
)
from composition.seed_upsert import upsert_seed_pairs

PROV = 'arch-2'


def _j(obj):
    return json.dumps(obj)


SEED_PART_COMPONENTS = [
    {'name': 'pc-magnet-wire-32awg',
     'display_name': 'Magnet wire, 32 AWG enamelled',
     'material_ref': 'opt-copper-magnet-wire',
     'material_condition': 'drawn-annealed',
     'shape_ref': '', 'shape_units': 'mm',
     # Coating is NOT the material: build adds to diameter, and the
     # window pays for it as a square (mag-24; heavy-build enamel
     # ~0.025 mm commercial figure).
     'coating_ref': 'enamel-polyurethane',
     'coating_build_mm': 0.025,
     'process_state_ref': '', 'quantity': 1,
     'is_prior': True, 'provenance_id': PROV,
     'notes': '32 AWG per mag-25 simplest-case-first: gauge sets '
              'voltage (turns cancel), and 32-38 AWG runs direct '
              'off one 1.5 V cell.'},
    {'name': 'pc-spool-core',
     'display_name': 'Spool / bobbin core, fired ceramic',
     'material_ref': 'opt-fired-ceramic',
     'material_condition': 'fired',
     'shape_ref': '', 'shape_units': 'mm',
     'coating_ref': '', 'coating_build_mm': 0.0,
     'process_state_ref': '', 'quantity': 1,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'field-inert body the winding lives on.'},
    {'name': 'pc-sol-gel-binder',
     'display_name': 'Sol-gel silica binder (potting)',
     'material_ref': 'opt-plain-solgel-mortar',
     'material_condition': 'cured',
     'shape_ref': '', 'shape_units': 'mm',
     'coating_ref': '', 'coating_build_mm': 0.0,
     'process_state_ref': '', 'quantity': 1,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the promotion agent: cures the winding into one '
              'solid body. Brittle — its crack-short mode is the '
              'bulk failure the bound stator trades for.'},
    {'name': 'pc-grooved-layer-shell',
     'display_name': 'Grooved winding layer shell',
     'material_ref': 'opt-fired-ceramic',
     'material_condition': 'fired',
     'shape_ref': '', 'shape_units': 'mm',
     'coating_ref': '', 'coating_build_mm': 0.0,
     'process_state_ref': '', 'quantity': 3,
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'grooves beat scramble only while the wall stays '
              'under ~14% of wound wire diameter (mag-26); snap '
              'features need elastic deflection the fired body '
              'does not have — the recorded two-material conflict.'},
]

#: The snap feature's demands vs the body's — mag-26's unresolved
#: conflict, stored where it belongs.
_SNAP_DEMANDS = _j({'all': [
    {'prop': 'elastic_strain_pct', 'op': '>=', 'value': 2.0,
     'why': 'a snap engages by deflecting and returning; fired '
            'ceramic and geopolymer crack instead of flexing, so '
            'the snap FEATURE may need a tougher material than the '
            'body (two-material part for non-electrical reasons)'}]})

SEED_INTERFACES = [
    # ----- stator-simple: everything separable -> assembly -----
    {'name': 'if-simple-wire-spool',
     'display_name': 'Winding on spool (unwindable)',
     'node_ref': 'stator-simple',
     'member_a': 'pc-magnet-wire-32awg', 'member_b': 'pc-spool-core',
     'designed_separable': True,
     'dof_removed_json': _j(['tx', 'ty', 'tz', 'rx', 'ry']),
     'retention_scheme': 'wound',
     'retention_material_requirements_json': '{}',
     'failure_mode_refs_json': _j(['fm-turn-to-turn-abrasion',
                                   'fm-fretting']),
     'equation_refs_json': _j(['eq-archard-wear-volume']),
     'realization_level': 'made-and-measured',
     'qualifying_act': 'the M0 build wound and unwound this joint',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'repairable: you are meant to get the wire back off.'},
    # ----- stator-bound: every interface promoted -> part -----
    {'name': 'if-bound-wire-wire',
     'display_name': 'Turn-to-turn, fused in sol-gel',
     'node_ref': 'stator-bound',
     'member_a': 'pc-magnet-wire-32awg',
     'member_b': 'pc-magnet-wire-32awg',
     'designed_separable': False,
     'dof_removed_json': _j(['tx', 'ty', 'tz', 'rx', 'ry', 'rz']),
     'retention_scheme': 'adhesive',
     'retention_material_requirements_json': '{}',
     # Promotion DELETED the interface modes — outright, not
     # reduced: a fused turn cannot fret (mag-26).
     'failure_mode_refs_json': _j([]),
     'equation_refs_json': _j([]),
     'realization_level': 'recipe-seeded',
     'qualifying_act': 'bend a dipped winding sample round a 3 mm '
                       'former without crazing (mag-24 test)',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'the coil becomes STRUCTURAL: flanges no longer '
              'carry the winding alone and can thin, giving back '
              'some of the window the coating cost.'},
    {'name': 'if-bound-wire-spool',
     'display_name': 'Winding to spool, fused in sol-gel',
     'node_ref': 'stator-bound',
     'member_a': 'pc-magnet-wire-32awg', 'member_b': 'pc-spool-core',
     'designed_separable': False,
     'dof_removed_json': _j(['tx', 'ty', 'tz', 'rx', 'ry', 'rz']),
     'retention_scheme': 'adhesive',
     'retention_material_requirements_json': '{}',
     'failure_mode_refs_json': _j([]),
     'equation_refs_json': _j([]),
     'realization_level': 'recipe-seeded',
     'qualifying_act': 'same 3 mm former test',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'not repairable — whole cost amortises over ONE '
              'life (lifecycle_cost).'},
    # ----- stator-layered: two regimes in one object -----
    {'name': 'if-layer-wire-groove',
     'display_name': 'Wire in groove, bound per layer',
     'node_ref': 'stator-layered',
     'member_a': 'pc-magnet-wire-32awg',
     'member_b': 'pc-grooved-layer-shell',
     'designed_separable': False,
     'dof_removed_json': _j(['tx', 'ty', 'tz', 'rx', 'ry', 'rz']),
     'retention_scheme': 'groove',
     'retention_material_requirements_json': '{}',
     'failure_mode_refs_json': _j([]),
     'equation_refs_json': _j([]),
     'realization_level': 'theoretical',
     'qualifying_act': 'wind + bind one grooved layer, measure fill',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'promoted PER LAYER — the named interface set.'},
    {'name': 'if-layer-snap',
     'display_name': 'Layer-to-layer snap (concentric)',
     'node_ref': 'stator-layered',
     'member_a': 'pc-grooved-layer-shell',
     'member_b': 'pc-grooved-layer-shell',
     'designed_separable': True,
     'dof_removed_json': _j(['tx', 'ty', 'rx', 'ry']),
     'retention_scheme': 'snap',
     'retention_material_requirements_json': _SNAP_DEMANDS,
     'failure_mode_refs_json': _j(['fm-fretting']),
     'equation_refs_json': _j([]),
     'realization_level': 'theoretical',
     'qualifying_act': 'snap two fired layers 10x without cracking '
                       '— directly tests the elastic-deflection '
                       'conflict',
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'a rigid floor forbids nesting: choose snap-on for '
              'per-layer inspectability and yield, NOT packing '
              '(forfeits ~13% fill, mag-26).'},
]

SEED_COMPOSITION_NODES = [
    {'name': 'stator-simple',
     'display_name': 'Stator — simple (enamelled wire on spool)',
     'declared_level': 'assembly',
     'members_json': _j([
         {'ref': 'pc-magnet-wire-32awg', 'kind': 'component',
          'quantity': 1},
         {'ref': 'pc-spool-core', 'kind': 'component',
          'quantity': 1}]),
     'functional_ref': 'fp-m0-stator', 'genealogy_ref': '',
     'bulk_failure_mode_refs_json': _j([]),
     'is_prior': True, 'provenance_id': PROV,
     'notes': '1 process step; fully repairable.'},
    {'name': 'stator-bound',
     'display_name': 'Stator — bound (sol-gel over the winding)',
     'declared_level': 'part',
     'members_json': _j([
         {'ref': 'pc-magnet-wire-32awg', 'kind': 'component',
          'quantity': 1},
         {'ref': 'pc-spool-core', 'kind': 'component',
          'quantity': 1},
         {'ref': 'pc-sol-gel-binder', 'kind': 'component',
          'quantity': 1}]),
     'functional_ref': 'fp-m0-stator',
     # arch-4 will make this a recorded PROMOTE operation; the
     # genealogy pointer is already true today.
     'genealogy_ref': 'stator-simple',
     'bulk_failure_mode_refs_json': _j([
         'fm-potted-winding-crack-short',
         'fm-thermal-mismatch-stress',
         'fm-brittle-fracture']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'what promotion bought: fretting and abrasion deleted '
              'outright. What it spent: repairability. What it now '
              'owes: the brittle bulk modes listed here.'},
    {'name': 'stator-layered',
     'display_name': 'Stator — layered bound (snap-on grooved '
                     'layers)',
     'declared_level': 'part-with-separable-sub-parts',
     'members_json': _j([
         {'ref': 'pc-magnet-wire-32awg', 'kind': 'component',
          'quantity': 1},
         {'ref': 'pc-grooved-layer-shell', 'kind': 'component',
          'quantity': 3},
         {'ref': 'pc-sol-gel-binder', 'kind': 'component',
          'quantity': 3}]),
     'functional_ref': 'fp-m0-stator', 'genealogy_ref': '',
     'bulk_failure_mode_refs_json': _j([
         'fm-potted-winding-crack-short',
         'fm-brittle-fracture']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'promoted per layer, separable between layers — one '
              'object, two separability regimes. A defective layer '
              'is discarded instead of a whole coil.'},
]


# ----- arch-3: the EBOM/MBOM split — ONE functional stator, -----
# ----- three constructions as first-class alternatives      -----

SEED_FUNCTIONAL_PARTS = [
    {'name': 'fp-m0-stator',
     'display_name': 'M0 stator (functional)',
     'purpose': 'hold the drive winding and carry its flux to the '
                'rotor gap',
     'allocated_role_refs_json': _j(['static-structural',
                                     'flux-carrying']),
     'archetype_ref': '',
     'tunable_toward': 'flux linkage per amp within the stated '
                       'winding window',
     'is_prior': True, 'provenance_id': 'arch-3',
     'notes': 'the ONE engineering-BOM row all three constructions '
              'realize — same roles as lavet-v2-stator.'},
]

SEED_CONSTRUCTION_VARIANTS = [
    {'name': 'cv-stator-simple',
     'display_name': 'Simple — enamelled wire on a spool',
     'functional_ref': 'fp-m0-stator', 'node_ref': 'stator-simple',
     'routing_ref': 'rt-stator-simple', 'fill_factor_class': 'scramble',
     'selection_rationale': 'the honest baseline: one operation, no '
                            'chemistry after winding, and the wire '
                            'is recoverable. Everything else is '
                            'measured against this.',
     'is_prior': True, 'provenance_id': 'arch-3', 'notes': ''},
    {'name': 'cv-stator-bound',
     'display_name': 'Bound — wound, then sol-gel over',
     'functional_ref': 'fp-m0-stator', 'node_ref': 'stator-bound',
     'routing_ref': 'rt-stator-bound', 'fill_factor_class': 'scramble',
     'selection_rationale': 'choose it to DELETE fretting and '
                            'crossover abrasion outright over 3.2e8 '
                            'cycles, and to make the coil '
                            'structural; it spends repairability '
                            'and takes on the brittle crack-short '
                            'mode.',
     'is_prior': True, 'provenance_id': 'arch-3', 'notes': ''},
    {'name': 'cv-stator-layered-bound',
     'display_name': 'Layered bound — grooved snap-on layers',
     'functional_ref': 'fp-m0-stator', 'node_ref': 'stator-layered',
     'routing_ref': 'rt-stator-layered',
     # Snap-on = rigid floor: the construction CLASS carries the
     # packing consequence (0.785 ceiling, not 0.907).
     'fill_factor_class': 'ordered-rigid-floor',
     'selection_rationale': 'choose it for PER-LAYER INSPECTABILITY '
                            'and yield — a defective layer is '
                            'discarded instead of a whole coil — '
                            'NOT for packing: snapping forfeits '
                            '~13% of the fill nesting would reach, '
                            'and past ~14% wall it is worse than '
                            'scramble.',
     'is_prior': True, 'provenance_id': 'arch-3', 'notes': ''},
]


# ----- arch-4: routings — step counts DERIVE, promotion is a -----
# ----- recorded operation with the Boothroyd-Dewhurst gate   -----

SEED_ROUTINGS = [
    {'name': 'rt-stator-simple', 'display_name': 'Wind on spool',
     'variant_ref': 'cv-stator-simple', 'per_unit': 'part',
     'is_prior': True, 'provenance_id': 'arch-4', 'notes': ''},
    {'name': 'rt-stator-bound',
     'display_name': 'Wind, impregnate, cure',
     'variant_ref': 'cv-stator-bound', 'per_unit': 'part',
     'is_prior': True, 'provenance_id': 'arch-4', 'notes': ''},
    {'name': 'rt-stator-layered',
     'display_name': 'Form, lay, bind, snap — per layer',
     'variant_ref': 'cv-stator-layered-bound', 'per_unit': 'layer',
     'is_prior': True, 'provenance_id': 'arch-4',
     'notes': 'mag-26: four process steps PER LAYER instead of one '
              'for the whole coil.'},
]

SEED_ROUTING_OPS = [
    # -- simple: one step, no chemistry after winding --
    {'name': 'op-simple-wind', 'display_name': 'Wind wire on spool',
     'routing_ref': 'rt-stator-simple', 'sequence': 1,
     'kind': 'join',
     'summary': 'scramble-wind enamelled wire onto the spool',
     'capability_rung_ref': 'W2', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': 'arch-4',
     'notes': 'W2 = fine wire (32-38 AWG, carbide dies) per '
              'wire_ladder — the mag-25 correction.'},
    # -- bound: wind, impregnate, then THE promotion --
    {'name': 'op-bound-wind', 'display_name': 'Wind wire on spool',
     'routing_ref': 'rt-stator-bound', 'sequence': 1,
     'kind': 'join', 'summary': 'as op-simple-wind',
     'capability_rung_ref': 'W2', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': 'arch-4', 'notes': ''},
    {'name': 'op-bound-impregnate',
     'display_name': 'Impregnate winding with sol-gel',
     'routing_ref': 'rt-stator-bound', 'sequence': 2,
     'kind': 'join',
     'summary': 'wick sol-gel silica through the wound coil',
     'capability_rung_ref': 'T0', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': 'arch-4',
     'notes': 'T0 = cast/bench tolerance rung; a dip tank, not a '
              'line — batch suffices at our volume (§3.8).'},
    {'name': 'op-bound-cure',
     'display_name': 'Cure — the promotion',
     'routing_ref': 'rt-stator-bound', 'sequence': 3,
     'kind': 'promote',
     'summary': 'cure fuses the winding into one solid body; the '
                'assembly stops existing and a part begins',
     'capability_rung_ref': 'T0', 'purpose_class': 'physics',
     'consumes_interface_refs_json': _j(['if-simple-wire-spool']),
     'fused_interface_refs_json': _j(['if-bound-wire-wire',
                                      'if-bound-wire-spool']),
     'emits_node_ref': 'stator-bound',
     'modes_deleted_refs_json': _j(['fm-turn-to-turn-abrasion',
                                    'fm-fretting']),
     'modes_introduced_refs_json': _j([
         'fm-potted-winding-crack-short',
         'fm-thermal-mismatch-stress']),
     'reversibility_spent': 'the wire is not recoverable: the whole '
                            'cost amortises over ONE life — a '
                            'lifecycle_cost term, not a footnote',
     'dfa_justification_json': _j({
         'if-bound-wire-wire': {
             'moves_relative': False, 'different_material': False,
             'separable_for_service': False,
             'why': 'turns must NOT move (fretting over 3.2e8 '
                    'cycles is the enemy), and the service model '
                    'for a failed coil is rewind-from-new, which '
                    'the simple variant keeps available'},
         'if-bound-wire-spool': {
             'moves_relative': False, 'different_material': True,
             'separable_for_service': False,
             'why': 'different materials (copper on ceramic) is a '
                    'reason to keep separate PARTS, not separate '
                    'MOTION — fusing is allowed, and the thermal '
                    'mismatch it locks in is on the record as '
                    'introduced stress'}}),
     'qualifying_act': 'bend a dipped winding sample round a 3 mm '
                       'former without crazing (mag-24) — opens or '
                       'closes the sol-gel option in one afternoon',
     'is_prior': True, 'provenance_id': 'arch-4', 'notes': ''},
    # -- layered: four steps PER LAYER, promotion per layer --
    {'name': 'op-layer-form',
     'display_name': 'Form grooved layer shell',
     'routing_ref': 'rt-stator-layered', 'sequence': 1,
     'kind': 'shape',
     'summary': 'mould a grooved shell at pitch near the wound '
                'wire diameter',
     'capability_rung_ref': 'T2', 'purpose_class': 'tolerance',
     'is_prior': True, 'provenance_id': 'arch-4',
     'notes': 'the groove pitch is a TOLERANCE spec: wall under '
              '~14% of wound diameter or the ordering loses to '
              'scramble.'},
    {'name': 'op-layer-lay-wire',
     'display_name': 'Lay wire into grooves',
     'routing_ref': 'rt-stator-layered', 'sequence': 2,
     'kind': 'join', 'summary': 'one turn per groove, ordered',
     'capability_rung_ref': 'W2', 'purpose_class': 'physics',
     'is_prior': True, 'provenance_id': 'arch-4', 'notes': ''},
    {'name': 'op-layer-bind',
     'display_name': 'Bind layer — promotion per layer',
     'routing_ref': 'rt-stator-layered', 'sequence': 3,
     'kind': 'promote',
     'summary': 'sol-gel over the laid wire fuses THIS layer; the '
                'layers themselves stay separable',
     'capability_rung_ref': 'T0', 'purpose_class': 'yield',
     'consumes_interface_refs_json': _j([]),
     'fused_interface_refs_json': _j(['if-layer-wire-groove']),
     'emits_node_ref': 'stator-layered',
     'modes_deleted_refs_json': _j([]),
     'modes_introduced_refs_json': _j([
         'fm-potted-winding-crack-short']),
     'reversibility_spent': 'a bound layer cannot be unwound — but '
                            'the yield unit shrinks to the LAYER: '
                            'a defective layer is discarded '
                            'instead of a whole coil',
     'dfa_justification_json': _j({
         'if-layer-wire-groove': {
             'moves_relative': False, 'different_material': True,
             'separable_for_service': False,
             'why': 'service model is replace-the-layer, not '
                    'unwind-the-wire — separability moved UP one '
                    'level to the snap, where it is kept'}}),
     'qualifying_act': 'wind + bind ONE grooved layer and measure '
                       'its fill against the derived 0.527/0.600 '
                       'crossover',
     'is_prior': True, 'provenance_id': 'arch-4',
     'notes': 'purpose_class=yield: this step exists to shrink the '
              'scrap unit, not for physics.'},
    {'name': 'op-layer-snap',
     'display_name': 'Snap next layer on',
     'routing_ref': 'rt-stator-layered', 'sequence': 4,
     'kind': 'join',
     'summary': 'concentric snap onto the layer below — DESIGNED '
                'separable, deliberately not promoted',
     'capability_rung_ref': 'T2', 'purpose_class': 'tolerance',
     'is_prior': True, 'provenance_id': 'arch-4',
     'notes': 'the elastic-deflection-vs-brittle-body conflict '
              'lives on if-layer-snap, unresolved and recorded.'},
]


def seed_composition(manager):
    """All composition seeds, through the arch-1 upsert path."""
    return upsert_seed_pairs(manager, [
        ('FailureModeDefinition', FailureModeDefinition,
         SEED_FAILURE_MODES),
        ('PartComponentDefinition', PartComponentDefinition,
         SEED_PART_COMPONENTS),
        ('CompositionNode', CompositionNode,
         SEED_COMPOSITION_NODES),
        ('InterfaceDefinition', InterfaceDefinition,
         SEED_INTERFACES),
        ('FunctionalPartDefinition', FunctionalPartDefinition,
         SEED_FUNCTIONAL_PARTS),
        ('ConstructionVariantDefinition',
         ConstructionVariantDefinition, SEED_CONSTRUCTION_VARIANTS),
        ('RoutingDefinition', RoutingDefinition, SEED_ROUTINGS),
        ('RoutingOperation', RoutingOperation, SEED_ROUTING_OPS),
    ], tag='CompositionSeed')
