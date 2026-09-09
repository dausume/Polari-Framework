"""
@module printing_suite.objects.printing.PrintJob

PrintJob — one artifact sent to one printer.
"""
from objectTreeDecorators import treeObject, treeObjectInit

PRINT_STATES = ('queued', 'uploaded', 'printing', 'paused', 'complete', 'cancelled', 'error')


class PrintJob(treeObject):
    """What it is: one `GcodeArtifact` on one printer (`printer` = the voron
    `PrinterDefinition`), with the material lot loaded, its Moonraker job
    id once uploaded, and the state Moonraker reports.
    Related concepts: `GcodeArtifact`, `PrinterDefinition`/`PrinterState`
    (voron), `MaterialLot`, `PrintOutcome`.
    How it is measured: state and progress from Moonraker through the
    voron part's state push; never typed.
    """

    @treeObjectInit
    def __init__(self, name: str = '', artifact: str = '', printer: str = '', material_lot: str = '',
                 moonraker_job_id: str = '', state: str = 'queued', progress_pct: float = 0.0,
                 started_at: str = '', finished_at: str = '', error: str = '', notes: str = ''):
        self.name = name
        self.artifact = artifact
        self.printer = printer
        self.material_lot = material_lot
        self.moonraker_job_id = moonraker_job_id
        self.state = state
        self.progress_pct = progress_pct
        self.started_at = started_at
        self.finished_at = finished_at
        self.error = error
        self.notes = notes
