"""
@module cmod.objects.cmod.CatomVariable

CatomVariable - one class per file (design section 7). HARDWARE_SYSTEM_PINS_PLAN.md section 7 "Catom VARIABLES = the generalized HAL" (hsp-3d).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CatomVariable(treeObject):
    """What it is: a named HAL value a catom reads (UART0_TX_PIN, LED_PIN, BUTTON_PIN, F_CPU) that is AT THE SAME TIME AN ASSERTION (his words, 2026-10-28: "a
    Catom variable can be both a variable and an assertion ... Catom Variables are how we make a generalized HAL, that is defined by people doing data entry for
    data sheets to define boards and benches"): UART0_TX_PIN = PD1 asserts "this is the TX of UART0 at PD1" (a `defines-role` Catom assertion, derived).
    `role` is a HAL role word (uart.tx, uart.rx, gpio.out, gpio.in, int.ext, adc.in, pwm.out, clock.hz); `type` pin | number. The VALUE comes by scope:
    `chip_default` (datasheet data entry, `chip_basis` cites the page) -> `board_value` (the board definition) -> `bench_value` (what is wired where); the
    effective value is the narrowest one set. Before a value counts it is CHECKED (cmod.custom.catom_variables.check): the role must be a function the pin
    offers, the pin's lifecycle rows must allow it (a reservation by the same peripheral = a warning, by another = refused), no other variable may claim the
    pin for a different role. `status` accepted | warning | refused with `status_why` - recomputed on read, never trusted from the row. `c_form` says how the
    firmware spells the value (arduino-number 6 | port-bit PD1 | gpio-number 21 | number 16000000UL); `used_by` names the catoms that read it.
    Related concepts: CatomAssertion (kind defines-role), PinFunction + PinLifecycleConstraint (board), CAtom.bindings + cmod knob identifiers (generalized).
    """

    plain_words = ('A catom variable is a named setting the firmware reads - which pin the serial line uses, which pin the light is on - and saying its value '
                   'is also a claim the rules check: that pin must really be able to do that job.')

    @treeObjectInit
    def __init__(self, name: str = '', variant: str = '', variable: str = '', role: str = '', type: str = 'pin', soc: str = '', board: str = '',
                 c_form: str = '', chip_default: str = '', chip_basis: str = '', board_value: str = '', board_basis: str = '', bench_value: str = '',
                 bench_basis: str = '', used_by: str = '', status: str = '', status_why: str = '', notes: str = '', manager=None):
        self.name = name                # '<variant>:<VARIABLE>'
        self.variant = variant          # uno-light | light-c3
        self.variable = variable        # UART0_TX_PIN
        self.role = role                # uart.tx | uart.rx | gpio.out | gpio.in | int.ext | adc.in | pwm.out | clock.hz
        self.type = type                # pin | number
        self.soc = soc                  # atmega328p | esp32c3
        self.board = board              # arduino-uno-r3 | esp32-c3-devkitm-1
        self.c_form = c_form            # arduino-number | port-bit | gpio-number | number
        self.chip_default = chip_default
        self.chip_basis = chip_basis    # the datasheet page the default came from
        self.board_value = board_value
        self.board_basis = board_basis
        self.bench_value = bench_value
        self.bench_basis = bench_basis  # the variant knob / the bench part
        self.used_by = used_by          # comma separated catoms that read it
        self.status = status            # accepted | warning | refused (recomputed on read)
        self.status_why = status_why
        self.notes = notes
