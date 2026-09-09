"""
@module printing_suite.objects.printing.PrintOutcome

PrintOutcome — what came off the printer, measured.
"""
from objectTreeDecorators import treeObject, treeObjectInit

OUTCOME_VERDICTS = ('good', 'usable', 'failed', 'unmeasured')


class PrintOutcome(treeObject):
    """What it is: the measured result of one `PrintJob`: actual time and
    material used, dimensional deviation against the shape, defects, and a
    verdict — the row that feeds BACK into the material and mold rows
    (waxprint's `MoldLifecycleRecord`, casting's `CastingRunRecord`,
    materials_science properties) so the next profile is derived from
    evidence.
    Related concepts: `PrintJob`, `PrintProfile` (what to adjust), the
    feedback rows above.
    How it is measured: calipers/scale/inspection typed WITH the method;
    `unmeasured` until someone does.
    """

    @treeObjectInit
    def __init__(self, name: str = '', print_job: str = '', verdict: str = 'unmeasured', actual_seconds: int = 0,
                 actual_material_g: float = 0.0, deviation_mm_json: str = '{}', defects_json: str = '[]',
                 measured_by: str = '', method: str = '', feeds_back_to: str = '', measured_at: str = '', notes: str = ''):
        self.name = name
        self.print_job = print_job
        self.verdict = verdict
        self.actual_seconds = actual_seconds
        self.actual_material_g = actual_material_g
        self.deviation_mm_json = deviation_mm_json
        self.defects_json = defects_json
        self.measured_by = measured_by
        self.method = method
        self.feeds_back_to = feeds_back_to
        self.measured_at = measured_at
        self.notes = notes
