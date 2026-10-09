"""
@module cmod.objects.cmod.PeripheralClaim

PeripheralClaim — one class per file (design §7); ucd-0b (UNO_CORE_DEMO_PLAN.md §5f/§5g).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PeripheralClaim(treeObject):
    """What it is: ONE FIRMWARE SOLUTION'S HOLD ON ONE PERIPHERAL (OR ONE CHANNEL OF IT) — "uno-sim-rig holds TIMER0
    channel A exclusively (the PWM atoms); its prescaler (shared across both channels) is shared-config". Derived
    from the project's own atoms' register resources (`cmod.custom.claims.peripheral_claims`), grouped by the
    peripheral id a register's resource already carries (board.custom.hardware_chain's vocabulary: TIMER0/1/2,
    USART0, ADC, EXINT, PCINT, GPIO PORTx, SPI, TWI — never re-typed). `usage` says how exclusive the hold is:
    'exclusive' (one configuration only — a second, non-cooperating task reconfiguring it is a conflict), 'shared-
    config' (several tasks legitimately touch it, e.g. a timer's prescaler used by two channels), 'shared-read'
    (several tasks read it without configuring it, e.g. the ADC's result register across channels). Two DIFFERENT
    tasks holding the SAME exclusive peripheral/channel, neither an '_init' setup paired with its one user, is a
    conflict — never silently last-write-wins (the same cooperation posture as `cmod.custom.firmware`'s pin
    conflicts).
    Related concepts: `PinClaim`, board's `Peripheral`, `RegisterSetting`, `cmod.custom.firmware.assignments_for`.
    """

    plain_words = ('A peripheral claim is one firmware\'s hold on one peripheral or one channel of it, and whether '
                   'that hold is exclusive, shared for configuration, or shared for reading.')

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', peripheral: str = '', channel: str = '',
                 tasks_json: str = '[]', usage: str = 'exclusive', registers_json: str = '[]', rule: str = '',
                 status: str = 'ok', why: str = '', provenance: str = 'derived', binding: str = '',
                 notes: str = '', manager=None):
        self.name = name                 # '<solution>:<peripheral>[:<channel>]' ('uno-sim-rig:TIMER0:A') for the
                                          # default binding; '<binding>:<peripheral>[:<channel>]' otherwise (ucd-0b2b)
        self.solution = solution         # the FirmwareSolution row (the base solution — never the binding name)
        self.binding = binding           # ucd-0b2b: the HardwareBinding row this claim belongs to ('' pre-0b2b rows)
        self.peripheral = peripheral     # the Peripheral row name ('<soc>:TIMER0')
        self.channel = channel           # '' | 'A' | 'B' | '0' … (a channel of the peripheral, when it has one)
        self.tasks_json = tasks_json     # ["task", …] — every CGraphNode instance touching this peripheral/channel
        self.usage = usage               # exclusive | shared-config | shared-read
        self.registers_json = registers_json  # ["TCCR0A", …] — the register NAMES the atoms touch (plain, not refs)
        self.rule = rule                 # the derivation rule name (claims.py)
        self.status = status             # ok | conflict
        self.why = why
        self.provenance = provenance     # derived
        self.notes = notes
