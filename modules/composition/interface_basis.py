"""
@module composition.interface_basis

arch-2: the INTERFACE as a first-class row — the load-bearing idea
of the whole schema. mag-26 proved promotion attaches to a NAMED
INTERFACE SET, never to a whole assembly, so interfaces need
identity, ownership, and their own evidence level (practice: ICDs,
CAD mates, the FMEA boundary — PART_COMPOSITION_PRACTICE_MAP §2).

`designed_separable` is THE level-deciding bit: a node whose
interfaces are all non-separable is a part; all separable, an
assembly; mixed, a part with separable sub-parts (the layered
stator — one object, two separability regimes).

@consumers composition.node_basis, composition.routing_basis,
polariServer seed passes
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: The six rigid-body degrees of freedom a mate can remove.
DOF_AXES = ('tx', 'ty', 'tz', 'rx', 'ry', 'rz')

#: How the interface holds — each scheme carries its own material
#: demands (a snap needs elastic deflection; fired ceramic cracks
#: instead of flexing — the mag-26 conflict, recorded not glossed).
RETENTION_SCHEMES = ('snap', 'groove', 'fastener', 'adhesive',
                     'mortar', 'press', 'wound', 'none')


class InterfaceDefinition(treeObject):
    """One designed (or promoted-away) boundary between two members
    of a CompositionNode."""

    @treeObjectInit
    def __init__(self, name='', display_name='', node_ref='',
                 member_a='', member_b='', designed_separable=True,
                 dof_removed_json='[]', retention_scheme='none',
                 retention_material_requirements_json='{}',
                 failure_mode_refs_json='[]', equation_refs_json='[]',
                 realization_level='theoretical', qualifying_act='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        #: Owning CompositionNode. Ownership does real work: a
        #: promoted part's internal interfaces belong to IT, so an
        #: assembly one level up derives from its OWN boundaries
        #: only.
        self.node_ref = node_ref
        #: Member refs within the owning node (component or node
        #: names as listed in its members_json).
        self.member_a = member_a
        self.member_b = member_b
        #: True = meant to come apart (assembly-side); False = not
        #: meant to (part-side / promoted).
        self.designed_separable = designed_separable
        #: JSON subset of DOF_AXES — the mate, machine-checkable.
        self.dof_removed_json = dof_removed_json
        self.retention_scheme = retention_scheme
        #: Role-predicate-shaped demands the retention FEATURE puts
        #: on its material — which may conflict with the body's
        #: (mag-26 req 3: a part may need two materials for reasons
        #: that are not electrical).
        self.retention_material_requirements_json = \
            retention_material_requirements_json
        #: INTERFACE-locus FailureModeDefinition names. These die
        #: with the interface when a promotion consumes it.
        self.failure_mode_refs_json = failure_mode_refs_json
        #: EquationDefinition names (interface equations: friction,
        #: preload, fretting) — retired with the row, by
        #: construction.
        self.equation_refs_json = equation_refs_json
        #: Interfaces EARN evidence like parts do (practice: IRL —
        #: integration readiness). Same ladder as materials.
        self.realization_level = realization_level
        #: The named measurement that would promote it.
        self.qualifying_act = qualifying_act
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
