"""
@module board.objects.board.RegisterFieldSetting

RegisterFieldSetting — one class per file (design §7); ucd-0a defines it, ucd-0b populates it (UNO_CORE_DEMO_PLAN.md §5g A).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RegisterFieldSetting(treeObject):
    """What it is: WHY ONE FIELD OF ONE REGISTER HAS ITS VALUE IN ONE SOLUTION — "EICRA.ISC1 = 01 (any logical change)
    because PinClaim D3/sense.isr asked for edge=any". One row per field a `RegisterSetting` sets: the field (cited
    `RegisterField`), the value and its meaning in the datasheet's words, the `PinClaim` (or `PeripheralClaim`) that
    required it, the firmware task behind that claim, and the derivation `rule` that turned the claim into bits. This is
    the last hop of his firmware-side chain (Firmware Task → PinClaim → SignalRoute → PinFunction → PeripheralSignal →
    Peripheral → RegisterField → RegisterFieldSetting → RegisterSetting → the generated C). DERIVED in ucd-0b; never
    authored.
    Related concepts: `RegisterSetting`, `RegisterField`, cmod's `PinClaim`, `PeripheralClaim`, `SignalRoute`.
    """

    plain_words = ('A register field setting says what value one bit field was given in one firmware, what that value '
                   'means, and which pin assignment or task asked for it.')

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', register_setting: str = '', register_field: str = '',
                 value: str = '', meaning: str = '', pin_claim: str = '', peripheral_claim: str = '', task: str = '',
                 rule: str = '', status: str = 'planned', provenance: str = 'derived', notes: str = '', manager=None):
        self.name = name                    # '<solution>:<REGISTER>.<FIELD>:<phase>' (uno-button-clock:EICRA.ISC1:init)
        self.solution = solution
        self.register_setting = register_setting  # the RegisterSetting row name
        self.register_field = register_field      # the RegisterField row name ('<soc>:EICRA.ISC1')
        self.value = value                  # '01'
        self.meaning = meaning              # the datasheet's words for that value
        self.pin_claim = pin_claim          # the PinClaim row (cmod) when a pin claim required it
        self.peripheral_claim = peripheral_claim  # the PeripheralClaim row when a peripheral claim required it
        self.task = task                    # the firmware task (CGraphNode instance) behind the claim
        self.rule = rule                    # the derivation rule name (claims.py), e.g. edge-any-to-ISC
        self.status = status                # planned | generated | conflict
        self.provenance = provenance        # derived
        self.notes = notes
