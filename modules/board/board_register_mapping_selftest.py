"""board_register_mapping_selftest — rm-0 + rm-1 (REGISTER_MAPPING_PLAN.md §1, §4): every ATmega328P register lands in at least one domain by a CITED rule
(none unclassified; an unknown register is unclassified by name), DDRx / PORTx / PINx / UCSR0A / MCUSR land as the plan lists them with their read and write
roles, field roles follow access, the deferred branches show as future scope; the phase groupings cover the seven phases; the stage assessment gives UNO D0
BOOTLOADER = reserved (Optiboot), a GPIO-output claim on D0 = a boot-critical conflict, a uart-rx claim on D0 = a warning, D13 = warning (the L LED buffer),
a pin with no evidence = unknown (never valid); conditions are judged in a context; the door answers; the manifest conforms.

    PYTHONPATH=.:modules python3 -m board.board_register_mapping_selftest      # from polari-framework/
"""
import json
import sys
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def taxonomy():
    from board.custom import register_taxonomy as T
    from board.custom import hardware_chain as H
    regs = sorted(H.R.load('atmega328p')['registers'])
    cls = {r: T.classify('atmega328p', r) for r in regs}
    un = [r for r, c in cls.items() if c['domains'] == ['unclassified']]
    check('rm-0 EVERY 328P register (%d) lands in at least one domain by a rule; none unclassified' % len(regs), len(regs) == 96 and not un, un)
    check('rm-0 every rule cites the datasheet (DS40002061B): register sections with their page where board cites them, else the chapter - said',
          all('DS40002061B' in c['cite'] for c in cls.values()) and all(('p.' in c['cite']) or ('not re-read' in c['cite']) or ('not read' in c['cite']) for c in cls.values()),
          [r for r, c in cls.items() if 'DS40002061B' not in c['cite']])
    dead = [rule['pattern'] for rule in T.RULES['atmega328p'] if not any(rule['rx'].match(r) for r in regs)]
    check('rm-0 no dead rule: every rule matches a register of the snapshot', not dead, dead)
    want = {'DDRD': (['mcu-pin/direction'], ['control'], ['control']), 'PORTD': (['mcu-pin/io-data', 'mcu-pin/electrical'], ['data', 'control'], ['data', 'control']),
            'PIND': (['mcu-pin/io-data'], ['status'], ['control']), 'UCSR0A': (['mcu-peripheral/uart'], ['status', 'control'], ['control']),
            'MCUSR': (['mcu-system/reset'], ['status'], ['control'])}
    got = {r: (cls[r]['domains'], cls[r]['roles']['read'], cls[r]['roles']['write']) for r in want}
    check('rm-0 DDRx / PORTx / PINx / UCSR0A / MCUSR land as the plan lists: direction control; io-data data + pull-up control; PINx reads status, a write toggles '
          '(control); UCSR0A uart status (+ U2X0 control); MCUSR reset status, written to clear', got == want, got)
    u = T.classify('atmega328p', 'FOOREG')
    check('rm-0 a register no rule matches is `unclassified` BY NAME (never guessed)', u['domains'] == ['unclassified'] and 'FOOREG' in u['cite'] and u['verification'] == 'none')
    tree = {t['path']: t for t in T.tree('atmega328p', regs)}
    check('rm-0 TREE: the SoC / platform branches are deferred (count 0, future scope); mcu-pin/direction holds DDRB/C/D; no unclassified branch',
          all(tree[p]['state'] == 'future scope' and tree[p]['count'] == 0 for p in tree if p.split('/')[0] in ('soc-interconnect', 'soc-processor', 'soc-device', 'platform-virtual'))
          and tree['mcu-pin/direction']['registers'] == 'DDRB, DDRC, DDRD' and 'unclassified' not in tree, tree['mcu-pin/direction'])
    rows = {r['register']: r for r in H.registers()}
    fields = {f['name']: f for f in H.register_fields()}
    check('rm-0 the chain rows carry it: Register.domains_json / roles_json / taxonomy_cite; RegisterField.roles_json refined by access (PIND0 rw-toggle: read status / '
          'write control; INTF0 w1c: read status / write control; PORTD0 rw: the register\'s data + control)',
          json.loads(rows['DDRD']['domains_json']) == ['mcu-pin/direction'] and json.loads(rows['PIND']['roles_json']) == {'read': ['status'], 'write': ['control']}
          and '§14.4' in rows['DDRD']['taxonomy_cite']
          and json.loads(fields['atmega328p:PIND.PIND0']['roles_json']) == {'read': ['status'], 'write': ['control']}
          and json.loads(fields['atmega328p:EIFR.INTF0']['roles_json']) == {'read': ['status'], 'write': ['control']}
          and json.loads(fields['atmega328p:PORTD.PORTD0']['roles_json']) == {'read': ['data', 'control'], 'write': ['data', 'control']})


