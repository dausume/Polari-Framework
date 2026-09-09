"""
@module printing_suite.objects.printing.RunStepRecord

RunStepRecord — one cached step result of a ProductionRun.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RunStepRecord(treeObject):
    """What it is: the cache: what one step of one run produced — the row it
    created or found (`result_class` + `result_ref`), the artifact bytes it
    cached (`store_key` + sha256 + size: the STL of the mold, the gcode),
    whether it succeeded, the refusal when it did not, and the attempt
    number. Retrying a step writes a new attempt and invalidates the
    records of later steps; reprinting reuses the cached gcode.
    Related concepts: `ProductionRun`, the contract rows.
    How it is measured: written by the pipeline only; sha256 over the cached bytes.
    """

    @treeObjectInit
    def __init__(self, name: str = '', run: str = '', step: str = '', attempt: int = 1, ok: bool = False,
                 result_class: str = '', result_ref: str = '', store_key: str = '', sha256: str = '', bytes: int = 0,
                 error: str = '', detail_json: str = '{}', started_at: str = '', finished_at: str = '',
                 valid: bool = True):
        self.name = name
        self.run = run
        self.step = step
        self.attempt = attempt
        self.ok = ok
        self.result_class = result_class
        self.result_ref = result_ref
        self.store_key = store_key
        self.sha256 = sha256
        self.bytes = bytes
        self.error = error
        self.detail_json = detail_json
        self.started_at = started_at
        self.finished_at = finished_at
        self.valid = valid
