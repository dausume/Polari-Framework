"""
@module instruments.objects.instruments.WaveformCapture

WaveformCapture — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit

FORMATS = ('BYTE', 'WORD', 'ASCII')
SOURCES = ('real', 'emulated', 'replay')


class WaveformCapture(treeObject):
    """What it is: the CANONICAL capture record (OSCILLOSCOPE_PLAN.md §0, D-osc-3) — one channel of one acquisition as read
    from an instrument: the IEEE 488.2 block kept VERBATIM (its sha256, its bytes or the file-store path) plus the ten
    preamble parameters both command lineages map onto — points, x_increment (s/sample), x_origin, x_reference,
    y_increment (V/level), y_origin, y_reference — and the formulas' convention (`lineage`), so volts and times are
    recomputed on read and never stored as floats that could drift from the source:
        agilent lineage:   V = (raw - y_origin - y_reference) * y_increment ;  t = (i - x_reference) * x_increment + x_origin
        tektronix lineage: V = (raw - y_reference) * y_increment + y_origin ;  t = (i - x_reference) * x_increment + x_origin
    (Tektronix's YOFf → y_reference, YMUlt → y_increment, YZEro → y_origin, PT_Off → x_reference, XINcr → x_increment, XZEro → x_origin.)

    Related concepts: `InstrumentEndpoint` (where it was read), `ScopeChannel` (the settings at the time, copied into
    `settings_json`), `Instrument` (the model's limits), the GraphDefinition `instruments-capture` (the 4-series chart).

    How it is measured or derived: written only by `instruments.custom.client.capture` (real / emulated) or by a replay;
    `source_ref` names what produced an emulated capture (the twin session, the stimulus, the synth spec) so the capture is
    reproducible from stored inputs; `raw_sha256` is the sha256 of the block's bytes."""

    plain_words = ('One recorded trace from one oscilloscope channel, kept exactly as the instrument sent it along with the few '
                   'numbers needed to turn it back into volts over time.')

    @treeObjectInit
    def __init__(self, name: str = '', endpoint: str = '', instrument: str = '', channel: int = 1, acquired_at: str = '',
                 acquisition: str = '', points: int = 0, format: str = 'WORD', lineage: str = 'agilent',
                 x_increment: float = 0.0, x_origin: float = 0.0, x_reference: float = 0.0,
                 y_increment: float = 0.0, y_origin: float = 0.0, y_reference: float = 0.0,
                 sample_rate_sps: float = -1.0, memory_depth_pts: float = -1.0, trigger_json: str = '{}', settings_json: str = '{}',
                 raw_sha256: str = '', raw_bytes: int = 0, raw_path: str = '', raw_b64: str = '', preamble_text: str = '',
                 source: str = 'real', source_ref: str = '', note: str = '', manager=None):
        self.name = name                    # '<acquisition>-ch<n>'
        self.endpoint = endpoint
        self.instrument = instrument
        self.channel = channel
        self.acquired_at = acquired_at
        self.acquisition = acquisition      # one id shared by the channels read in the same acquisition
        self.points = points
        self.format = format                # FORMATS — WORD = 2 bytes little-endian per sample (12-bit models)
        self.lineage = lineage              # which formula set applies
        self.x_increment = x_increment
        self.x_origin = x_origin
        self.x_reference = x_reference
        self.y_increment = y_increment
        self.y_origin = y_origin
        self.y_reference = y_reference
        self.sample_rate_sps = sample_rate_sps
        self.memory_depth_pts = memory_depth_pts
        self.trigger_json = trigger_json
        self.settings_json = settings_json  # the ScopeChannel fields at capture time
        self.raw_sha256 = raw_sha256        # sha256 of the block payload bytes (header excluded)
        self.raw_bytes = raw_bytes
        self.raw_path = raw_path            # file-store path when the payload is not inline
        self.raw_b64 = raw_b64              # the payload inline (base64) when small enough for a dev instance
        self.preamble_text = preamble_text  # the preamble reply verbatim
        self.source = source                # SOURCES
        self.source_ref = source_ref        # what produced an emulated/replayed capture (reproducibility)
        self.note = note
