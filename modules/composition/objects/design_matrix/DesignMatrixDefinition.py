"""
@module composition.objects.design_matrix.DesignMatrixDefinition

Row class DesignMatrixDefinition of the composition module — one class per file (design §7), split
from design_matrix_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DesignMatrixDefinition(treeObject):
    """The knob→outcome structure of one archetype's equations."""

    @treeObjectInit
    def __init__(self, name='', display_name='', archetype_ref='',
                 entries_json='[]', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.archetype_ref = archetype_ref
        #: [{'knob', 'outcome', 'coupling': direct|inverse|both,
        #:   'via': the equation/cancellation that makes it so}].
        #: Absent (knob, outcome) pairs mean NO coupling — the
        #: cancellations are the empty cells, and the 'via' of a
        #: present cell should say what canceled to keep others
        #: empty (turns cancel in the voltage equation).
        self.entries_json = entries_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
