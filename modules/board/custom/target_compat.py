"""
@module board.custom.target_compat

fs-2a (his ruling 2026-10-06, verbatim essentials): "we need to know compatibility between targets and registers as
well … a clear indicator of when we click on a target what ones are valid targets. The pins are the targets."
Confirmed: an invalid drop is REFUSED; THIS TABLE (the compatibility between a firmware task's TARGET KIND and a
board's PIN ROLES/capabilities) lives in the BOARD module — a property of the board, not of cmod's graphs.

TASK_KINDS is derived from what the atoms of the UNO's own firmware already declare today (cmod.custom.targets /
cmod.custom.firmware's resource scan): analog-in (an ADC channel), pwm-out (a timer Output Compare pin), uart-rx /
uart-tx (USART0's two signals), i2c-sda / i2c-scl, spi-mosi / spi-miso / spi-sck / spi-ss, digital-in / digital-out
(a plain GPIO pin, either direction), interrupt-in (INT0/INT1 or a PCINTn pin-change pin), and power / ground —
never assignable to any task (his rule).

Every verdict `compatible()` returns cites its source: the pin's own SoC alternate-function fact (the SocPin row's
`fact` — a DatasheetFact name already seeded by board.custom.soc_atmega328p, e.g. 'atmega328p:pin.PD6') when the
check is per-pin, and board.custom.pin_roles.ROLES[*]['sources'] (the same UNO-docs/datasheet/Wikipedia citations
the pin-roles table already uses) for the general kind -> roles vocabulary rows() describes — never a new,
uncited claim. A fact this session did not re-verify (External/Pin-Change interrupts' exact chapter/page) is
marked so in ROLE_FOR_KIND's notes rather than guessed (derive-or-cite).
"""
import json

from board.custom import pin_roles as PR
from board.custom.soc_atmega328p import FUNCTION_PERIPHERAL, PWM_FUNCTIONS

#: the task target kind vocabulary (his ruling 2026-10-06) — never assignable kinds last. ucd-0b2d (§5h, the
#: HardwareBinding fix): 'timer' | 'usart' | 'adc' | 'spi' | 'twi' | 'exint' | 'pcint' | 'gpio-port' are
#: PERIPHERAL-level kinds (a TargetDefinition row with resource_kind='peripheral' — the whole block, never one
#: pin) — a task that configures a peripheral with no pin/signal touch at all (hal_tick_init: Timer2's CTC mode,
#: no Output Compare pin driven) names ONE of these, never a pin-flavoured kind like pwm-out just because the
#: register family happens to overlap one.
TASK_KINDS = ('analog-in', 'pwm-out', 'uart-rx', 'uart-tx', 'i2c-sda', 'i2c-scl', 'spi-mosi', 'spi-miso', 'spi-sck',
              'spi-ss', 'digital-in', 'digital-out', 'interrupt-in', 'timer', 'usart', 'adc', 'spi', 'twi', 'exint',
              'pcint', 'gpio-port', 'power', 'ground')
NEVER_ASSIGNABLE = ('power', 'ground')
#: the INTERRUPT chapters were NOT re-fetched/re-paginated this session (unlike ADC/PWM/USART/TWI/SPI, whose pages
#: soc_atmega328p.py cites from the 2026-10-01 read) — cited by document + revision only, the gap named honestly
INT_DOC_NOTE = 'External Interrupts (INT0/INT1) and Pin Change Interrupt (PCINT0..23) chapters — exact page not reconfirmed this session; see each pin\'s own SocPin fact for its specific alternate function citation'


def _wiki(label, url):
    return {'label': label, 'url': url}


