"""
@module sifet.objects.si_refinement.RefinementStep

Row class RefinementStep of the sifet module — one class per file (design §7), split
from si_refinement_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class RefinementStep(treeObject):
    """One unit operation that moves silicon up the ladder; its
    model kind + parameters are DATA so route_simulation can push
    an impurity vector through it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', order=0,
                 chemistry='', inputs_json='[]', outputs_json='[]',
                 purity_in_grade='', purity_out_grade='',
                 temperature_c=0.0, pressure_pa=101325.0,
                 energy_kwh_per_kg=0.0, energy_range_json='[0, 0]',
                 model_kind='none', model_params_json='{}',
                 openness='open-research', openness_reasoning='',
                 equipment_class='', citations='[]', notes='',
                 confidence='prior', is_prior=True, manager=None):
        self.name = name
        self.display_name = display_name
        self.order = order
        self.chemistry = chemistry
        self.inputs_json = inputs_json
        self.outputs_json = outputs_json
        self.purity_in_grade = purity_in_grade
        self.purity_out_grade = purity_out_grade
        self.temperature_c = temperature_c
        self.pressure_pa = pressure_pa
        self.energy_kwh_per_kg = energy_kwh_per_kg
        self.energy_range_json = energy_range_json
        self.model_kind = model_kind
        self.model_params_json = model_params_json
        self.openness = openness
        self.openness_reasoning = openness_reasoning
        self.equipment_class = equipment_class
        self.citations = citations
        self.notes = notes
        self.confidence = confidence
        self.is_prior = is_prior