def stages():
    from board.custom import pin_stages as P
    l4 = [p for _s, ps in P.GROUPINGS['lifecycle-4']['stages'] for p in ps]
    check('rm-1 GROUPINGS (D-rm-2): lifecycle-4 covers the seven phases exactly once (RESET / BOOTLOADER / INITIALIZATION / ACTIVE); boot-safety, firmware and all-7 '
          'are data rows beside it', sorted(l4) == sorted(['power-up', 'reset', 'bootloader', 'programming', 'debug', 'init', 'runtime'])
          and [s for s, _p in P.GROUPINGS['lifecycle-4']['stages']] == ['RESET', 'BOOTLOADER', 'INITIALIZATION', 'ACTIVE'] and set(P.GROUPINGS) == {'lifecycle-4', 'boot-safety', 'firmware', 'all-7'})
    a = {s['stage']: s for s in P.assess('arduino-uno-r3', 'D0')['stages']}
    check('rm-1 UNO D0 alone: RESET = input tri-state from the cited reset fields (DDD0 = 0, PORTD0 = 0); BOOTLOADER = reserved, owned by the boot firmware (Optiboot); '
          'INIT / ACTIVE owned by the bridge (the 16U2 transport) - each valid, said',
          a['RESET']['direction'] == 'input, tri-state' and 'DDRD.DDD0 = 0' in a['RESET']['register_fields'] and a['BOOTLOADER']['owner'] == 'boot-firmware'
          and 'Optiboot' in a['BOOTLOADER']['reasons'] and a['BOOTLOADER']['verdict'] == 'valid' and a['ACTIVE']['owner'] == 'bridge', {k: (v['verdict'], v['owner']) for k, v in a.items()})
    g = P.assess('arduino-uno-r3', 'D0', 'gpio-out')
    gs = {s['stage']: s for s in g['stages']}
    check('rm-1 a GPIO-output claim on D0 = CONFLICT in INIT and ACTIVE, BOOT-CRITICAL (D0 is the bootloader\'s link: the recovery path) and listed first',
          gs['INITIALIZATION']['verdict'] == gs['ACTIVE']['verdict'] == 'conflict' and gs['ACTIVE']['boot_critical'] and len(g['boot_critical']) == 2
          and 'recovery path' in g['boot_critical'][0]['boot_why'] and 'CONFLICT with the gpio-out claim' in gs['ACTIVE']['reasons'], {k: v['verdict'] for k, v in gs.items()})
    u = {s['stage']: s for s in P.assess('arduino-uno-r3', 'D0', 'uart-rx')['stages']}
    check('rm-1 a uart-rx claim on D0 IS the reserving peripheral (USART0): a warning, not a conflict, and not boot-critical',
          u['ACTIVE']['verdict'] == 'warning' and not u['ACTIVE']['boot_critical'], u['ACTIVE']['reasons'][:200])
    d13 = {s['stage']: s for s in P.assess('arduino-uno-r3', 'D13')['stages']}
    check('rm-1 D13 = warning in INIT / ACTIVE (the L LED buffer on the line); the ICSP programming row is NOT applied (icsp=connected does not hold) and says so',
          d13['ACTIVE']['verdict'] == 'warning' and 'L LED' in d13['ACTIVE']['reasons'] and 'not applied (condition icsp=connected' in d13['BOOTLOADER']['reasons'], d13['ACTIVE']['reasons'][:200])
    ic = {s['stage']: s for s in P.assess('arduino-uno-r3', 'D13', context={'icsp': 'connected'})['stages']}
    check('rm-1 CONTEXT: with icsp=connected the programming reservation applies (BOOTLOADER owned by the programmer)', ic['BOOTLOADER']['owner'] == 'programmer'
          and 'ICSP SCK' in ic['BOOTLOADER']['reasons'], ic['BOOTLOADER']['reasons'][:200])
    d5 = P.assess('arduino-uno-r3', 'D5')['stages']
    a0 = {s['stage']: s for s in P.assess('arduino-uno-r3', 'A0')['stages']}
    zero = P.assess('arduino-zero', 'D0')['stages']
    check('rm-1 NO EVIDENCE = UNKNOWN: D5 is valid only because the cited table gives it no constraint ("free"); A0\'s RESET is unknown (no cited Port C reset fields); '
          'a board with no lifecycle table is unknown in every stage - never valid',
          all(s['verdict'] == 'valid' for s in d5) and 'free: the cited lifecycle table' in d5[3]['reasons'] and a0['RESET']['verdict'] == 'unknown'
          and 'no cited reset-value fields' in a0['RESET']['reasons'] and all(s['verdict'] == 'unknown' for s in zero), (a0['RESET']['verdict'], [s['verdict'] for s in zero]))
    c3 = {s['stage']: s for s in P.assess('esp32-c3', 'GPIO9')['stages']}
    check('rm-1 C3 GPIO9: RESET = warning (a strapping pin, latched at reset), from lifecycle_c3', c3['RESET']['verdict'] == 'warning' and 'strapping' in c3['RESET']['reasons'])
    try:
        P.assess('arduino-uno-r3', 'D0', 'teleport')
        bad = False
    except KeyError as e:
        bad = 'claim must be one of' in e.args[0]
    check('rm-1 an unknown claim is refused with the vocabulary', bad)


def door():
    from board.board_object_api import BoardObjectAPI
    api = BoardObjectAPI(polServer=None, manager=None)

    def get(board, pin, params):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        api.on_get_stages(types.SimpleNamespace(params=params, get_param=lambda k: params.get(k)), resp, board, pin)
        return resp
    full, view, bad = get('arduino-uno-r3', 'D0', {'claim': 'gpio-out'}), get('arduino-uno-r3', 'D0', {'claim': 'gpio-out', 'view': 'stages'}), get('arduino-uno-r3', 'D0', {'grouping': 'x'})
    check('rm-1 DOOR: GET /api/board/arduino-uno-r3/pins/D0/stages?claim=gpio-out = the matrix + boot_critical; ?view=stages = plain rows, boot-critical first; '
          'unknown grouping 422', full.media['ok'] and len(full.media['boot_critical']) == 2 and view.media['rows'][0]['boot_critical'] is True
          and all(not isinstance(v, (dict, list)) for r in view.media['rows'] for v in r.values()) and bad.status.startswith('422'), bad.status)
    from moduleService.manifests import conform
    r = conform('board')
    check('MANIFEST: pol modules conform board is clean with the new files listed', r['ok'], r.get('findings'))


def main():
    taxonomy()
    stages()
    door()
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
