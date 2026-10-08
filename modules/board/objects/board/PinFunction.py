"""
@module board.objects.board.PinFunction

PinFunction — one class per file (design §7); ucd-0a, THE HARDWARE CHAIN.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PinFunction(treeObject):
    """What it is: ONE THING ONE SoC PIN CAN DO — PD3 can be plain GPIO, INT1, OC2B or PCINT19; each is a row. The pin's
    side of the pin ↔ peripheral link (what is AVAILABLE; `SignalRoute` is what a firmware solution ACTIVATED). DERIVED one
    row per entry of `SocPin.functions_json` (the datasheet's port tables, cited by the SocPin's own fact) plus one GPIO
    row per I/O pin (every port pin is general digital I/O, datasheet §14.2). `routing` says how the signal reaches the
    pin: `fixed` on the AVR (each alternate function has ONE pin); `mux` / `matrix` are reserved for SoCs that choose
    (the ESP32-C3's GPIO matrix, Phase 2). `overrides_gpio` is the datasheet's §14.3 rule: an enabled alternate function
    overrides the port's DDR/PORT control of that pin. `exclusive_group` is left '' (undetermined) until a cited rule
    says which functions of one pin cannot be active together — never guessed.
    Related concepts: `SocPin`, `PeripheralSignal`, `Peripheral`, `SignalRoute`, board.custom.target_compat (the
    compatibility if-chain that this table will replace).
    """

    plain_words = ('A pin function is one thing a chip pin is able to do — be a plain input/output, an interrupt input, '
                   'a timer output, a serial line. One pin usually has several; a firmware picks one at a time.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', soc_pin: str = '', function: str = '', signal: str = '',
                 peripheral: str = '', routing: str = 'fixed', overrides_gpio: bool = False, exclusive_group: str = '',
                 description: str = '', board_pins_refs_json: str = '[]', fact: str = '', origin: str = '',
                 undetermined: str = '', notes: str = '', manager=None):
        self.name = name                    # '<soc>:<pin>:<function>' (atmega328p:PD3:INT1)
        self.soc = soc
        self.soc_pin = soc_pin              # the SocPin row name ('<soc>:<pin>')
        self.function = function            # GPIO | INT1 | OC2B | PCINT19 | …
        self.signal = signal                # the PeripheralSignal row name ('<soc>:<peripheral>:<signal>')
        self.peripheral = peripheral        # the Peripheral row name
        self.routing = routing              # fixed | mux | matrix
        self.overrides_gpio = overrides_gpio  # §14.3: when enabled, the alternate function overrides DDR/PORT for the pin
        self.exclusive_group = exclusive_group  # '' = undetermined; a cited group id when functions of one pin exclude each other
        self.description = description
        self.board_pins_refs_json = board_pins_refs_json  # ["BoardPin:<board>:<canonical>", …] — which board pins expose this SoC pin
        self.fact = fact                    # the SocPin's DatasheetFact (port table + page)
        self.origin = origin
        self.undetermined = undetermined
        self.notes = notes
