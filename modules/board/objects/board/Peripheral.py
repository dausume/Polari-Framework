"""
@module board.objects.board.Peripheral

Peripheral — one class per file (design §7); ucd-0a, THE HARDWARE CHAIN (UNO_CORE_DEMO_PLAN.md §5f/§5g).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Peripheral(treeObject):
    """What it is: ONE FUNCTIONAL BLOCK of a SoC — a timer, a USART, an I/O port, the ADC, the external-interrupt unit —
    the hop between a pin's alternate functions and the registers that configure them (his chain, 2026-10-07: Board → Pin
    → SoC Pin → PinFunction → PeripheralSignal → Peripheral → Register → RegisterField, navigable both ways). DERIVED, never
    typed in: the ids come from the register snapshot's grouping rules (board.custom.registers.PERIPHERAL_RULES, the
    datasheet's own register-summary naming) and from the alternate-function table (board.custom.soc_atmega328p
    .FUNCTION_PERIPHERAL); the chapter citation is the datasheet's TOC. `registers_refs_json` / `signals_refs_json` /
    `pin_functions_refs_json` are the REVERSE links (Class:name strings) so the generic object page walks back down the
    chain with no custom component. Materialized at boot (code-owned, converges); `origin` says from what.
    Related concepts: `PeripheralSignal`, `Register`, `PinFunction`, `SocDefinition` (its `peripherals_json` names these).
    """

    plain_words = ('A peripheral is one functional block inside the chip — a timer, a serial port, an I/O port, the '
                   'analog-to-digital converter, the external-interrupt unit. Its page lists the signals it can put on '
                   'pins and the registers that configure it.')

    @treeObjectInit
    def __init__(self, name: str = '', soc: str = '', peripheral: str = '', title: str = '', kind: str = '',
                 chapter: str = '', description: str = '', registers_refs_json: str = '[]', signals_refs_json: str = '[]',
                 pin_functions_refs_json: str = '[]', fact: str = '', origin: str = '', undetermined: str = '',
                 notes: str = '', manager=None):
        self.name = name                    # '<soc>:<peripheral>' (atmega328p:TIMER2)
        self.soc = soc                      # the SocDefinition row
        self.peripheral = peripheral        # the id: TIMER2 | USART0 | EXINT | PCINT | GPIO PORTD | ADC | AC | SPI | TWI | WDT | EEPROM | CPU | CLOCK | RESET
        self.title = title                  # the datasheet chapter title ("8-bit Timer/Counter2 with PWM and Asynchronous Operation")
        self.kind = kind                    # timer | usart | gpio-port | adc | exint | pcint | comparator | spi | twi | wdt | eeprom | cpu | clock | reset
        self.chapter = chapter              # the citation (chapter + page), '' when the snapshot alone names it
        self.description = description      # what it does, in plain words
        self.registers_refs_json = registers_refs_json        # ["Register:<soc>:<REG>", …] — reverse link
        self.signals_refs_json = signals_refs_json            # ["PeripheralSignal:<soc>:<peripheral>:<signal>", …]
        self.pin_functions_refs_json = pin_functions_refs_json  # ["PinFunction:<soc>:<pin>:<function>", …]
        self.fact = fact                    # the DatasheetFact row naming the chapter, when one exists
        self.origin = origin                # derived:<how> — the snapshot sha / the function table
        self.undetermined = undetermined    # what no source gave (e.g. no chapter cite for CPU-misc registers)
        self.notes = notes