#: kind -> (title, pin_roles.ROLE_NAMES this draws on, extra sources beyond that role's own, plain-words description)
_KIND_META = {
    'analog-in': ('Analog input (ADC)', ('adc',), (), 'reads a continuously-varying voltage on one of the SoC\'s ADC channels'),
    'pwm-out': ('PWM output', ('pwm',), (), 'drives a timer\'s Output Compare pin to fake an analog output'),
    'uart-rx': ('UART receive', ('uart',), (), 'receives a byte stream on USART0\'s RXD signal'),
    'uart-tx': ('UART transmit', ('uart',), (), 'sends a byte stream on USART0\'s TXD signal'),
    'i2c-sda': ('I2C data (SDA)', ('i2c',), (), 'the 2-wire TWI bus\'s data line'),
    'i2c-scl': ('I2C clock (SCL)', ('i2c',), (), 'the 2-wire TWI bus\'s clock line'),
    'spi-mosi': ('SPI MOSI/COPI', ('spi',), (), 'the controller-out-peripheral-in line of the SPI bus'),
    'spi-miso': ('SPI MISO/CIPO', ('spi',), (), 'the controller-in-peripheral-out line of the SPI bus'),
    'spi-sck': ('SPI clock (SCK)', ('spi',), (), 'the SPI bus\'s clock line'),
    'spi-ss': ('SPI slave-select (SS)', ('spi',), (), 'the SPI bus\'s per-device select line'),
    'digital-in': ('Digital input', ('gpio',), (), 'reads a plain 0/1 logic level'),
    'digital-out': ('Digital output', ('gpio',), (), 'drives a plain 0/1 logic level'),
    'interrupt-in': ('Interrupt input', ('gpio',), (_wiki('Wikipedia — Interrupt', 'https://en.wikipedia.org/wiki/Interrupt'),),
                     'wakes firmware on an edge — a dedicated external interrupt (INT0/INT1) or a pin-change interrupt (PCINTn)'),
    'power': ('Power', ('power',), (), 'a supply pin — never a firmware task\'s target'),
    'ground': ('Ground', ('ground',), (), 'the 0 V reference — never a firmware task\'s target'),
    # ucd-0b2d: peripheral-level kinds — the WHOLE functional block, never one pin (resource_kind='peripheral')
    'timer': ('Timer/Counter peripheral', ('pwm',), (), 'the whole timer block (clock source, counting mode) — '
              'not a specific Output Compare pin (e.g. Timer2 run as a plain 1 ms tick, driving no pin at all)'),
    'usart': ('USART peripheral', ('uart',), (), 'the whole serial port block (baud rate, frame format) — not '
              'either of its RXD/TXD signal lines'),
    'adc': ('ADC peripheral', ('adc',), (), 'the whole analog-to-digital converter block (reference, prescaler) — '
            'not one channel pin'),
    'spi': ('SPI peripheral', ('spi',), (), 'the whole SPI bus block (clock rate, mode) — not one of its signal lines'),
    'twi': ('TWI (I2C) peripheral', ('i2c',), (), 'the whole 2-wire bus block (bit rate, address) — not one of its signal lines'),
    'exint': ('External interrupt unit', (), (_wiki('Wikipedia — Interrupt', 'https://en.wikipedia.org/wiki/Interrupt'),),
              'the external-interrupt unit as a whole (EICRA/EIMSK) — not one INT0/INT1 pin'),
    'pcint': ('Pin-change interrupt unit', (), (_wiki('Wikipedia — Interrupt', 'https://en.wikipedia.org/wiki/Interrupt'),),
              'the pin-change-interrupt unit as a whole (PCICR/PCMSKn bank enables) — not one pin'),
    'gpio-port': ('GPIO port peripheral', ('gpio',), (), 'a whole I/O port block (e.g. all of PORTB\'s direction/pull '
                  'bits) — not one pin of it'),
}


def sources_for(kind):
    """The cited sources for one kind: its pin_roles.ROLES role(s) (reused, never duplicated) + any extra."""
    _, roles, extra, _ = _KIND_META[kind]
    out = []
    for role in roles:
        out += PR.ROLES[role]['sources']
    return out + list(extra)


