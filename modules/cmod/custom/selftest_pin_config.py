"""selftest_pin_config — ucd-0b (UNO_CORE_DEMO_PLAN.md §5f/§5g): the GENERATED pin_config.h/.c
(cmod.custom.pin_config_gen) over uno-sim-rig's real claims, plus a synthetic EXINT settings list (D2) built
directly to exercise the fixed init order (DDR, PORT, EICRA, EIFR, EIMSK), the w1c plain write, and the
w-strobe refusal — same shape as selftest_export.py's export_parts. Run by cmod_selftest.main() (pin_config_parts).
"""
import re

SOLUTION, GRAPH = 'uno-sim-rig', 'uno-sim-rig-graph'


def pin_config_parts(check):
    def uno_sim_rig_render():
        _uno_sim_rig_render(check)

    def fixed_order_and_comments():
        _fixed_order_and_comments(check)

    def w1c_plain_write():
        _w1c_plain_write(check)

    def refusals():
        _refusals(check)

    def no_runtime_dependency():
        _no_runtime_dependency(check)

    def button_clock_render():
        _button_clock_render(check)

    return (uno_sim_rig_render, fixed_order_and_comments, w1c_plain_write, refusals, no_runtime_dependency, button_clock_render)


def _soc_pin_bit(canonical):
    """The bit this canonical board pin's DDR/PORT register touches, read off the SAME SocPin rows claims.py reads —
    never a hard-coded 5/6."""
    from cmod.custom import claims as C
    tables = C._chain_tables(None)
    soc_pins = C._index(tables, 'SocPin')
    bp = next(r for r in tables.get('BoardPin', []) if r['canonical'] == canonical and r.get('board') == 'arduino-uno-r3')
    from board.custom.soc_atmega328p import SOC
    sp = soc_pins['%s:%s' % (SOC, bp['soc_pin'])]
    return sp['port'], sp['bit']


def _uno_sim_rig_render(check):
    from cmod.custom import pin_config_gen as PG
    out = PG.render(SOLUTION, GRAPH)
    h, c = out['pin_config.h'].decode(), out['pin_config.c'].decode()
    port13, bit13 = _soc_pin_bit('D13')
    port6, bit6 = _soc_pin_bit('D6')
    check('pin_config.h declares PIN_CONFIG_D13_DDR = DDR<port> and PIN_CONFIG_D13_BIT = D13\'s OWN SocPin bit (never 5 hard-coded)',
          ('#define PIN_CONFIG_D13_DDR               DDR%s' % port13) in h and re.search(r'#define PIN_CONFIG_D13_BIT\s+%d\b' % bit13, h), h)
    check('pin_config.h declares PIN_CONFIG_D6_DDR = DDR<port> and PIN_CONFIG_D6_BIT = D6\'s OWN SocPin bit (never 6 hard-coded)',
          ('#define PIN_CONFIG_D6_DDR                DDR%s' % port6) in h and re.search(r'#define PIN_CONFIG_D6_BIT\s+%d\b' % bit6, h), h)
    check('pin_config.h declares the prototype', 'void pin_config_init(void);' in h)
    check('pin_config.c writes DDRB (via its PIN_CONFIG_D13_DDR alias) using PIN_CONFIG_D13_BIT',
          'PIN_CONFIG_D13_DDR = (uint8_t)((PIN_CONFIG_D13_DDR & (uint8_t)~(((uint8_t)0x01 << PIN_CONFIG_D13_BIT))) | '
          '(((uint8_t)0x01 << PIN_CONFIG_D13_BIT)));' in c, c)
    check('pin_config.c writes DDRD (via its PIN_CONFIG_D6_DDR alias) using PIN_CONFIG_D6_BIT',
          'PIN_CONFIG_D6_DDR = (uint8_t)((PIN_CONFIG_D6_DDR & (uint8_t)~(((uint8_t)0x01 << PIN_CONFIG_D6_BIT))) | '
          '(((uint8_t)0x01 << PIN_CONFIG_D6_BIT)));' in c, c)
    check('pin_config.c defines no main() and calls no hal_* function — pure avr-libc, main() is elsewhere (polari_graph.c)',
          'int main' not in c and not re.search(r'\bhal_\w+\s*\(', c), c)
    check('pin_config.h/.c carry a header naming the solution, graph, board and "edit the model, not this file" — no literal timestamp in the bytes',
          all(x in h for x in ('Firmware Solution %s' % SOLUTION, GRAPH, 'arduino-uno-r3', 'EDIT THE MODEL'))
          and all(x in c for x in ('Firmware Solution %s' % SOLUTION, GRAPH, 'arduino-uno-r3', 'EDIT THE MODEL')))
    out2 = PG.render(SOLUTION, GRAPH)
    check('render() is deterministic: re-rendering with nothing changed produces BYTE-IDENTICAL output (no timestamp in the file)',
          out2['pin_config.h'] == out['pin_config.h'] and out2['pin_config.c'] == out['pin_config.c'])


