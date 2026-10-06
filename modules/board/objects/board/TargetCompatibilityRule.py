"""
@module board.objects.board.TargetCompatibilityRule

TargetCompatibilityRule — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TargetCompatibilityRule(treeObject):
    """What it is: fs-2a (his ruling 2026-10-06: "we need to know compatibility between targets and registers as
    well"): ONE ROW of THE COMPATIBILITY TABLE — a firmware task's TARGET KIND (analog-in, pwm-out, uart-rx,
    uart-tx, i2c-sda, i2c-scl, spi-mosi, spi-miso, spi-sck, spi-ss, digital-in, digital-out, interrupt-in, power,
    ground) against the PIN ROLES/capabilities that satisfy it (board.custom.pin_roles.ROLE_NAMES), cited to the
    ATmega328P datasheet section/table or the Arduino UNO pinout that names the alternate function (or Wikipedia for
    the general bus concept) — the SAME rows `board.custom.target_compat.compatible()` checks a specific pin
    against, never a second table. `board.custom.target_compat` is the one place this vocabulary is derived and
    read from; this class only carries it as rows a page can show (one row per kind → roles, with its source).
    `kind='power'`/`'ground'` rows carry `roles=''`: power/ground pins are never assignable to any task (his rule).
    Related concepts: `board.custom.pin_roles.ROLE_NAMES`, `BoardPin` (what a pin's own role is today), `SocPin`
    (the alternate-function capability a pin actually has), cmod's `RegisterAssignment`/`TargetDefinition`.
    """

    plain_words = ('A target compatibility rule says which pin roles can satisfy one kind of firmware task target '
                   '(an analog input, a PWM output, a UART pin, …) — and cites where that comes from.')

    @treeObjectInit
    def __init__(self, name: str = '', kind: str = '', title: str = '', roles: str = '', description: str = '',
                 matches: str = '', source_label: str = '', source_url: str = '', notes: str = '', manager=None):
        self.name = name              # '<kind>' (the vocabulary is global, not per-board)
        self.kind = kind              # analog-in | pwm-out | uart-rx | uart-tx | i2c-sda | i2c-scl | spi-mosi |
                                       # spi-miso | spi-sck | spi-ss | digital-in | digital-out | interrupt-in |
                                       # power | ground
        self.title = title            # a short plain-words name ("Analog input (ADC)")
        self.roles = roles            # comma-separated board.custom.pin_roles.ROLE_NAMES this kind draws on
        self.description = description  # what a task of this kind needs, in plain words
        self.matches = matches        # which pins qualify, in plain words (e.g. "A0-A5 — the ADC0..ADC5 alternate function")
        self.source_label = source_label
        self.source_url = source_url
        self.notes = notes            # caveats (e.g. PCINT-only pins are undetermined, not refused)
