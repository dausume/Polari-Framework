"""
@module board.objects.board.PeripheralSignal

PeripheralSignal — one class per file (design §7); ucd-0a, THE HARDWARE CHAIN.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PeripheralSignal(treeObject):
    """What it is: ONE SIGNAL A PERIPHERAL CAN PUT ON (or take from) A PIN — OC2B is Timer2's compare-output B, INT1 is
    the external-interrupt unit's second input, RXD is USART0's receive line. The peripheral's side of the pin ↔ peripheral
    link: a `PinFunction` row says WHICH SoC pin can carry this signal; this row says what the signal IS and which
    peripheral owns it. DERIVED from the alternate-function table (board.custom.soc_atmega328p.FUNCTION_PERIPHERAL,
    every function name in the datasheet's port tables) — never typed in. `direction` is derived from the signal's
    role where the datasheet is unambiguous (an Output Compare pin is out, an interrupt/clock input is in, a bus data
    line is inout) and left 'undetermined' otherwise. `pin_functions_refs_json` is the reverse link.
    Related concepts: `Peripheral`, `PinFunction`, `SocPin`, cmod's `RegisterAssignment` (a task's target lands on a pin
    carrying one of these).
    """

    plain_words = ('A peripheral signal is one line a chip block can drive or read through a pin — a timer\'s PWM '
                   'output, a serial receive line, an interrupt input. Its page says which pins can carry it.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', peripheral: str = '', signal: str = '', channel: str = '',
                 direction: str = '', description: str = '', pin_functions_refs_json: str = '[]', fact: str = '',
                 origin: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name                    # '<soc>:<peripheral>:<signal>' (atmega328p:TIMER2:OC2B)
        self.soc = soc
        self.peripheral = peripheral        # the Peripheral row name ('<soc>:<peripheral>')
        self.signal = signal                # OC2B | INT1 | RXD | ADC0 | PCINT19 | GPIO …
        self.channel = channel              # A | B | 0..7 | '' — the channel within the peripheral when the name carries one
        self.direction = direction          # in | out | inout | undetermined
        self.description = description      # plain words
        self.pin_functions_refs_json = pin_functions_refs_json  # ["PinFunction:<soc>:<pin>:<function>", …] — reverse link
        self.fact = fact                    # the DatasheetFact (the port table the function name came from)
        self.origin = origin
        self.undetermined = undetermined
        self.notes = notes