def rows():
    """[TargetCompatibilityRule dict, ...] — one row per TASK_KINDS entry, described + cited (brd-bo his ruling:
    "a clear indicator of when we click on a target what ones are valid targets"; the table itself, shown on
    /display/boards)."""
    out = []
    for kind in TASK_KINDS:
        title, roles, _extra, desc = _KIND_META[kind]
        srcs = sources_for(kind)
        matches = {
            'analog-in': 'pins with an ADCn alternate function (the UNO: A0-A5)',
            'pwm-out': 'pins with a timer Output Compare alternate function (the UNO: D3, D5, D6, D9, D10, D11)',
            'uart-rx': 'the pin with USART0\'s RXD alternate function (the UNO: D0)',
            'uart-tx': 'the pin with USART0\'s TXD alternate function (the UNO: D1)',
            'i2c-sda': 'the pin with the TWI SDA alternate function (the UNO: A4)',
            'i2c-scl': 'the pin with the TWI SCL alternate function (the UNO: A5)',
            'spi-mosi': 'the pin with the SPI MOSI alternate function (the UNO: D11 / ICSP COPI)',
            'spi-miso': 'the pin with the SPI MISO alternate function (the UNO: D12 / ICSP CIPO)',
            'spi-sck': 'the pin with the SPI SCK alternate function (the UNO: D13 / ICSP SCK)',
            'spi-ss': 'the pin with the SPI SS alternate function (the UNO: D10)',
            'digital-in': 'any non-power/ground I/O pin (every SoC pin can be a plain GPIO input)',
            'digital-out': 'any non-power/ground I/O pin (every SoC pin can be a plain GPIO output)',
            'interrupt-in': 'INT0/INT1 pins are valid; a PCINTn-only pin is undetermined (its PCICR/PCMSKn bank is not modeled yet)',
            'timer': 'not a pin at all — met by a PeripheralClaim on the whole Timer/Counter block',
            'usart': 'not a pin at all — met by a PeripheralClaim on the whole USART0 block',
            'adc': 'not a pin at all — met by a PeripheralClaim on the whole ADC block',
            'spi': 'not a pin at all — met by a PeripheralClaim on the whole SPI block',
            'twi': 'not a pin at all — met by a PeripheralClaim on the whole TWI block',
            'exint': 'not a pin at all — met by a PeripheralClaim on the external-interrupt unit',
            'pcint': 'not a pin at all — met by a PeripheralClaim on the pin-change-interrupt unit',
            'gpio-port': 'not a pin at all — met by a PeripheralClaim on the whole GPIO port block',
            'power': '(never — power/ground pins are not assignable to any task)',
            'ground': '(never — power/ground pins are not assignable to any task)',
        }[kind]
        out.append({'name': kind, 'kind': kind, 'title': title, 'roles': ', '.join(roles), 'description': desc,
                    'matches': matches, 'source_label': srcs[0]['label'] if srcs else '', 'source_url': srcs[0]['url'] if srcs else '',
                    'notes': INT_DOC_NOTE if kind == 'interrupt-in' else ''})
    return out


def _functions(soc_pin):
    return json.loads(soc_pin['functions_json']) if soc_pin else []


def _fact_cite(soc_pin, pin):
    f = (soc_pin or {}).get('fact') or ''
    return 'datasheet fact %s' % f if f else 'no SoC register fact for pin %s' % pin.get('canonical', '?')


