"""
@module cmod.objects.cmod.PinClaim

PinClaim — one class per file (design §7); ucd-0b (UNO_CORE_DEMO_PLAN.md §5f/§5g).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PinClaim(treeObject):
    """What it is: ONE FIRMWARE SOLUTION'S DESIGN CHOICE FOR ONE PHYSICAL PIN — the first hop of his firmware-side
    chain (Firmware Task -> PinClaim -> SignalRoute -> PinFunction -> PeripheralSignal -> Peripheral -> RegisterField
    -> RegisterFieldSetting -> RegisterSetting -> the generated C). One row per pin a solution's `RegisterAssignment`
    rows bind (`cmod.custom.claims.pin_claims`), re-homing the representative task/port that CONFIGURES the pin
    (an '_init' atom when one exists, else the sole non-dispatcher user — never ambiguous, never guessed) alongside
    the DESIGN fields a novice actually chooses: `mode` (in | out | alt — the analogue of DDR direction, or 'the
    pin's alternate function is in control'), `pull` (none | up | undetermined), `edge` (none | any | rising |
    falling | low | undetermined — only meaningful when an interrupt is wanted on this pin), `initial` (low | high |
    none — the GPIO level at boot, 'none' when the pin's level comes from a peripheral, not GPIO logic). These are
    NOT scannable from the atom's C (UNO_CORE_DEMO_PLAN.md §5f point 1: the scan records register names/r-w access,
    not the VALUES written) — defaults come from `requirement_kind` + the board pin's own known alternate function;
    a person overrides them on the pin page (`provenance` becomes 'canvas'), persisted on the originating
    `RegisterAssignment.config_json` so a re-derive never loses it. `status` is 'incomplete' (never a refusal) when
    a needed field stays undetermined (e.g. an interrupt wanted with no edge chosen yet) and 'conflict' when the
    underlying RegisterAssignment itself conflicts.
    Related concepts: `RegisterAssignment`, `PeripheralClaim`, board's `PinFunction`, `SignalRoute`, `RegisterSetting`.
    """

    plain_words = ('A pin claim is one firmware\'s design choice for one physical pin — in, out or an alternate '
                   'function, with its pull-up, edge and startup level — and why.')

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', board: str = '', board_pin: str = '', soc_pin: str = '',
                 task: str = '', port: str = '', assignment: str = '', requirement_kind: str = 'undetermined',
                 mode: str = 'undetermined', pin_function: str = '', pull: str = 'none', edge: str = 'none',
                 initial: str = 'none', rule: str = '', provenance: str = 'derived', status: str = 'ok',
                 why: str = '', binding: str = '', notes: str = '', manager=None):
        self.name = name                        # '<solution>:<canonical>' ('uno-sim-rig:D6') for the default binding;
                                                  # '<binding>:<canonical>' for a non-default one (ucd-0b2b)
        self.solution = solution                # the FirmwareSolution row (the base solution — never the binding name)
        self.binding = binding                  # ucd-0b2b: the HardwareBinding row this claim belongs to ('' pre-0b2b rows)
        self.board = board                      # the BoardDefinition name
        self.board_pin = board_pin               # the BoardPin row name ('<board>:<canonical>')
        self.soc_pin = soc_pin                   # the SocPin row name ('<soc>:<pin>')
        self.task = task                         # the representative CGraphNode instance (the one that CONFIGURES this pin)
        self.port = port                         # '' for a whole-node representative
        self.assignment = assignment             # the representative RegisterAssignment row name
        self.requirement_kind = requirement_kind  # board.custom.target_compat.TASK_KINDS vocabulary (digital-out, pwm-out, …)
        self.mode = mode                         # in | out | alt | undetermined
        self.pin_function = pin_function         # the PinFunction row name when mode is alt ('' otherwise)
        self.pull = pull                         # none | up | undetermined
        self.edge = edge                         # none | any | rising | falling | low | undetermined
        self.initial = initial                   # low | high | none
        self.rule = rule                         # the derivation rule name (claims.py)
        self.provenance = provenance             # derived | canvas (an override was authored)
        self.status = status                     # ok | conflict | incomplete
        self.why = why
        self.notes = notes
