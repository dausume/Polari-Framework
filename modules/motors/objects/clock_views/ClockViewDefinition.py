"""
@module motors.objects.clock_views.ClockViewDefinition

Row class ClockViewDefinition of the motors module — one class per file (design §7), split
from clock_views_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from motors.objects.clock_views._shared import DISCIPLINES

class ClockViewDefinition(treeObject):
    """One specialized view: discipline + ordered data sections."""

    @treeObjectInit
    def __init__(self, name='', display_name='', discipline='goals',
                 description='', sections_json='[]',
                 scene_json='', scale_support='m0-only',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.discipline = (discipline if discipline in DISCIPLINES
                           else 'goals')
        self.description = description
        #: viz-1: {'base': <SimSpaceDefinition>, 'layers': [names],
        #: 'defaultOn': [names]} — the view's 3D assembly; layers
        #: are ClockSceneLayerDefinition rows, stackable.
        self.scene_json = scene_json
        #: [{'name', 'source', 'args': {...}}] — source is a key in
        #: SECTION_SOURCES; args merge under any caller overrides.
        self.sections_json = sections_json
        #: 'any-scale' = parameterized by goal/scale rows;
        #: 'm0-only' = the deep engines run on the built M0 today,
        #: and SAY so — per-scale depth is the growth path, not an
        #: assumption.
        self.scale_support = scale_support
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
