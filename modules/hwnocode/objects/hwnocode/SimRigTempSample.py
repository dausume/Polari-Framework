"""
@module hwnocode.objects.hwnocode.SimRigTempSample

SimRigTempSample — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SimRigTempSample(treeObject):
    """What it is: one TELEMETRY SAMPLE the backend half of `uno-temp-split` keeps (HARDWARE_NOCODE_PLAN.md §4 h): the SimRigState
    row's `temp_c` at its `uptime_ms`, with the moving average the backend computed at that moment. Written by the AnalysisCall
    node `hwnocode-temp-derive` once per frame that reaches the row (10 Hz), in a RING of `keep` slots per source row (the
    oldest slot is overwritten — bounded storage, no deletes). The chart on /display/hardware-solutions reads these rows.
    Related concepts: `SimRigTempDerived` (the current derived value + the threshold boolean), grpcbridge `SimRigState`.
    """

    plain_words = 'A temperature sample is one reading from the board kept by the server, with the smoothed value computed when it arrived.'

    @treeObjectInit
    def __init__(self, name: str = '', source_object: str = '', seq: int = 0, slot: int = 0, uptime_ms: int = 0,
                 temp_c: float = 0.0, temp_avg: float = 0.0, window: int = 0, written_at: str = '', manager=None):
        self.name = name                    # <source_object>#<slot>
        self.source_object = source_object  # the SimRigState row (uno-twin)
        self.seq = seq                      # 0.. — the sample counter (slot = seq % keep)
        self.slot = slot
        self.uptime_ms = uptime_ms          # the firmware's clock in the frame
        self.temp_c = temp_c
        self.temp_avg = temp_avg            # the moving average over `window` samples ending here
        self.window = window
        self.written_at = written_at