#: a synthetic settings list (never derived from claims.py — the FIXED-ORDER/comment/w1c/refusal checks below drive
#: cmod.custom.pin_config_gen.plan_from_rows directly, per the task's own fallback) for a D2 interrupt-in claim:
#: mode in, pull up, edge any — exercising DDR, PORT, EICRA (a 2-bit field), EIFR (w1c) and EIMSK in one register set.
def _synthetic_d2_rows():
    rs = [
        {'name': 'synth:DDRD:init', 'register': 'atmega328p:DDRD', 'phase': 'init', 'value': '0x00', 'write_mask': '0x04', 'value_bits': '00000100'},
        {'name': 'synth:PORTD:init', 'register': 'atmega328p:PORTD', 'phase': 'init', 'value': '0x04', 'write_mask': '0x04', 'value_bits': '00000100'},
        {'name': 'synth:EICRA:init', 'register': 'atmega328p:EICRA', 'phase': 'init', 'value': '0x01', 'write_mask': '0x03', 'value_bits': '00000001'},
        {'name': 'synth:EIFR:init', 'register': 'atmega328p:EIFR', 'phase': 'init', 'value': '0x01', 'write_mask': '0x01', 'value_bits': '00000001'},
        {'name': 'synth:EIMSK:init', 'register': 'atmega328p:EIMSK', 'phase': 'init', 'value': '0x01', 'write_mask': '0x01', 'value_bits': '00000001'},
    ]
    fs = [
        {'register_setting': 'synth:DDRD:init', 'register_field': 'atmega328p:DDRD.DDD2', 'value': '0', 'meaning': 'input',
         'pin_claim': 'synth:D2', 'task': 'sense_isr', 'rule': 'ddr-from-interrupt-in'},
        {'register_setting': 'synth:PORTD:init', 'register_field': 'atmega328p:PORTD.PORTD2', 'value': '1', 'meaning': 'pull-up',
         'pin_claim': 'synth:D2', 'task': 'sense_isr', 'rule': 'port-pull-up'},
        {'register_setting': 'synth:EICRA:init', 'register_field': 'atmega328p:EICRA.ISC0', 'value': '01', 'meaning': 'any logical change',
         'pin_claim': 'synth:D2', 'task': 'sense_isr', 'rule': 'edge-any-to-ISC0'},
        {'register_setting': 'synth:EIFR:init', 'register_field': 'atmega328p:EIFR.INTF0', 'value': '1', 'meaning': 'clear pending',
         'pin_claim': 'synth:D2', 'task': 'sense_isr', 'rule': 'clear-pending-before-enable'},
        {'register_setting': 'synth:EIMSK:init', 'register_field': 'atmega328p:EIMSK.INT0', 'value': '1', 'meaning': 'enable',
         'pin_claim': 'synth:D2', 'task': 'sense_isr', 'rule': 'enable-external-interrupt'},
    ]
    return rs, fs


