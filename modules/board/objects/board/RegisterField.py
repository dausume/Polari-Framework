"""
@module board.objects.board.RegisterField

RegisterField — one class per file (design §7); ucd-0a, THE HARDWARE CHAIN.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RegisterField(treeObject):
    """What it is: ONE BIT FIELD OF A REGISTER — EICRA.ISC1 (bits 3:2), EIMSK.INT1 (bit 1), DDRD.DDD3 (bit 3) — with
    what each value MEANS and how the field may be ACCESSED. CITED, never derived from code: every row names the
    datasheet section, table and page its bit positions, meanings and access come from (board.custom
    .register_fields_atmega328p — read from DS40002061B on 2026-10-07, file sha matched). `access` is typed so a
    generator never treats every bit as an ordinary read-modify-write bit: `rw` plain; `r` read-only; `w1c` a flag
    cleared by WRITING A ONE to it (EIFR.INTF1 — a read-modify-write would clear every pending flag at once);
    `w-strobe` writes act, reads give zero (TCCR2B.FOC2A); `rw-toggle` writing one TOGGLES another register's bit
    (PIND.PIND3 toggles PORTD3, §14.2.2). `values_json` maps each value to its meaning in the datasheet's words
    ("01": "Any logical change on INT1 generates an interrupt request"). `affects_signal` names the PeripheralSignal the
    field configures when it is one signal's (ISC1 → INT1), so a signal's page reaches its control bits.
    Related concepts: `Register`, `PeripheralSignal`, `RegisterFieldSetting` (a solution's value for this field),
    `Datasheet` (ucd-doc: the document itself, as a first-class row — `datasheet` names it, resolved at seed time
    from `document`+`url` by board.custom.datasheets.rows()).
    """

    plain_words = ('A register field is a group of one or more bits inside a register that mean one thing — which edge '
                   'triggers an interrupt, whether a pin is an input or an output. Its page lists every value and what '
                   'it means, and whether the bits can be read, written, or only cleared by writing a one.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', register: str = '', field: str = '', bit_hi: int = 0, bit_lo: int = 0,
                 width: int = 1, access: str = 'rw', reset_value: str = '0', description: str = '', values_json: str = '{}',
                 affects_signal: str = '', affects_pin: str = '', document: str = '', page_table: str = '', url: str = '',
                 origin: str = 'cited', undetermined: str = '', notes: str = '', datasheet: str = '', manager=None):
        self.name = name                    # '<soc>:<REGISTER>.<FIELD>' (atmega328p:EICRA.ISC1)
        self.soc = soc
        self.register = register            # the Register row name ('<soc>:EICRA')
        self.field = field                  # ISC1 | INT1 | DDD3 | CS2 …
        self.bit_hi = bit_hi                # the field's highest bit (3 for ISC1 = bits 3:2)
        self.bit_lo = bit_lo                # its lowest bit (2)
        self.width = width                  # bit_hi - bit_lo + 1
        self.access = access                # rw | r | w1c | w-strobe | rw-toggle
        self.reset_value = reset_value      # the datasheet's Initial Value for these bits ('0'; 'N/A' for PINx)
        self.description = description      # the datasheet's bit title ("Interrupt Sense Control 1 Bit 1 and Bit 0")
        self.values_json = values_json      # {"00": "…", "01": "…"} — the datasheet's own words per value
        self.affects_signal = affects_signal  # the PeripheralSignal row this field configures, when it is one signal's
        self.affects_pin = affects_pin      # the SocPin row this field configures, when it is one pin's (DDD3 → PD3)
        self.document = document
        self.page_table = page_table        # "§13.2.1 EICRA, Table 13-1, p.80"
        self.url = url
        self.origin = origin                # cited
        self.undetermined = undetermined
        self.notes = notes
        self.datasheet = datasheet          # ucd-doc: the Datasheet row this (document, url) resolves to
