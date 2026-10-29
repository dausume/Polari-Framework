"""
@module cmod.objects.cmod.CatomAssertion

CatomAssertion - one class per file (design section 7). HARDWARE_SYSTEM_PINS_PLAN.md section 7 (hsp-3a; D-hsp-7 ruled 2026-10-28).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CatomAssertion(treeObject):
    """What it is: a claim a C atom makes about what its code DOES to a struct or a bridge (his word, 2026-10-28: "we assert a piece of code changes a struct
    or parts of a struct, or that it sends data to or from bridges"). `kind` is changes-struct (the whole struct) | changes-field (the named `fields`) |
    reads-field (the atom reads the named fields and drives `pins` from them: the struct controls the hardware) | sends-to-bridge | receives-from-bridge |
    defines-role (hsp-3d: a CatomVariable's value - UART0_TX_PIN = PD1 asserts uart.tx at PD1; derived from the variable, never hand-written).
    `pins` are the pins the atom touches to do it, `lane` where it runs (isr | loop | task | userspace - the Task Plan's lane words + userspace, D-hsp-5),
    `event` what sets it off (edge-rise | edge-fall | level | poll | uart-rx | uart-tx | ui | boot), `updater` HW (the chip) | US (userspace) - the struct's
    lastUpdater - and `stamps` the timestamp it writes (timestampHW | timestampUS | both | none). `object_map` names the StructObjectMap whose field -> attribute pairs
    the assertion rides (D-hsp-8: definitions only, no bench copies). `status` is DECLARED as unverified and SET by a twin run's record: verified (the record
    shows it) | unverified (not observable in the record, or not exercised) | false (the record contradicts it), `status_why` says which.
    Pin <-> field bindings are DERIVED from these rows (cmod.custom.catom_assertions.struct_pin_bindings); a field nobody asserts is a GAP, named.
    Related concepts: CFunctionAtom (the atom), TaskStructBinding (shared data a task touches), StructObjectMap, PolariBridgeInstance (grpcbridge).
    """

    plain_words = ('A catom assertion says what a piece of firmware does to the data: which fields of a struct it changes or reads, which pins it uses '
                   'to do it, or that it sends the struct over a bridge - and a twin run checks the claim.')

    @treeObjectInit
    def __init__(self, name: str = '', variant: str = '', atom: str = '', kind: str = '', struct: str = '', fields: str = '', bridge: str = '', pins: str = '',
                 lane: str = '', event: str = '', updater: str = '', stamps: str = 'none', object_map: str = '', status: str = 'unverified', status_why: str = '',
                 basis: str = '', notes: str = '', manager=None):
        self.name = name              # '<variant>:<atom>:<kind>'
        self.variant = variant        # the firmware variant whose atoms these are (uno-light)
        self.atom = atom              # the cycle-record / atom key: 'apps/light.led_toggle', 'hal.USART_RX_vect'
        self.kind = kind              # changes-struct | changes-field | reads-field | sends-to-bridge | receives-from-bridge
        self.struct = struct          # the C struct type: LightState_t
        self.fields = fields          # comma separated field names (empty = the whole struct)
        self.bridge = bridge          # a PolariBridgeInstance name (sends-to / receives-from)
        self.pins = pins              # comma separated pin names the atom touches: PD2, PD6, PD0, PD1
        self.lane = lane              # isr | loop | task | userspace | init
        self.event = event            # edge-rise | edge-fall | level | poll | uart-rx | uart-tx | ui | boot
        self.updater = updater        # HW | US | '' (the struct's lastUpdater value this atom writes)
        self.stamps = stamps          # timestampHW | timestampUS | both | none
        self.object_map = object_map  # a StructObjectMap name
        self.status = status          # verified | unverified | false (set by the record, declared unverified)
        self.status_why = status_why
        self.basis = basis            # where the claim was read: the atom's own source / POLARI_NODE role text
        self.notes = notes
