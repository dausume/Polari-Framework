"""
@module board.objects.board.BoardPin

BoardPin — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardPin(treeObject):
    """What it is: THE PIN ASSIGNMENT (§2b — the one overlap of KiCad, Zephyr, ESP-IDF, bare C and Polari): one board pin, named
    ONCE (`canonical`: the connector label when there is one — D6, A0 — else the SoC pin — GPIO21), wired to a SoC pin, a net
    and a connector pin, with the function / peripheral / signal it serves, the C identifier the C views emit
    (`firmware_symbol`) and the electrical facts. Every view renders from these rows and every ingest compares against them;
    a disagreement is a `BoardConflict`, never an edit.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', canonical: str = '', number: int = -1, soc_pin: str = '',
                 net: str = '', connector_pin: str = '', function: str = 'gpio', peripheral: str = '',
                 signal: str = '', firmware_symbol: str = '', alias: str = '', electrical_json: str = '{}',
                 facts_json: str = '[]', origin: str = '', undetermined: str = '', notes: str = '', links_refs_json: str = '[]',
                 manager=None):
        self.name = name  # '<board>:<canonical>'
        self.board = board
        self.canonical = canonical  # THE name every view uses
        self.number = number  # the number the C side uses (Arduino pin n, A-channel n, GPIO n)
        self.soc_pin = soc_pin  # a SocPin pin (PD6)
        self.net = net  # a BoardNet net
        self.connector_pin = connector_pin  # '<connector>:<n>' or ''
        self.function = function  # gpio | pwm | adc | uart | spi | i2c | usb | button | led | …
        self.peripheral = peripheral  # TIMER0 | USART0 | UART1 | ADC …
        self.signal = signal  # OC0A | TX | RX | ADC0 | SDA …
        self.firmware_symbol = firmware_symbol  # the C #define a C view emits (PWM_PIN)
        self.alias = alias  # a Zephyr alias / node label (sw0)
        self.electrical_json = electrical_json  # {bias, drive, output, active, max_ma, …}
        self.facts_json = facts_json  # DatasheetFact names
        self.origin = origin  # cited:<doc> | ingested:<file>@<tag> | polari:<why>
        self.undetermined = undetermined  # what the parse / the sources did not give
        self.notes = notes
        # ucd-0a: the chain's first hop from this pin — ["SocPin:<soc>:<pin>", "PinFunction:…", …] — derived (board.custom.
        # hardware_chain.link), read by the generic object page: Board → Pin → SoC Pin → PinFunction → … both ways
        self.links_refs_json = links_refs_json
