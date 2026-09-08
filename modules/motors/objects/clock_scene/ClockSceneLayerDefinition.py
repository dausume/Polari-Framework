"""
@module motors.objects.clock_scene.ClockSceneLayerDefinition

Row class ClockSceneLayerDefinition of the motors module — one class per file (design §7), split
from clock_scene_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from motors.objects.clock_scene._shared import LAYER_KINDS

class ClockSceneLayerDefinition(treeObject):
    """One 3D visualization layer: kind + engine + mapping data."""

    @treeObjectInit
    def __init__(self, name='', display_name='',
                 kind='part-coloring', source='', params_json='{}',
                 style_json='{}', description='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.kind = kind if kind in LAYER_KINDS else 'part-coloring'
        self.source = source
        self.params_json = params_json
        self.style_json = style_json
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
