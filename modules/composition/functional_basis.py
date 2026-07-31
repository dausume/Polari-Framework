"""
@module composition.functional_basis

arch-3: the EBOM/MBOM split (PART_COMPOSITION_PRACTICE_MAP §1.1).
Industry keeps two linked views and so do we:

- FunctionalPartDefinition — what the design NEEDS (one functional
  stator), carrying purpose, allocated roles and tunability. This is
  the engineering-BOM side.
- ConstructionVariantDefinition — one way of BUILDING it (simple /
  bound / layered-bound are three variants of ONE functional part,
  mag-26 requirement 1). Fill class, routing and rationale live
  here: they are manufacturing-BOM facts.

"Tunable toward a purpose" is ALLOCATION-side (handover §5.4): it is
a property of the functional slot in a design, not of the casting —
so it lives on the functional row, never on the node.

@consumers polariServer seed passes, composition.composition_seed,
composition.selftest_composition
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from composition.data_refs import resolve_named, rows
from composition.fill_models import FILL_CLASSES, fill_for_class
from composition.node_basis import derive_level


class FunctionalPartDefinition(treeObject):
    """The functional slot: what the design needs done."""

    @treeObjectInit
    def __init__(self, name='', display_name='', purpose='',
                 allocated_role_refs_json='[]', archetype_ref='',
                 tunable_toward='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: What it is FOR, in a sentence a builder can act on.
        self.purpose = purpose
        #: composition.part_roles role names ALLOCATED to this slot
        #: — requirements-side, screened by role_viability.
        self.allocated_role_refs_json = allocated_role_refs_json
        #: PartArchetypeDefinition (arch-5) this slot instantiates.
        self.archetype_ref = archetype_ref
        #: The outcome this slot is optimised against in THIS
        #: design (allocation-side, handover §5.4).
        self.tunable_toward = tunable_toward
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ConstructionVariantDefinition(treeObject):
    """One way of building a functional part — an MBOM realization,
    first-class alternative of the SAME functional part."""

    @treeObjectInit
    def __init__(self, name='', display_name='', functional_ref='',
                 node_ref='', routing_ref='', fill_factor_class='n/a',
                 selection_rationale='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.functional_ref = functional_ref
        #: The CompositionNode this variant builds — level derives
        #: from ITS interface rows.
        self.node_ref = node_ref
        #: RoutingDefinition (arch-4); process step COUNT derives
        #: from the routing, it is not stamped here.
        self.routing_ref = routing_ref
        #: Fill is a property of the CONSTRUCTION (mag-26 req 2).
        self.fill_factor_class = (
            fill_factor_class if fill_factor_class in FILL_CLASSES
            else 'n/a')
        #: What this variant is FOR — inspectability, packing,
        #: step count, repairability. The choice must be knowing.
        self.selection_rationale = selection_rationale
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


def variants_of(manager, functional_name):
    return [v for v in rows(manager, 'ConstructionVariantDefinition')
            if getattr(v, 'functional_ref', '') == functional_name]


def variant_report(manager, functional_name,
                   wound_diameter_mm=None, wall_mm=None):
    """One functional part, all its constructions: derived level,
    fill (computed from the class when geometry is stated, refused
    honestly when not), repairability implied by the level."""
    fp, refusal = resolve_named(manager, 'FunctionalPartDefinition',
                                functional_name)
    if refusal:
        return {'ok': False, **refusal}
    variants = variants_of(manager, functional_name)
    if not variants:
        return {'ok': False, 'functional': functional_name,
                'refusal': 'no construction variants — a functional '
                           'part with no way to build it is a '
                           'requirement, not a design',
                'suggestion': {'knob': 'ConstructionVariantDefinition',
                               'action': 'add at least one variant '
                                         'with its node'}}
    out = []
    for v in variants:
        node_ref = getattr(v, 'node_ref', '')
        level = derive_level(manager, node_ref)
        fill = fill_for_class(getattr(v, 'fill_factor_class', 'n/a'),
                              wound_diameter_mm, wall_mm)
        derived = level.get('derived', '')
        out.append({
            'variant': getattr(v, 'name', ''),
            'displayName': getattr(v, 'display_name', ''),
            'node': node_ref,
            'level': level if not level.get('ok') else derived,
            'separableSet': level.get('separableSet', []),
            'boundSet': level.get('boundSet', []),
            # Repairability FOLLOWS from separability — a promoted
            # interface set is exactly what cannot be repaired.
            'repairable': (level.get('ok', False)
                           and derived == 'assembly'),
            'fillClass': getattr(v, 'fill_factor_class', 'n/a'),
            'fill': fill.get('fill') if fill.get('ok') else None,
            'fillNote': fill.get('refusal', fill.get('note', '')),
            'routing': getattr(v, 'routing_ref', '') or
            'routing-unstated (arch-4)',
            'rationale': getattr(v, 'selection_rationale', ''),
        })
    return {
        'ok': True, 'functional': functional_name,
        'purpose': getattr(fp, 'purpose', ''),
        'tunableToward': getattr(fp, 'tunable_toward', ''),
        'allocatedRoles': json.loads(
            getattr(fp, 'allocated_role_refs_json', '') or '[]'),
        'variants': out, 'count': len(out),
        'note': 'these are ALTERNATIVES of one functional part, not '
                'different parts — fill, steps and repairability '
                'are properties of the construction, and choosing '
                'between them is an MBOM decision the EBOM row '
                'survives.',
    }