def compatible(kind, pin, soc_pin=None):
    """(verdict, reason) — verdict in 'ok' | 'no' | 'undetermined'. `pin` is a BoardPin dict (board.custom.
    board_object rows); `soc_pin` is its SocPin dict (board.custom.board_object rows_for(...)['soc_pins'], matched
    by pin['soc_pin']) — the FULL alternate-function capability (not just the pin's CURRENTLY assigned role), so a
    pin already wired to something else (e.g. D13 = LED_BUILTIN today) is still correctly judged by what the SoC
    pin CAN do. Power/ground pins (board_uno.POWER_NETS / pin.function) are refused for every kind, no exception."""
    canonical = pin.get('canonical', '?')
    if pin.get('function') in NEVER_ASSIGNABLE or kind in NEVER_ASSIGNABLE:
        which = pin.get('function') if pin.get('function') in NEVER_ASSIGNABLE else kind
        return 'no', '%s is a %s pin — power/ground pins are never assignable to a firmware task (his ruling 2026-10-06)' % (canonical, which)
    if kind not in TASK_KINDS:
        return 'undetermined', 'unknown task target kind %r (not in board.custom.target_compat.TASK_KINDS)' % kind
    fns = _functions(soc_pin)
    cite = _fact_cite(soc_pin, pin)
    if not fns:
        return 'undetermined', '%s has no SoC alternate-function facts to check (%s)' % (canonical, cite)

    def ok(why):
        return 'ok', '%s: %s (%s)' % (canonical, why, cite)

    def no(why):
        return 'no', '%s: %s (%s)' % (canonical, why, cite)

    if kind == 'analog-in':
        return ok('has an ADC alternate function (%s)' % ', '.join(f for f in fns if f.startswith('ADC'))) if any(f.startswith('ADC') for f in fns) \
            else no('no ADC alternate function (%s)' % '/'.join(fns))
    if kind == 'pwm-out':
        oc = [f for f in fns if f in PWM_FUNCTIONS]
        return ok('has an Output Compare alternate function (%s, timer %s)' % (oc[0], FUNCTION_PERIPHERAL[oc[0]][0])) if oc \
            else no('no Output Compare function (%s) — not PWM-capable' % '/'.join(fns))
    if kind == 'uart-rx':
        return ok('has the USART0 RXD alternate function') if 'RXD' in fns else no('no RXD alternate function (%s)' % '/'.join(fns))
    if kind == 'uart-tx':
        return ok('has the USART0 TXD alternate function') if 'TXD' in fns else no('no TXD alternate function (%s)' % '/'.join(fns))
    if kind == 'i2c-sda':
        return ok('has the TWI SDA alternate function') if 'SDA' in fns else no('no SDA alternate function (%s)' % '/'.join(fns))
    if kind == 'i2c-scl':
        return ok('has the TWI SCL alternate function') if 'SCL' in fns else no('no SCL alternate function (%s)' % '/'.join(fns))
    if kind == 'spi-mosi':
        return ok('has the SPI MOSI alternate function') if 'MOSI' in fns else no('no MOSI alternate function (%s)' % '/'.join(fns))
    if kind == 'spi-miso':
        return ok('has the SPI MISO alternate function') if 'MISO' in fns else no('no MISO alternate function (%s)' % '/'.join(fns))
    if kind == 'spi-sck':
        return ok('has the SPI SCK alternate function') if 'SCK' in fns else no('no SCK alternate function (%s)' % '/'.join(fns))
    if kind == 'spi-ss':
        return ok('has the SPI SS alternate function') if 'SS' in fns else no('no SS alternate function (%s)' % '/'.join(fns))
    if kind in ('digital-in', 'digital-out'):
        return ok('every I/O pin is GPIO-capable')
    if kind == 'interrupt-in':
        if any(f in ('INT0', 'INT1') for f in fns):
            return ok('has a dedicated external-interrupt alternate function (%s)' % ', '.join(f for f in fns if f in ('INT0', 'INT1')))
        pcint = [f for f in fns if f.startswith('PCINT')]
        if pcint:
            return 'undetermined', ('%s: has a pin-change-interrupt alternate function (%s) but enabling it needs the PCICR/PCMSKn bank '
                                     'registers, not modeled per-pin yet (%s) — %s' % (canonical, pcint[0], cite, INT_DOC_NOTE))
        return no('no INT0/INT1/PCINTn alternate function')
    return 'undetermined', 'no rule written for kind %r' % kind


def board_target_universe(r):
    """Every 'pin' a task could be dropped on, for one board.custom.board_object.rows_for(...) result `r`: its
    BoardPin rows, PLUS the connector-only power/ground labels that are not themselves a BoardPin (the UNO's POWER
    header: NC, IOREF, RESET, +3V3, +5V, GND, VIN, and DIGITAL_H's AREF/GND) — synthesized as pin-shaped dicts with
    function='power'|'ground' so compatible()'s never-assignable rule covers them too ("the pins are the targets",
    his ruling — including the ones that are never valid)."""
    from board.custom.pinmap_svg import GROUND_LABELS, POWER_LABELS
    out = list(r['pins'])
    seen = {p['canonical'] for p in out}
    for cp in r.get('connector_pins', []):
        label = cp.get('label', '')
        if cp.get('board_pin') or label in seen or label not in (POWER_LABELS | GROUND_LABELS):
            continue
        seen.add(label)
        out.append({'canonical': label, 'function': 'ground' if label in GROUND_LABELS else 'power', 'soc_pin': '',
                    'signal': '', 'net': cp.get('net', ''), 'board': r['board']})
    return out


def valid_targets(kind, r):
    """[{pin, verdict, reason}, ...] over EVERY pin of board rows `r` (board_target_universe) for one task kind —
    the per-kind listing `cmod.custom.firmware.valid_targets_for_task` wraps with registration/conflict state."""
    soc_by_pin = {s['pin']: s for s in r.get('soc_pins', [])}
    out = []
    for pin in board_target_universe(r):
        soc_pin = soc_by_pin.get(pin.get('soc_pin') or '')
        verdict, reason = compatible(kind, pin, soc_pin)
        out.append({'pin': pin['canonical'], 'verdict': verdict, 'reason': reason})
    return out
