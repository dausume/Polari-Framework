"""
@module composition.objects.functional.FunctionalPartDefinition

Row class FunctionalPartDefinition of the composition module — one class per file (design §7), split
from functional_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
        #: composition.custom.part_roles role names ALLOCATED to this slot
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
