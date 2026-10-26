"""
@module instruments.objects.instruments.InstrumentEndpoint

InstrumentEndpoint — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit

#: how an endpoint is reached (OSCILLOSCOPE_PLAN.md §2): raw SCPI socket (stdlib), the PyVISA resource kinds, or the emulator
TRANSPORTS = ('scpi-raw', 'vxi-11', 'hislip', 'usbtmc', 'emulator')


class InstrumentEndpoint(treeObject):
    """What it is: ONE row per REACHABLE instrument — a unit of an `Instrument` model at an address. The address is typed at
    runtime (POST /api/instruments/endpoints) and lives only in the instance's rows: nothing here is seeded with a real
    address (privacy rule), the only seeded endpoint is the emulator's isle-local service name once osc-5 deploys it.

    Related concepts: `Instrument` (the model), `ScopeChannel` (its per-channel settings), `WaveformCapture` (what was read
    from it), `islemesh` EngineProviderBinding `scope` (the emulator worker).

    How it is measured or derived: `status` / `last_idn` / `checked_at` are written only by an actual `*IDN?` exchange
    through `instruments.custom.client` — 'unchecked' until then; a refused or timed-out exchange keeps the refusal words."""

    plain_words = 'A real (or emulated) instrument at an address, and whether it answered the last time we asked who it was.'

    @treeObjectInit
    def __init__(self, name: str = '', instrument: str = '', transport: str = 'scpi-raw', address: str = '', port: int = 0,
                 resource: str = '', status: str = 'unchecked', last_idn: str = '', checked_at: str = '', note: str = '',
                 manager=None):
        self.name = name                # kebab-case key
        self.instrument = instrument    # an Instrument row name (the model)
        self.transport = transport      # TRANSPORTS
        self.address = address          # host or IP as typed; '' for an emulator started in-process
        self.port = port                # 0 = the transport's default
        self.resource = resource        # the PyVISA resource string when that transport is used (derived from address/port)
        self.status = status            # unchecked | answered | refused | unreachable
        self.last_idn = last_idn        # the *IDN? reply verbatim (or the refusal words)
        self.checked_at = checked_at
        self.note = note
