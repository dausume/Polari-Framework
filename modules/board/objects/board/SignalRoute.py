"""
@module board.objects.board.SignalRoute

SignalRoute — one class per file (design §7); ucd-0a defines it, ucd-0b populates it (UNO_CORE_DEMO_PLAN.md §5g B).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SignalRoute(treeObject):
    """What it is: THE ROUTE A FIRMWARE SOLUTION ACTIVATED — one `PinFunction` chosen for one pin by one `PinClaim`
    ("D3 carries INT1 in uno-button-clock"). `PinFunction` is what is available; this row is what is in use, per
    solution, and `configuration_refs_json` names the `RegisterFieldSetting` rows that make it active (for a fixed AVR
    route: the enable bit, e.g. EIMSK.INT1; for a GPIO-matrix SoC later: the matrix select registers). Kept as its own
    row even on fixed-routing chips so the chain has the SAME shape on the UNO, the ESP32-C3 and custom hardware (his
    ruling via ChatGPT round 4). DERIVED from the claims (ucd-0b: board.custom / cmod.custom.claims), never authored;
    `status` is active once the solution's generated config carries the enabling settings, planned before.
    Related concepts: `PinFunction`, cmod's `PinClaim`, `RegisterFieldSetting`, `FirmwareSolution`.
    """

    plain_words = ('A signal route says which of a pin\'s possible functions one firmware actually turned on, and '
                   'which register settings turned it on.')

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', pin_claim: str = '', board_pin: str = '', soc_pin: str = '',
                 pin_function: str = '', signal: str = '', peripheral: str = '', routing: str = 'fixed',
                 configuration_refs_json: str = '[]', status: str = 'planned', provenance: str = 'derived',
                 notes: str = '', manager=None):
        self.name = name                    # '<solution>:<canonical>:<function>' (uno-button-clock:D3:INT1)
        self.solution = solution            # the FirmwareSolution row
        self.pin_claim = pin_claim          # the PinClaim row (cmod) that selected this route
        self.board_pin = board_pin          # the BoardPin row name
        self.soc_pin = soc_pin              # the SocPin row name
        self.pin_function = pin_function    # the PinFunction row name — the chosen one
        self.signal = signal                # the PeripheralSignal row name
        self.peripheral = peripheral        # the Peripheral row name
        self.routing = routing              # copied from the PinFunction
        self.configuration_refs_json = configuration_refs_json  # ["RegisterFieldSetting:…", …] that activate it
        self.status = status                # planned | active | conflict
        self.provenance = provenance        # derived (from the claims) — never canvas
        self.notes = notes
