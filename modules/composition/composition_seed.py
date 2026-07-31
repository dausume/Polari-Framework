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
from composition.interface_basis import InterfaceDefinition
from composition.node_basis import CompositionNode
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
     'functional_ref': '', 'genealogy_ref': '',
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
     'functional_ref': '',
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
     'functional_ref': '', 'genealogy_ref': '',
     'bulk_failure_mode_refs_json': _j([
         'fm-potted-winding-crack-short',
         'fm-brittle-fracture']),
     'is_prior': True, 'provenance_id': PROV,
     'notes': 'promoted per layer, separable between layers — one '
              'object, two separability regimes. A defective layer '
              'is discarded instead of a whole coil.'},
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
    ], tag='CompositionSeed')
