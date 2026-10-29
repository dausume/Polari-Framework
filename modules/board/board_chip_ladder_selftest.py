"""board_chip_ladder_selftest - chp-0 (MISSION_GENERIC_PLAN.md section 13.1): the chips-and-levels ladder - two sections that never mix, two RISC-V
chips per level, every level claim with a basis, every emulator with a status, the boards he showed on the bench, the three doors and the page.

    PYTHONPATH=.:modules python3 -m board.board_chip_ladder_selftest
"""
import json

LEVELS = ('bare_c', 'freertos', 'zephyr', 'ubuntu')


def run_chip_ladder(check):
    from board.custom import chip_ladder as CL
    from board.custom import chip_ladder_seed as S
    from board.objects.board.ChipLadderEntry import ChipLadderEntry as E
    rows = S.SEED_CHIP_LADDER
    names = [r['name'] for r in rows]
    check('chp-0 ROWS: %d entries, unique names, every one in exactly one section (riscv | convenience)' % len(rows),
          len(set(names)) == len(names) and all(r['section'] in E.SECTIONS for r in rows), names)
    riscv = [r for r in rows if r['section'] == 'riscv']
    conv = [r for r in rows if r['section'] == 'convenience']
    slots = sorted(r['slot'] for r in riscv if r['slot'] != 'exception')
    check('chp-0 SAMPLE: the RISC-V section fills exactly eight slots, two per level (his "2 risc-v chips per level"), and the exceptions sit beside them',
          slots == sorted('%s %d' % (lv, i) for lv in ('bare-c', 'freertos', 'zephyr', 'ubuntu') for i in (1, 2)) and len([r for r in riscv if r['slot'] == 'exception']) >= 3,
          slots)
    check('chp-0 APART: no convenience board is RISC-V and every convenience family is one of AVR / ARM Cortex-M0+ / Xtensa LX7 / FPGA (his "separated out cleanly"; the Elecrow board is an S3 by its silk, 2026-10-24)',
          all(r['family'] != 'RISC-V' for r in conv) and {r['family'] for r in conv} <= {'AVR', 'ARM Cortex-M0+', 'Xtensa LX7', 'FPGA'}
          and all(r['family'] == 'RISC-V' for r in riscv), sorted({r['family'] for r in conv}))
    bad = []
    for r in rows:
        lv = json.loads(r['levels_json'])
        for k in LEVELS:
            v = lv.get(k) or {}
            if v.get('status') not in E.STATUSES or not v.get('basis'):
                bad.append((r['name'], k, v))
    check('chp-0 BASIS: every one of the %d level claims is a known word and carries a basis (a URL, a module, or the word unverified) - nothing guessed' % (4 * len(rows)),
          not bad, bad[:3])
    yes_no_url = [(r['name'], k) for r in rows for k, v in json.loads(r['levels_json']).items()
                  if v.get('status') == 'yes' and 'http' not in v.get('basis', '') and 'board.custom' not in v.get('basis', '') and 'see the' not in v.get('basis', '')
                  and 'avr-gcc' not in v.get('basis', '') and 'ESP-IDF' not in v.get('basis', '') and 'Arduino' not in v.get('basis', '') and 'riscv-cores-reference' not in v.get('basis', '')
                  and 'Pico SDK' not in v.get('basis', '') and 'FreeRTOS' not in v.get('basis', '')]
    check('chp-0 CITED: every "yes" names a document, a module or a toolchain in its basis', not yes_no_url, yes_no_url[:4])
    emus = {r['name']: json.loads(r['emulator_json']) for r in rows}
    check('chp-0 EMULATORS: every chip names an emulator entry with a known status and a pins word; the AVRs are simavr with real pins; the SAMD21 has none known',
          all(e.get('status') in E.EMULATOR_STATUSES and e.get('pins') in ('real', 'stub', 'unverified', 'none') for e in emus.values())
          and all(emus[n]['kind'] == 'simavr' and emus[n]['pins'] == 'real' for n in ('atmega328p', 'atmega2560', 'attiny85'))
          and emus['samd21g18a']['status'] == 'none', {n: (e['status'], e['pins']) for n, e in emus.items()})
    check('chp-0 PREFER EXISTING: every RISC-V sample slot (not the exceptions) names an emulator that exists (his "preferring solutions where those already exist")',
          all(emus[r['name']]['status'].startswith('exists') for r in riscv if r['slot'] != 'exception'),
          [(r['name'], emus[r['name']]['status']) for r in riscv if r['slot'] != 'exception'])
    on_hand = {b['title'] for r in rows for b in json.loads(r['boards_json']) if b.get('on_hand')}
    check('chp-0 BENCH: the boards he showed 2026-10-24 are on hand - the UNO R3, the Arduino Zero, the Feather M0 Express, the Elecrow ESP32 eval board, the bare iCE40UP5K',
          all(any(w in t for t in on_hand) for w in ('UNO R3', 'Arduino Zero', 'Feather M0 Express', 'ESP32', 'iCE40UP5K')), sorted(on_hand))
    check('chp-0 PRIVACY: no e-mail, street or invoice number in any row (part names only)',
          not any(s in json.dumps(rows) for s in ('@', 'Arrowhead', 'Fairfax', '3689309', '134236176')), '')
    # ---- the doors
    st, body = CL.door(None, {'section': 'riscv'}, 'chips')
    check('chp-0 DOOR chips?section=riscv: 200, only RISC-V rows, each flat row carries the four level words, their basis columns, the emulator columns and in_polari',
          st == 200 and body['ok'] and body['rows'] and all(r['section'] == 'riscv' for r in body['rows'])
          and all(k in body['rows'][0] for k in LEVELS + tuple(k + '_basis' for k in LEVELS) + ('emulator', 'emulator_pins', 'emulator_status', 'in_polari', 'on_hand')),
          sorted(body['rows'][0].keys()) if body.get('rows') else body)
    c3 = next(r for r in body['rows'] if r['name'] == 'esp32c3')
    check('chp-0 DERIVED: the C3 row\'s in_polari is worked out from the board tables (SoC row yes, thousands of pin functions; rm-2b: its 91 drawing-set registers, still 0 '
          'memory regions - the G1 gap said in numbers, now partly closed)',
          c3['in_polari'].startswith('SoC row yes') and 'registers 91' in c3['in_polari'] and 'memory regions 0' in c3['in_polari'] and 'pin functions' in c3['in_polari'], c3['in_polari'])
    st2, body2 = CL.door(None, {'section': 'convenience'}, 'chips')
    uno = next(r for r in body2['rows'] if r['name'] == 'atmega328p')
    check('chp-0 DERIVED: the UNO row holds its SoC and board rows (the board tables know arduino-uno-r3 and atmega328p)',
          st2 == 200 and uno['in_polari'].startswith('SoC row yes') and 'arduino-uno-r3' in uno['in_polari'], uno['in_polari'])
    check('chp-0 DOOR: a bad section is 400; levels gives the four; emulators gives one row per kind with the chips it covers',
          CL.door(None, {'section': 'arm'}, 'chips')[0] == 400 and [r['level'] for r in CL.door(None, {}, 'levels')[1]['rows']] == list(LEVELS)
          and {r['kind'] for r in CL.door(None, {}, 'emulators')[1]['rows']} >= {'simavr', 'esp-emulator', 'qemu-upstream', 'renode', 'none'}
          and any('esp32c3' in r['chips_covered'] for r in CL.door(None, {}, 'emulators')[1]['rows'] if r['kind'] == 'esp-emulator'), '')
    # ---- the page
    from board.chip_ladder_page import CHIP_LADDER_PAGES as P
    page = P[0]
    d = json.loads(page['definition'])
    tabs = d.get('tabs') or []
    check('chp-0 PAGE: /display/chip-ladder has the levels table above three tabs - RISC-V, Convenience, Emulators - and every table reads a chip-ladder door',
          page['pageRoute'] == 'chip-ladder' and page['isPage'] and [t['key'] for t in tabs] == ['riscv', 'convenience', 'emulators']
          and all('/api/board/chip-ladder' in json.dumps(t) for t in tabs) and 'chip-ladder/levels' in json.dumps(d['rows']),
          [t['key'] for t in tabs])
    check('chp-0 PAGE APART: the RISC-V tab\'s tables read ?section=riscv only and the convenience tab\'s ?section=convenience only',
          'section=convenience' not in json.dumps(tabs[0]) and 'section=riscv' not in json.dumps(tabs[1]), '')

def main():
    fails = []

    def check(label, cond, extra=''):
        print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, '' if cond else '  <- %r' % (extra,)))
        if not cond:
            fails.append(label)
    run_chip_ladder(check)
    print('chip ladder selftest: %d failure(s)' % len(fails))
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
