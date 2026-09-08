"""
@module climate.objects.sim_binding.AtmosphereSeriesBinding

Row class AtmosphereSeriesBinding of the climate module — one class per file (design §7), split
from sim_binding_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from climate.objects.sim_binding._shared import BINDING_MODES

class AtmosphereSeriesBinding(treeObject):
    """One simulation input bound to one measured series.

    The row is the audit trail: which target field, which series,
    which mode, what was written, WHAT IT REPLACED, and when.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', target_class='',
                 target_row='', target_field='', series_ref='',
                 mode='latest', year=0.0, enabled=True,
                 last_applied_value=0.0, replaced_value=0.0,
                 last_applied_at='', last_source_year=0.0,
                 refusal='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: the class whose row this binding writes into. Named as
        #: data so a binding is not a hard-coded reference to
        #: aquaponics - any simulation input can be bound.
        self.target_class = target_class
        self.target_row = target_row
        self.target_field = target_field
        self.series_ref = series_ref
        self.mode = mode if mode in BINDING_MODES else 'latest'
        self.year = year
        self.enabled = enabled
        self.last_applied_value = last_applied_value
        #: WHAT THE SEEDED CONSTANT WAS. Kept so the binding is
        #: reversible and so a reader can see how far the guess
        #: was from the measurement.
        self.replaced_value = replaced_value
        self.last_applied_at = last_applied_at
        self.last_source_year = last_source_year
        self.refusal = refusal
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