def _fixed_order_and_comments(check):
    from cmod.custom import pin_config_gen as PG
    rs, fs = _synthetic_d2_rows()
    plan, defines = PG.plan_from_rows(rs, fs)
    check('plan_from_rows orders a D2 interrupt-in claim\'s registers DDR, PORT, EICRA, EIFR, EIMSK (his fixed order)',
          [p['regname'] for p in plan] == ['DDRD', 'PORTD', 'EICRA', 'EIFR', 'EIMSK'], [p['regname'] for p in plan])
    c = PG._render_c(plan, 'synth-sol', 'synth-graph', 'arduino-uno-r3').decode()
    positions = [c.index('PIN_CONFIG_D2_%s = ' % reg) for reg in ('DDR', 'PORT', 'EICRA', 'EIFR', 'EIMSK')]
    check('the GENERATED C itself writes those five registers in that exact order (strictly increasing line positions)',
          positions == sorted(positions) and len(set(positions)) == 5, positions)
    check('every register write is preceded by a comment naming the claim, the task and the rule for each field it sets',
          all(x in c for x in ('claim synth:D2', 'task sense_isr', 'rule ddr-from-interrupt-in', 'rule port-pull-up',
                               'rule edge-any-to-ISC0', 'rule clear-pending-before-enable', 'rule enable-external-interrupt')), c)
    check('the EICRA comment cites the field name ISC0 and its meaning', 'ISC0' in c and 'any logical change' in c, c)


def _w1c_plain_write(check):
    from cmod.custom import pin_config_gen as PG
    rs, fs = _synthetic_d2_rows()
    plan, _ = PG.plan_from_rows(rs, fs)
    c = PG._render_c(plan, 'synth-sol', 'synth-graph', 'arduino-uno-r3').decode()
    check('EIFR (access w1c) renders as a PLAIN WRITE of the mask — never a read-modify-write (that would clear every other pending flag)',
          'PIN_CONFIG_D2_EIFR = (uint8_t)(((uint8_t)0x01 << PIN_CONFIG_D2_EIFR_BIT));' in c
          and 'PIN_CONFIG_D2_EIFR = (uint8_t)((PIN_CONFIG_D2_EIFR &' not in c, c)
    check('every OTHER register (rw) renders as a masked read-modify-write (bits outside write_mask keep the reset value, said in a comment)',
          'PIN_CONFIG_D2_DDR = (uint8_t)((PIN_CONFIG_D2_DDR & (uint8_t)~' in c and 'keep the chip\'s' in c, c)


def _refusals(check):
    """access refusal is checked FIELD BY FIELD, independent of which register it sits in — the real datasheet's
    DDR/PORT/EIFR/EIMSK/EICRA/PCMSK/PCICR fields are all rw or w1c (board.custom.register_fields_atmega328p), so to
    exercise the access-refusal path itself (never reachable with a real field this generator ever sees) the test
    attaches a w-strobe / rw-toggle field to a register that IS in the fixed order (PORTD) — the point is the access
    check, not the register."""
    from cmod.custom import pin_config_gen as PG
    rs = [{'name': 'synth:PORTD:init', 'register': 'atmega328p:PORTD', 'phase': 'init', 'value': '0x04', 'write_mask': '0x04', 'value_bits': '00000100'}]
    fs = [{'register_setting': 'synth:PORTD:init', 'register_field': 'atmega328p:TCCR2B.FOC2A', 'value': '1', 'meaning': 'strobe',
          'pin_claim': 'synth:D11', 'task': 'x', 'rule': 'x'}]
    try:
        PG.plan_from_rows(rs, fs)
        check('a w-strobe field (TCCR2B.FOC2A) is refused by name — w-strobe never belongs in init', False)
    except PG.GenRefused as e:
        check('a w-strobe field (TCCR2B.FOC2A) is refused by name — w-strobe never belongs in init',
              'FOC2A' in str(e) and 'w-strobe' in str(e), str(e))

    rs2 = [{'name': 'synth:PORTD:init', 'register': 'atmega328p:PORTD', 'phase': 'init', 'value': '0x04', 'write_mask': '0x04', 'value_bits': '00000100'}]
    fs2 = [{'register_setting': 'synth:PORTD:init', 'register_field': 'atmega328p:PIND.PIND2', 'value': '1', 'meaning': 'toggle',
           'pin_claim': 'synth:D2', 'task': 'x', 'rule': 'x'}]
    try:
        PG.plan_from_rows(rs2, fs2)
        check('an rw-toggle field (PIND.PIND2) is refused by name — rw-toggle never belongs in init', False)
    except PG.GenRefused as e:
        check('an rw-toggle field (PIND.PIND2) is refused by name — rw-toggle never belongs in init',
              'PIND2' in str(e) and 'rw-toggle' in str(e), str(e))

    check('a register outside the fixed init order (TCCR2B is timer config, stays in the hand-written HAL this slice) is refused by name',
          _category_refused(PG, 'TCCR2B'))


