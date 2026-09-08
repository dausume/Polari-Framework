"""
@module reticulum.objects.meshsim.MeshSimNode

Row class MeshSimNode of the reticulum module — one class per file (design §7), split
from meshsim_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MeshSimNode(treeObject):
    """A placed node in a scenario: local meters; elevation is
    RECORDED but UNUSED (the disclaimer says why)."""

    @treeObjectInit
    def __init__(self, name='', scenario_name='', x_m=0.0, y_m=0.0,
                 elevation_m=0.0, device_model_name='',
                 role='observer', notes='', manager=None):
        self.name = name
        self.scenario_name = scenario_name
        self.x_m = x_m
        self.y_m = y_m
        self.elevation_m = elevation_m
        self.device_model_name = device_model_name
        self.role = role
        self.notes = notes
