"""
@module printing_suite.objects.printing.ProductionRun

ProductionRun — one "make this part out of that material" request, walked step by step.
"""
from objectTreeDecorators import treeObject, treeObjectInit

RUN_STEPS = ('design', 'material', 'nesting', 'mold', 'slice', 'print', 'measure')
RUN_STATES = ('open', 'running', 'blocked', 'done', 'failed')


class ProductionRun(treeObject):
    """What it is: the automation Dustin asked for (2026-09-09): "you upload a
    CAD design to Polari, define what material you want the object to be
    made out of, and it runs the mold nesting automation generation. Then
    you get the outermost nested PLA or wax filament mold from the
    simulation process, and that mold is what gets passed to the slicer and
    then sent to the printer — cached at each step so we can print it again
    or retry steps." One row per request: the CAD object, the target
    material, the printable mold feedstock, the printer; `step` is where it
    stands; every step's result is a `RunStepRecord` (the cache).
    Related concepts: `ImportedCadObject` (mathshapes), casting's
    `plan_nesting` → `MoldNestingChain`/`CastingStageDefinition`/`MoldDefinition`,
    `PrintProfile`, `SliceJob`/`GcodeArtifact`/`PrintJob`/`PrintOutcome`,
    `PrinterDefinition` (voron), the kirimoto slicer.
    How it moves: `printing_suite.custom.pipeline.advance` runs the next
    step through adapters that call the real machinery and REFUSE by name
    when it is absent; `retry` re-runs one step (later steps are
    invalidated); nothing here is typed by hand except the request.
    """

    @treeObjectInit
    def __init__(self, name: str = '', cad_object: str = '', target_material: str = '', mold_feedstock: str = 'pla',
                 printer: str = 'voron-2.4-350', profile: str = '', slicer: str = 'kirimoto',
                 step: str = 'design', state: str = 'open', last_error: str = '', requested_by: str = '',
                 requested_at: str = '', updated_at: str = '', notes: str = ''):
        self.name = name
        self.cad_object = cad_object
        self.target_material = target_material
        self.mold_feedstock = mold_feedstock
        self.printer = printer
        self.profile = profile
        self.slicer = slicer
        self.step = step
        self.state = state
        self.last_error = last_error
        self.requested_by = requested_by
        self.requested_at = requested_at
        self.updated_at = updated_at
        self.notes = notes
