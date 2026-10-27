"""
@module instruments.objects.instruments.ScopeChannel

ScopeChannel — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit

COUPLINGS = ('DC', 'AC', 'GND')
#: osc-6: what the channel is READING - board.custom.signal_kinds (analog = volts; digital = levels by threshold_v; differential = this channel minus pair_channel)
SIGNAL_KINDS = ('analog', 'digital', 'differential')


class ScopeChannel(treeObject):
    """What it is: the SETTINGS of one analog channel of one `InstrumentEndpoint` — enabled, volts per division, offset,
    coupling, bandwidth limit, probe attenuation, and a label for what is clipped to it on the bench (a board pin, a net).

    Related concepts: `InstrumentEndpoint`, `WaveformCapture` (a capture records the settings it was taken with, so this
    row is the CURRENT intent and the capture is the history), `Instrument.sensitivity_*` (the legal range the door checks).

    How it is measured or derived: written by the person (the channel door) or read back from the instrument
    (`:CHAN<n>:SCALE?` etc. through the client) — `basis` says which; never both silently."""

    plain_words = 'One oscilloscope channel: how many volts each division is, where zero sits, and what it is probing.'

    @treeObjectInit
    def __init__(self, name: str = '', endpoint: str = '', channel: int = 1, enabled: bool = True, scale_v_div: float = 1.0,
                 offset_v: float = 0.0, coupling: str = 'DC', bw_limit: str = 'OFF', probe: float = 1.0, label: str = '',
                 probing: str = '', basis: str = 'typed', signal_kind: str = 'analog', threshold_v: float = -1.0, pair_channel: int = 0, manager=None):
        self.name = name            # '<endpoint>-ch<n>'
        self.endpoint = endpoint    # an InstrumentEndpoint name
        self.channel = channel      # 1..channels
        self.enabled = enabled
        self.scale_v_div = scale_v_div
        self.offset_v = offset_v
        self.coupling = coupling    # COUPLINGS
        self.bw_limit = bw_limit    # 'OFF' | '20M' (the model's bw_limits)
        self.probe = probe          # attenuation factor, 1 = 1X
        self.label = label
        self.probing = probing      # what the probe is on: 'uno-light:D6', a net name, ''
        self.basis = basis          # typed | read-back
        self.signal_kind = signal_kind      # SIGNAL_KINDS: how the capture is READ (osc-6) - the probe still sees volts
        self.threshold_v = threshold_v      # digital: the 0/1 threshold (-1 = not set; a 3.3 V or 5 V logic family's midpoint is the usual choice, typed)
        self.pair_channel = pair_channel    # differential: the channel subtracted (this - pair); 0 = none
