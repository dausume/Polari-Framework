"""board_profile_overlap_selftest - pp-1: the cited overlap table (board.custom.profile_overlap*), its door, page, nav, manifest and CLI.
Called from board_selftest as run_profile_overlap(check). Every verdict is compared with the rules that own it (pin/net/periph modules), the pin sets with
target_compat, never with a copy."""
import contextlib
import io
import json
import os


def run_profile_overlap(check):
    from board.custom import profile_overlap as PO
    from board.custom import profile_overlap_kinds as K
    from board.custom import target_compat as TC
    from board.custom.profile_overlap_cites import CITES
    SOC = 'atmega328p'
    T = PO.table(SOC)
    L = lambda a, b, s: PO.lookup(SOC, a, b, s)   # noqa: E731

    # ---- size, completeness, citations
    tot = PO.totals(SOC)
    check('pp-1: 17 kinds -> 153 unordered pairs (self-pairs included) x 3 scopes = 459 verdicts, every one of compatible | exclusive | conditional | undetermined with a mode',
          tot['kinds'] == 17 and tot['pairs'] == 153 and tot['rows'] == len(T) == 459 and all(r['verdict'] in PO.VERDICTS and r['mode'] in PO.MODES for r in T) and sum(tot['verdicts'].values()) == 459, str(tot))
    check('pp-1: every kind is in the table with every other at every scope exactly once (no pair missing, none twice)',
          len({(r['a'], r['b'], r['scope']) for r in T}) == 459 and all(K.KINDS.index(r['a']) <= K.KINDS.index(r['b']) for r in T))
    bad = [r['name'] for r in T if not r['reason'] or not r['cites'] or not r['rule'] or any(k not in CITES for k in r['cite_keys'])]
    check('pp-1: EVERY row has a plain-words reason, a rule id and at least one citation that exists in the citation table', not bad, str(bad[:5]))
    dsb = [k for k, c in CITES.items() if c['kind'] == 'datasheet' and not (c['section'] and isinstance(c['page'], int) and 1 <= c['page'] <= 400 and c['quote'])]
    cdb = [k for k, c in CITES.items() if c['kind'] == 'code' and not (c['doc'] and c['section'])]
    check('pp-1: every datasheet citation has a section, a printed page and a verbatim quote; every code citation names its module and rule (%d citations)' % len(CITES), not dsb and not cdb, str((dsb, cdb)))
    check('pp-1: no row is decided by an `unwritten` fallback - a pair is settled by a cited rule or marked undetermined WITH its reason',
          not [r['name'] for r in T if r['rule'].endswith('unwritten')])
    und = [r for r in T if r['verdict'] == 'undetermined']
    check('pp-1: undetermined rows carry a reason that names what the datasheet does not say (%d: %s)' % (len(und), ', '.join(r['name'] for r in und)),
          und and all(len(r['reason']) > 60 and 'datasheet' in r['reason'] for r in und))
    check('pp-1: every conditional row states its condition', all(r['condition'] for r in T if r['verdict'] == 'conditional') and not [r for r in T if r['verdict'] != 'conditional' and r['condition']])
    check('pp-1: the table is symmetric: lookup(a, b) is lookup(b, a) for every pair and scope',
          all(PO.lookup(SOC, r['b'], r['a'], r['scope']) is PO.lookup(SOC, r['a'], r['b'], r['scope']) for r in T))
    check('pp-1: pin sets come from target_compat (pwm-out = the six Output Compare pins, uart-rx = PD0, interrupt-in = INT0/INT1 only) and the kinds target_compat lacks from the pin tables',
          K.pins_for('pwm-out') == ['PB1', 'PB2', 'PB3', 'PD3', 'PD5', 'PD6'] and K.pins_for('uart-rx') == ['PD0'] and K.pins_for('interrupt-in') == ['PD2', 'PD3']
          and K.pins_for('comparator-in') == ['PD6', 'PD7'] and K.pins_for('clock-in') == ['PD4', 'PD5'] and 'comparator-in' not in TC.TASK_KINDS)

    # ---- the examples of plan section 2.3, each with its citation
    def has(r, *keys):
        return all(k in r['cite_keys'] for k in keys)
    r = L('digital-out', 'digital-in', 'pin')
    check('pp-1 SAME PIN digital-out + digital-in = compatible, shared-read (PINx reads the pin whatever its direction, 14.2.4 p.86)', r['verdict'] == 'compatible' and r['mode'] == 'shared-read' and has(r, 'pinx-read') and 'p.86' in r['cite'], str(r))
    r = L('interrupt-in', 'digital-in', 'pin')
    check('pp-1 SAME PIN interrupt-in + digital-in = compatible, shared-read', r['verdict'] == 'compatible' and r['mode'] == 'shared-read' and has(r, 'pinx-read'))
    r = L('digital-out', 'pwm-out', 'pin')
    check('pp-1 SAME PIN pwm-out + digital-out = exclusive (an enabled alternate function overrides PORT/DDR, 14.3 p.89; Output Compare p.106/130/154); the way back is cited (COM bits cleared)',
          r['verdict'] == 'exclusive' and has(r, 'alt-override', 'oc0', 'oc1', 'oc2') and r['mode'] == 'time-multiplexed-later' and 'p.89' in r['cite'])
    r = L('digital-out', 'uart-rx', 'pin')
    check('pp-1 SAME PIN uart-rx + digital-out on PD0 = exclusive while RXEN0 is set (20.7 p.188, Table 14-11 p.99), released by 20.7.6 p.191', r['verdict'] == 'exclusive' and has(r, 'usart-rx', 'tbl-d-uart', 'usart-rx-off') and r['common_pins'] == 'PD0')
    r2 = L('digital-in', 'uart-rx', 'pin')
    check('pp-1 SAME PIN uart-rx + digital-in = conditional (the pin can be read, the USART owns direction and pull-up) - not "exclusive with everything"', r2['verdict'] == 'conditional' and r2['condition'])
    r = L('analog-in', 'digital-in', 'pin')
    check('pp-1 SAME PIN analog-in + digital-in = conditional on DIDR0 (24.9.5 p.261: the PIN bit reads zero when the digital buffer is off; 10.10.6 p.52 power)', r['verdict'] == 'conditional' and has(r, 'didr0', 'adc-didr-power') and 'p.261' in r['cite'])
    r = L('digital-out', 'interrupt-in', 'pin')
    check('pp-1 SAME PIN interrupt-in on an OUTPUT pin = conditional: the interrupt triggers even when the pin is an output (13 p.79) - a software interrupt', r['verdict'] == 'conditional' and has(r, 'exint-output') and 'p.79' in r['cite'])
    r = L('digital-out', 'digital-in', 'net')
    check('pp-1 SAME NET one output + an input = compatible, shared-read (rule single_output ok; the D6 -> D3 wire)', r['verdict'] == 'compatible' and has(r, 'single-output') and 'single_output' in r['cite'])
    check('pp-1 SAME NET any number of inputs = compatible; two outputs = exclusive (single_output refuses)', L('digital-in', 'interrupt-in', 'net')['verdict'] == 'compatible' and L('digital-in', 'interrupt-in', 'net')['rule'] == 'net.inputs-only'
          and L('digital-out', 'digital-out', 'net')['verdict'] == 'exclusive' and L('digital-out', 'pwm-out', 'net')['verdict'] == 'exclusive' and L('pwm-out', 'uart-tx', 'net')['verdict'] == 'exclusive')
    r = L('i2c-sda', 'digital-out', 'net')
    check('pp-1 SAME NET a push-pull output on a TWI line = exclusive (all bus drivers open-drain, 22.2.2 p.216)', r['verdict'] == 'exclusive' and has(r, 'twi-wired-and'))
    r = L('pwm-out', 'pwm-out', 'peripheral')
    check('pp-1 SAME PERIPHERAL two channels of one timer = conditional: compatible as channels, exclusive on the mode (claims timer-channel-split; 15.7 p.107; shared prescaler 17.2 p.147)',
          r['verdict'] == 'conditional' and has(r, 'claims-timer', 'timer-mode') and 'channels' in r['reason'] and 'mode' in r['reason'] and 'A and B' in r['condition'])
    check('pp-1 SAME PERIPHERAL uart-rx + uart-tx = conditional (one baud/frame), two receivers = exclusive (claims: USART0 exclusive); SPI signals are one bus; TWI SDA + SCL compatible; the ADC takes turns',
          L('uart-rx', 'uart-tx', 'peripheral')['verdict'] == 'conditional' and L('uart-rx', 'uart-rx', 'peripheral')['verdict'] == 'exclusive' and L('spi-sck', 'spi-mosi', 'peripheral')['verdict'] == 'conditional'
          and L('i2c-sda', 'i2c-scl', 'peripheral')['verdict'] == 'compatible' and L('analog-in', 'analog-in', 'peripheral')['mode'] == 'time-multiplexed-later')
    d = L('digital-out', 'interrupt-in', 'peripheral')
    check('pp-1 SAME PERIPHERAL kinds on different blocks share nothing: compatible, `applies` says no (different peripherals)', d['verdict'] == 'compatible' and d['rule'] == 'periph.distinct' and d['applies'].startswith('no'))
    r = L('transport', 'digital-out', 'pin')
    check('pp-1 the TRANSPORT reservation: exclusive with a plain output on its pins (lifecycle policy reserved), and its own role is the one uart profile that may sit on the line',
          r['verdict'] == 'exclusive' and has(r, 'lifecycle') and L('transport', 'uart-rx', 'pin')['verdict'] == 'conditional' and L('transport', 'transport', 'pin')['verdict'] == 'exclusive')
    r = L('comparator-in', 'pwm-out', 'pin')
    check('pp-1 an UNSETTLED pair stays undetermined with its reason: the comparator on a pin the chip drives with PWM (PD6: AIN0 + OC0A)', r['verdict'] == 'undetermined' and 'PWM' in r['reason'] and r['common_pins'] == 'PD6')
    check('pp-1 comparator-in is its own kind with the AIN0/AIN1 rules (DIDR1 p.245, Table 14-10 p.99, comparator mux 23.2 p.243); target_compat has no comparator kind',
          L('comparator-in', 'digital-in', 'pin')['verdict'] == 'conditional' and has(L('comparator-in', 'digital-in', 'pin'), 'didr1', 'tbl-d-ain') and has(L('comparator-in', 'analog-in', 'peripheral'), 'ac-mux') and 'comparator-in' not in TC.TASK_KINDS)

    # ---- queries
    check('pp-1 rows(): one kind lists its partners at every scope; a pair + a scope gives one row; unknown kind / scope / verdict are refused by name',
          len(PO.rows(SOC, a='pwm-out')) == 17 * 3 and len(PO.rows(SOC, a='pwm-out', b='digital-out', scope='pin')) == 1 and len(PO.rows(SOC, scope='net')) == 153
          and all(_raises(lambda x=x: PO.rows(SOC, **x)) for x in ({'a': 'zzz'}, {'scope': 'zzz'}, {'verdict': 'zzz'})) and _raises(lambda: PO.table('z80')))

    # ---- the door, on a real falcon.App next to every board route
    import types
    import falcon
    import falcon.testing as ft
    from board.board_endpoints import construct_board_endpoints
    S = types.SimpleNamespace(falconServer=falcon.App(), manager=types.SimpleNamespace(objectTables={}, idList=[]))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            construct_board_endpoints(S)
        c = ft.TestClient(S.falconServer)
        a = c.simulate_get('/api/board/socs/%s/profile-overlap' % SOC).json
        p = c.simulate_get('/api/board/socs/uno/profile-overlap?scope=pin&a=pwm-out&b=digital-out').json
        kinds_ = c.simulate_get('/api/board/socs/%s/profile-overlap?list=kinds' % SOC).json
        rules_ = c.simulate_get('/api/board/socs/%s/profile-overlap?list=rules' % SOC).json
        conds = c.simulate_get('/api/board/socs/%s/profile-overlap?verdict=conditional' % SOC).json
        nope, badk = c.simulate_get('/api/board/socs/z80/profile-overlap'), c.simulate_get('/api/board/socs/%s/profile-overlap?a=zzz' % SOC)
        other = [c.simulate_get('/api/board/socs/%s/register-profile' % SOC).status_code, c.simulate_get('/api/board/arduino-uno-r3/pin-roles').status_code]
        ok = (a['count'] == 459 and a['totals']['rows'] == 459 and p['count'] == 1 and p['rows'][0]['verdict'] == 'exclusive' and kinds_['count'] == 17 and rules_['count'] > 20
              and conds['count'] == tot['verdicts']['conditional'] and nope.status_code == 404 and badk.status_code == 400 and other == [200, 200])
        why = str((a.get('count'), p.get('count'), kinds_.get('count'), conds.get('count'), other))
    except Exception as ex:
        ok, why = False, repr(ex)
    check('pp-1 DOOR: GET /api/board/socs/{soc}/profile-overlap[?a=&b=&scope=&verdict=&list=kinds|rules] ADDS on a real falcon.App beside rp-0\'s register-profile and the /api/board/{board}/... routes and answers; unknown SoC 404, unknown kind 400', ok, why)

    # ---- page, nav, manifest, CLI
    from board.board_page import SEED_BOARD_PAGE_DISPLAYS as P
    pg = next((x for x in P if x['pageRoute'] == 'profile-overlap'), None)
    dfn = json.loads(pg['definition']) if pg else {}
    items = [it for row in dfn.get('rows', []) for it in row['items']]
    names = {it['componentProps']['componentName'] for it in items}
    check('pp-1 PAGE: /display/profile-overlap is a configured page titled "Profile overlap": class-rows-tables only (no raw JSON, no new component), 7 tables each described, no *_json column',
          pg and dfn.get('title') == 'Profile overlap' and names == {'class-rows-table'} and len(items) == 7 and all(it.get('description') for it in items)
          and all('_json' not in it['componentProps']['inputs']['columns'] for it in items), str((names, len(items))))
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    src = open(os.path.join(root, 'polariapps', 'apps_seed.py')).read()
    check('pp-1 NAV: the Hardware home links the page in its own group entry, right after "Pin profiles"',
          "_tgrp('Profile overlap'" in src and "route='/display/profile-overlap'" in src and src.index("_tgrp('Pin profiles'") < src.index("_tgrp('Profile overlap'"))
    man = json.load(open(os.path.join(root, 'board', 'polari-app.json')))
    listed = {f for v in man['files'].values() for f in v}
    new = ['profile_overlap_api', 'profile_overlap_page', 'board_profile_overlap_selftest'] + ['custom/profile_overlap' + s for s in ('', '_cites', '_kinds', '_net', '_periph', '_pin')]
    check('pp-1 MANIFEST: board/polari-app.json lists every new board file and the door class; each listed file exists', all(n in listed for n in new) and 'ProfileOverlapAPI' in man['classes']
          and all(os.path.exists(os.path.join(root, 'board', n + '.py')) for n in new))
    outs = []
    for argv in (['table', 'uno', '--a', 'pwm-out', '--b', 'digital-out', '--scope', 'pin'], ['table', SOC, '--json'], ['kinds', SOC], ['rules', SOC], ['table', 'z80'], ['table', SOC, '--a', 'zzz']):
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc = PO.main(argv)
        outs.append((rc, o.getvalue()))
    j = json.loads(outs[1][1])
    check('pp-1 CLI: `table <soc> [--a --b --scope --verdict] [--json]`, `kinds`, `rules` run; the one-pair text shows verdict, reason and cite; --json is valid (459 rows); an unknown SoC or kind is refused (rc 3)',
          outs[0][0] == 0 and 'exclusive' in outs[0][1] and 'p.89' in outs[0][1] and j['count'] == 459 and outs[2][0] == 0 and 'pwm-out' in outs[2][1] and outs[3][0] == 0 and outs[4][0] == 3 and outs[5][0] == 3, str([o[0] for o in outs]))


def _raises(fn):
    try:
        fn()
    except KeyError:
        return True
    return False
