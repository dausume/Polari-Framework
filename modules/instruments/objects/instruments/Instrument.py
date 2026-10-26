"""
@module instruments.objects.instruments.Instrument

Instrument — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit

#: the SCPI command lineages a capture's preamble is read with (OSCILLOSCOPE_PLAN.md §0)
LINEAGES = ('agilent', 'tektronix', 'unverified')
#: instrument kinds this module knows how to read; others are rows with facts only
KINDS = ('oscilloscope', 'vendor-lineage')


class Instrument(treeObject):
    """What it is: ONE row per instrument MODEL the bench can carry (an oscilloscope first — the RIGOL DHO804 and its
    DHO800 siblings), or per VENDOR LINEAGE (Keysight, Tektronix) until a model of theirs has its datasheet read.
    The numbers are the WORKBENCH card: channels, bandwidth, sample rate and memory depth (both fall as more channels
    are enabled — the per-channel-count tables are kept as JSON, the single-channel maximum as the headline), vertical
    resolution, capture rate, input limits, sensitivity and timebase ranges, the LAN/USB transports, the command lineage
    its waveform preamble follows, the *IDN? form, and whether this module's EMULATOR can stand in for it.

    Related concepts: `InstrumentEndpoint` (a reachable unit of this model — address typed at runtime, never seeded),
    `ScopeChannel`, `WaveformCapture` (the canonical capture record), `board.objects.board.Bench` (`instruments_json`
    lists the models on a bench), the Mission Purposes that need "N channels at >= X MHz" (mis-1).

    How it is measured or derived: EVERY number is cited in `citation` (the datasheet page) or is -1 = unverified;
    strings that were not read are 'unverified' — never typed from memory (derive-or-cite). The command set and the
    preamble formula are cited to the BSD-3 scopehal driver, the LAN ports to a forum-compiled port list (said so in
    `transports_json`)."""

    plain_words = ('One card per oscilloscope model: how many channels it has, how fast it samples, how deep its memory is, '
                   'how it is reached over the network, and whether Polari can pretend to be one for testing.')

    @treeObjectInit
    def __init__(self, name: str = '', vendor: str = '', model: str = '', kind: str = 'oscilloscope', family: str = '',
                 channels: int = -1, ext_trigger: bool = False, bandwidth_hz: float = -1.0, rise_time_ns: float = -1.0,
                 sample_rate_sps: float = -1.0, sample_rate_by_channels_json: str = '{}',
                 memory_depth_pts: float = -1.0, memory_depth_by_channels_json: str = '{}',
                 resolution_bits: int = -1, capture_rate_wfms: float = -1.0, capture_rate_basis: str = '',
                 input_impedance_ohm: float = -1.0, input_capacitance_pf: float = -1.0, max_input_v_rms: float = -1.0,
                 sensitivity_min_v_div: float = -1.0, sensitivity_max_v_div: float = -1.0,
                 timebase_min_s_div: float = -1.0, timebase_max_s_div: float = -1.0, bw_limits: str = '',
                 trigger_types: str = '', transports_json: str = '[]', lineage: str = 'unverified', idn_format: str = '',
                 lxi: str = 'unverified', display: str = '', size_mm: str = '', price_usd: float = -1.0, price_basis: str = '',
                 citation: str = '', emulated: bool = False, emulator_profile: str = '', note: str = '', manager=None):
        self.name = name                        # kebab-case key, e.g. 'rigol-dho804'
        self.vendor = vendor
        self.model = model
        self.kind = kind                        # oscilloscope | vendor-lineage
        self.family = family                    # the series, e.g. 'DHO800'
        self.channels = channels                # analog channels (-1 unverified)
        self.ext_trigger = ext_trigger          # an EXT trigger input beside the channels
        self.bandwidth_hz = bandwidth_hz        # analog bandwidth, -3 dB
        self.rise_time_ns = rise_time_ns        # 10-90 %, typical
        self.sample_rate_sps = sample_rate_sps  # the single-channel maximum
        self.sample_rate_by_channels_json = sample_rate_by_channels_json    # {"1": sps, "2": sps, "4": sps}
        self.memory_depth_pts = memory_depth_pts                            # the single-channel maximum
        self.memory_depth_by_channels_json = memory_depth_by_channels_json  # {"1": pts, "2": pts, "4": pts}
        self.resolution_bits = resolution_bits
        self.capture_rate_wfms = capture_rate_wfms
        self.capture_rate_basis = capture_rate_basis    # the acquisition mode the rate is quoted in
        self.input_impedance_ohm = input_impedance_ohm
        self.input_capacitance_pf = input_capacitance_pf
        self.max_input_v_rms = max_input_v_rms
        self.sensitivity_min_v_div = sensitivity_min_v_div
        self.sensitivity_max_v_div = sensitivity_max_v_div
        self.timebase_min_s_div = timebase_min_s_div
        self.timebase_max_s_div = timebase_max_s_div
        self.bw_limits = bw_limits              # e.g. '20 MHz, FULL'
        self.trigger_types = trigger_types
        self.transports_json = transports_json  # [{"name": "scpi-raw", "port": 5555, "basis": "..."}]
        self.lineage = lineage                  # agilent | tektronix | unverified (LINEAGES)
        self.idn_format = idn_format            # the *IDN? shape, four comma fields
        self.lxi = lxi                          # the LXI class/version as stated, or 'unverified'
        self.display = display
        self.size_mm = size_mm
        self.price_usd = price_usd
        self.price_basis = price_basis          # where and when the price was seen
        self.citation = citation                # the documents the numbers come from (page numbers)
        self.emulated = emulated                # this module's emulator has a profile for it (osc-2)
        self.emulator_profile = emulator_profile
        self.note = note
