"""
@module reticulum.objects.meshsim.MeshSimResult

Row class MeshSimResult of the reticulum module — one class per file (design §7), split
from meshsim_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from reticulum.objects.meshsim._shared import TERRAIN_DISCLAIMER

class MeshSimResult(treeObject):
    """A computed plan snapshot — inputs, outputs, and the FULL
    assumptions list, so two runs are comparable and nobody mistakes
    planning math for a promise."""

    @treeObjectInit
    def __init__(self, name='', scenario_name='', computed_at='',
                 inputs_json='{}', outputs_json='{}',
                 assumptions_json='[]', disclaimer=TERRAIN_DISCLAIMER,
                 notes='', manager=None):
        self.name = name
        self.scenario_name = scenario_name
        self.computed_at = computed_at
        self.inputs_json = inputs_json
        self.outputs_json = outputs_json
        self.assumptions_json = assumptions_json
        self.disclaimer = disclaimer
        self.notes = notes
