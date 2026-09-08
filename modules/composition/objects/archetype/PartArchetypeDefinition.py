"""
@module composition.objects.archetype.PartArchetypeDefinition

Row class PartArchetypeDefinition of the composition module — one class per file (design §7), split
from archetype_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PartArchetypeDefinition(treeObject):
    """One recurring kind of part, with everything needed to size,
    select for, and distrust it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', summary='',
                 parameter_set_json='[]', equation_refs_json='[]',
                 failure_mode_refs_json='[]', role_refs_json='[]',
                 selection_procedure_json='[]', design_matrix_ref='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.summary = summary
        #: [{'name', 'unit', 'summary'}] — the knobs.
        self.parameter_set_json = parameter_set_json
        #: [{'name': EquationDefinition name, 'level':
        #:   EQUATION_LEVELS}] — behaviour half, by reference.
        self.equation_refs_json = equation_refs_json
        #: FailureModeDefinition names this archetype is prone to.
        self.failure_mode_refs_json = failure_mode_refs_json
        #: composition.custom.part_roles names — material half.
        self.role_refs_json = role_refs_json
        #: Ordered checks as data: [{'step', 'what', 'refuses_on'}].
        self.selection_procedure_json = selection_procedure_json
        self.design_matrix_ref = design_matrix_ref
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
