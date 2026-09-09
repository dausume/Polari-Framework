"""
@module printing_suite.objects.printing.SliceJob

SliceJob — a shape + a profile handed to a slicer.
"""
from objectTreeDecorators import treeObject, treeObjectInit

SLICE_STATES = ('requested', 'slicing', 'done', 'failed')
SHAPE_SOURCES = ('ImportedCadObject', 'MathShapeDefinition', 'MoldDefinition', 'FunctionalPartDefinition')


class SliceJob(treeObject):
    """What it is: one request to turn a shape into gcode: the shape row
    (a mathshapes `ImportedCadObject` / `MathShapeDefinition`, a casting
    `MoldDefinition`, a composition `FunctionalPartDefinition` — by class +
    name), the `PrintProfile`, the slicer part that takes it, and its state.
    The slicer writes the result as a `GcodeArtifact` naming this job.
    Related concepts: the shape rows above, `PrintProfile`, `GcodeArtifact`,
    the kirimoto part.
    How it is derived: created by the design/mold step; state moves by the
    slicer's report (never by hand).
    """

    @treeObjectInit
    def __init__(self, name: str = '', shape_class: str = 'ImportedCadObject', shape: str = '', profile: str = '',
                 slicer: str = 'kirimoto', orientation_json: str = '{}', supports: bool = False,
                 state: str = 'requested', requested_at: str = '', finished_at: str = '', error: str = '',
                 notes: str = ''):
        self.name = name
        self.shape_class = shape_class
        self.shape = shape
        self.profile = profile
        self.slicer = slicer
        self.orientation_json = orientation_json
        self.supports = supports
        self.state = state
        self.requested_at = requested_at
        self.finished_at = finished_at
        self.error = error
        self.notes = notes
