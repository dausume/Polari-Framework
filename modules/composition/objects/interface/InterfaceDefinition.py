"""
@module composition.objects.interface.InterfaceDefinition

Row class InterfaceDefinition of the composition module — one class per file (design §7), split
from interface_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