def _category_refused(PG, regname):
    try:
        PG._category(regname)
    except PG.GenRefused as e:
        return regname in str(e)
    return False


def _no_runtime_dependency(check):
    from cmod.custom import pin_config_gen as PG
    out = PG.render(SOLUTION, GRAPH)
    c = out['pin_config.c'].decode()
    h = out['pin_config.h'].decode()
    includes_c = re.findall(r'^#include\s+(\S+)', c, re.MULTILINE)
    includes_h = re.findall(r'^#include\s+(\S+)', h, re.MULTILINE)
    check('pin_config.c includes ONLY <avr/io.h>, <stdint.h> and its own pin_config.h — no Polari, no board_config.h',
          set(includes_c) == {'<avr/io.h>', '<stdint.h>', '"pin_config.h"'}, includes_c)
    check('pin_config.h includes nothing (just the include guard, the #defines and the prototype)', includes_h == [], includes_h)
    check('no "import" / "polari" runtime token appears in either generated file (python/runtime-free C)',
          'import ' not in c and 'import ' not in h and 'PolariManager' not in c and 'PolariManager' not in h)


def _button_clock_render(check):
    """ucd-0e2b: pin_config.c over uno-button-clock's real claims — the fixed order (DDR, PORT, EICRA, EIFR, EIMSK),
    EIFR as a plain write (never read-modify-write — w1c), and every line's comment naming the claim + task + rule."""
    from cmod.custom import pin_config_gen as PG
    out = PG.render('uno-button-clock', 'uno-button-clock-graph')
    c = out['pin_config.c'].decode()
    order = [m.start() for reg in ('PIN_CONFIG_D13_DDR', 'PIN_CONFIG_D2_DDR', 'PIN_CONFIG_D2_PORT', 'PIN_CONFIG_D2_EICRA',
                                    'PIN_CONFIG_D2_EIFR', 'PIN_CONFIG_D2_EIMSK') for m in [re.search(r'%s\s*=' % reg, c)]]
    check('the fixed order: DDR (B then D), PORT, EICRA, EIFR, EIMSK — each register appears once, in that order',
          None not in order and order == sorted(order), order)
    eifr_line = re.search(r'PIN_CONFIG_D2_EIFR = [^;]+;', c).group()
    check('EIFR is a PLAIN write (no `& ~(...)` read-modify-write — w1c clearing a pending flag never reads first)',
          '&' not in eifr_line or '~' not in eifr_line, eifr_line)
    check('every init write\'s comment names its claim (uno-button-clock:D2/D3/D6/D13), its task (button_init/sense_init/'
          'led_init/l_led_init) and a rule',
          all(('claim uno-button-clock:%s' % p) in c for p in ('D2', 'D3', 'D6', 'D13'))
          and all(('task %s' % t) in c for t in ('button_init', 'sense_init', 'led_init', 'l_led_init'))
          and 'rule ddr-from-interrupt-in' in c and 'rule edge-falling-to-ISC0' in c and 'rule edge-any-to-ISC1' in c
          and 'rule clear-pending-before-enable' in c and 'rule enable-external-interrupt' in c, c)
    check('the EXINT lines carry the exact bit values the plan specifies: EICRA = 00000110 (ISC0=10 falling, ISC1=01 '
          'any, write_mask 0x0F), EIFR = 00000011 (write_mask 0x03), EIMSK = 00000011 (write_mask 0x03)',
          re.search(r'EICRA:init = 00000110 \(write_mask 0x0F\)', c) is not None
          and re.search(r'EIFR:init = 00000011 \(write_mask 0x03\)', c) is not None
          and re.search(r'EIMSK:init = 00000011 \(write_mask 0x03\)', c) is not None, c)
