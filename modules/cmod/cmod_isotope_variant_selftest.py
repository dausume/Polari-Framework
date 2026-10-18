"""cmod_isotope_variant_selftest - iso-0: the isotope variant catalogue (MISSION_PROFILE_SOLVER_PLAN.md section 8): every route of section 8.3 exists,
the three implemented routes have a real non-declared status and MEASURED costs that agree with the atom rows, a wasteful route is listed (never
filtered), an SPI / I2C button route is BLOCKED on the UNO by the missing bench part (named, never silently ok) and becomes ok when the bench gains
the part, the analog comparator is ok on the UNO from its PinFunction rows, an unavailable runtime tier is refused by name, the ESP32-C3 model says
undetermined where its routing is not modelled, status climbs only on a passing run of a Purpose that really uses the route's atoms, every cost field
is measured / estimated / undetermined with a basis, the doors and CLI, the page, the manifest.

    PYTHONPATH=.:modules python3 -m cmod.cmod_isotope_variant_selftest
"""
import contextlib
import io
import json
import os
import sys
from types import SimpleNamespace

PLAN_83 = {'read-button': ['gpio-poll', 'ext-interrupt', 'pin-change-interrupt', 'analog-threshold', 'analog-comparator', 'spi-shift-register', 'i2c-expander'],
           'drive-led': ['gpio-out', 'pwm', 'spi-shift-register', 'i2c-expander', 'transistor-switch'],
           'read-temperature': ['analog-sensor', 'one-wire', 'i2c-sensor', 'spi-sensor'],
           'sense-led-line': ['ext-interrupt', 'pin-change-interrupt', 'gpio-poll', 'analog-read']}
IMPLEMENTED = {'read-button:ext-interrupt': 'uno-button-clock', 'drive-led:gpio-out': 'uno-light', 'read-temperature:analog-sensor': 'uno-sim-rig'}
UNO, C3 = 'arduino-uno-r3', 'esp32-c3'


def _by(rows):
    return {r['name']: r for r in rows}


def isotope_variant_parts(check):
    from cmod.custom import isotope_variants as IV
    from cmod.custom import isotope_variants_eligibility as E
    from cmod.custom import isotope_variants_seeds as S

    def catalogue():
        from cmod import cmod_basis as B
        from cmod.custom.code_interface import LEVEL_ORDER
        from board.custom.target_compat import TASK_KINDS
        jobs, vs = IV.jobs(), IV.variants()
        vn = _by(vs)
        missing = ['%s:%s' % (j, r) for j, rs in PLAN_83.items() for r in rs if '%s:%s' % (j, r) not in vn]
        check('every route of the plan\'s section 8.3 table exists as a variant (%d routes: 7 + 5 + 4 + 4)' % sum(len(r) for r in PLAN_83.values()),
              not missing and all(len([v for v in vs if v['job'] == j]) >= len(rs) for j, rs in PLAN_83.items()), missing)
        check('the variants of each job come in the plan\'s order, and the jobs are read-button, drive-led, sense-led-line, read-temperature, report-state, receive-command',
              [j['name'] for j in jobs] == ['read-button', 'drive-led', 'sense-led-line', 'read-temperature', 'report-state', 'receive-command']
              and [v['route'] for v in vs if v['job'] == 'read-button'] == PLAN_83['read-button'], [v['name'] for v in vs][:8])
        check('variant names are <job>:<route>, unique, every job exists, every route is in the vocabulary',
              len(vn) == len(vs) and all(v['name'] == '%s:%s' % (v['job'], v['route']) and v['route'] in S.ROUTES for v in vs) and {v['job'] for v in vs} <= {j['name'] for j in jobs})
        bad = [(v['name'], p['kind']) for v in vs for p in json.loads(v['profiles_json']) if p['kind'] not in TASK_KINDS]
        check('every pin profile kind is a TASK_KINDS entry (the pp-0 vocabulary), with a role and a count', not bad
              and all(p.get('role') and int(p.get('count', 1)) >= 1 for v in vs for p in json.loads(v['profiles_json'])), bad)
        check('every profile speaks pp-0\'s vocabulary: `role` is the Mission-level role (the button / the LED / the sense line / the transport / the temperature sensor) and `part` names the route\'s own pin',
              all(p['role'] in S.JOB_ROLE.values() and p['role'] == S.JOB_ROLE[v['job']] and p.get('part') for v in vs for p in json.loads(v['profiles_json'])))
        from cmod.custom import pin_profile_mission as PP
        got = {(p['kind'], p['role']) for p in PP.mission_profiles('uno-light-mission')['profiles']}
        mine = {(p['kind'], p['role']) for v in vs for p in json.loads(v['profiles_json'])}
        check('the variants can answer the uno-light-mission\'s derived profiles: every (kind, role) pp-0 derives for it is offered by at least one variant', got <= mine and bool(got), sorted(got - mine))
        badp = [(v['name'], p['kind']) for v in vs for p in json.loads(v['peripherals_json']) if p['kind'] not in S.PERIPHERAL_KINDS]
        check('every claimed on-chip block is of a known kind, each with its reason', not badp and all(p.get('why') for v in vs for p in json.loads(v['peripherals_json'])), badp)
        check('the minimum levels are on the runtime ladder (and the class and the ladder agree); all of today\'s are bare-c',
              B.IsotopeVariant.MINIMUM_LEVELS == LEVEL_ORDER and all(v['minimum_level'] in LEVEL_ORDER for v in vs) and all(v['minimum_level'] == 'bare-c' for v in vs),
              [v['name'] for v in vs if v['minimum_level'] != 'bare-c'])
        check('no variant needs an RTOS: a polled / interrupt superloop can do every route (the tier ladder filters, it does not add routes)',
              not [v['name'] for v in vs if v['minimum_level'] != 'bare-c'])
        check('the classes are registered, one per file, with plain words; the derived status is NOT a field of the row',
              {'AtomJob', 'IsotopeVariant'} <= {c.__name__ for c in B.CMOD_CLASSES} and B.AtomJob.plain_words and B.IsotopeVariant.plain_words
              and 'status' not in B.IsotopeVariant.__init__.__code__.co_varnames and 'on_bench' not in json.dumps(S.VARIANT_SEEDS))
        src = open(os.path.join(os.path.dirname(__file__), '..', '..', 'polariApiServer', 'polariServer.py')).read()
        fi = open(os.path.join(os.path.dirname(__file__), '..', '..', 'polariApiServer', 'feature_imports.py')).read()
        check('both classes are in polariServer\'s class list and the feature imports', 'AtomJob, IsotopeVariant' in src and "'AtomJob', 'IsotopeVariant'" in fi)
        words = [v['title'] + v['plain'] + v['wastefulness_note'] for v in vs] + [j['plain'] for j in jobs]
        check('plain words only: every title / plain / wastefulness note is a sentence with no braces or raw JSON', all(w and '{' not in w and '[' not in w for w in words))

    def seeds():
        from cmod.cmod_seed import CMOD_SEED_PAIRS
        pairs = {n: (c, r) for n, c, r in CMOD_SEED_PAIRS}
        check('the catalogue is code-owned seed pairs: 6 AtomJob + 22 IsotopeVariant rows, all with _converge (a reseed converges the declared fields)',
              len(pairs['AtomJob'][1]) == 6 and len(pairs['IsotopeVariant'][1]) == 22
              and all('_converge' in r for r in pairs['AtomJob'][1] + pairs['IsotopeVariant'][1]))
        built = [pairs[n][0](**{k: v for k, v in r.items() if k != '_converge'}) for n in ('AtomJob', 'IsotopeVariant') for r in pairs[n][1]]
        check('every seed row constructs its class (no stray field)', len(built) == 28)
        mgr = SimpleNamespace(objectTables={'IsotopeVariant': {i: o for i, o in enumerate(o for o in built if hasattr(o, 'route'))}, 'AtomJob': {}})
        check('rows read back from a manager serve the same catalogue as the seeds (the live rows are the truth when present)',
              [v['name'] for v in IV.variants(mgr)] == [v['name'] for v in IV.variants()])

    def implemented():
        vs = _by(IV.variants())
        cmod_rows = _by(__import__('cmod.cmod_seed', fromlist=['x']).CMOD_SEED_PAIRS and [r for n, c, rows in __import__('cmod.cmod_seed', fromlist=['x']).CMOD_SEED_PAIRS if n == 'CFunctionAtom' for r in rows])
        for name, cfg in IMPLEMENTED.items():
            st = IV.status(vs[name])
            check('%s: status is DERIVED and real (not declared): %s, built in %s' % (name, st['status'], cfg), st['status'] == 'compiles' and cfg in st['why'], st)
            c = IV.costs(vs[name])
            atoms = json.loads(vs[name]['implemented_by_json'])['atoms']
            rows = [cmod_rows[a] for a in atoms]
            want = sum(r['text_bytes'] or r['text_bytes_noinline'] for r in rows)
            check('%s: flash is MEASURED and equals the sum of the atom rows\' own text bytes (%d B)' % (name, want),
                  c['flash_bytes']['kind'] == 'measured' and c['flash_bytes']['value'] == want and all(r['measured_in'] in c['flash_bytes']['basis'] for r in rows), c['flash_bytes'])
            check('%s: stack and RAM are measured too, with the basis said' % name,
                  c['stack_bytes']['kind'] == 'measured' and c['stack_bytes']['value'] == max(r['stack_bytes'] for r in rows) and c['ram_bytes']['kind'] == 'measured' and c['ram_bytes']['basis'], c['ram_bytes'])
            check('%s: the on-chip blocks are cross-checked against the registers the atoms touch (measured)' % name, c['peripherals']['kind'] == 'measured', c['peripherals'])
        ib = IV.costs(vs['read-button:ext-interrupt'])
        check('the INT0 button costs 210 B of flash (hal_button_init 24 + hal_presses 16 + the INT0 ISR 170, measured in uno-button-clock) and 8 B of RAM',
              ib['flash_bytes']['value'] == 210 and ib['ram_bytes']['value'] == 8, (ib['flash_bytes']['value'], ib['ram_bytes']['value']))
        pwm = IV.status(vs['drive-led:pwm'])
        check('the PWM route (hal_pwm_init + hal_pwm_apply, in the sim-rig build) also compiles - and no Purpose proves it, so nothing lifts it',
              pwm['status'] == 'compiles' and not pwm['proof_purposes_used'], pwm)
        check('the sense route (INT1) and the serial routes compile',
              all(IV.status(vs[n])['status'] == 'compiles' for n in ('sense-led-line:ext-interrupt', 'report-state:uart-tx', 'receive-command:uart-rx-interrupt')))
        decl = [n for n, v in vs.items() if not json.loads(v['implemented_by_json']).get('atoms')]
        check('every route with no atom is `declared`, with the reason in words (never optimistic)',
              all(IV.status(vs[n])['status'] == 'declared' and IV.status(vs[n])['why'] for n in decl) and len(decl) == 11, len(decl))   # fgm-5b: -2 more (the polled and the pin-change sense of the LED line have templates now); fgm-5a: -2 (the PCINT and analog-threshold buttons have templates now)
        ts = IV.status(vs['drive-led:transistor-switch'])
        check('the transistor route shares the plain output atoms\' C but is not wired anywhere: declared, and its estimated size is that C\'s measured 16 B, said so',
              ts['status'] == 'declared' and 'drive-led:gpio-out' in ts['why'] and IV.costs(vs['drive-led:transistor-switch'])['flash_bytes']['value'] == IV.costs(vs['drive-led:gpio-out'])['flash_bytes']['value'] == 16)
        broken = dict(vs['drive-led:gpio-out'], implemented_by_json=json.dumps({'atoms': ['uno:hal.hal_led_init', 'uno:hal.no_such_atom'], 'config': 'uno-light'}))
        check('an implemented_by that names a missing atom drops to declared and NAMES it (a renamed atom shows up)',
              IV.status(broken)['status'] == 'declared' and 'no_such_atom' in IV.status(broken)['why'])
        ja = {j['name']: IV.job_atoms(j) for j in IV.jobs()}
        check('the job\'s atoms are checked against the manifests and also DERIVED from the pin macro they declare (read-button: BUTTON_PIN)',
              not any(a['missing'] for a in ja.values()) and 'uno:hal.hal_button_init' in ja['read-button']['atoms'] and 'uno:hal.hal_presses' in ja['read-button']['atoms']
              and 'uno:hal.hal_sense_read' not in ja['read-button']['atoms'])
        check('read-button finds hal_button_init and hal_presses by BUTTON_PIN; drive-led finds hal_led by LED_PIN; sense-led-line finds hal_sense_init by SENSE_PIN',
              {'uno:hal.hal_button_init', 'uno:hal.hal_presses'} <= set(ja['read-button']['atoms']) and 'uno:hal.hal_led' in ja['drive-led']['atoms']
              and 'uno:hal.hal_sense_init' in ja['sense-led-line']['atoms'], {k: v['atoms'] for k, v in ja.items()})

    def costs_honest():
        vs = IV.variants()
        bad = []
        for v in vs:
            c = IV.costs(v)
            for k in IV.COST_KEYS:
                e = c.get(k)
                if not e or e['kind'] not in ('measured', 'estimated', 'undetermined') or not e.get('basis') or (e['kind'] == 'undetermined') != (e['value'] is None):
                    bad.append((v['name'], k, e))
        check('every cost field of every variant is measured / estimated / undetermined, carries its basis, and a value only when it is not undetermined', not bad, bad[:3])
        meas = {v['name'] for v in vs if any(IV.costs(v)[k]['kind'] == 'measured' for k in ('flash_bytes', 'ram_bytes'))}
        check('a size is `measured` only on the routes that have atoms in a build (the 11 implemented ones; fgm-5a: + PCINT and analog-threshold buttons; fgm-5b: + the polled and PCINT sense) - estimates never pose as measurements',
              meas == {n for n, v in _by(vs).items() if json.loads(v['implemented_by_json']).get('atoms')} and len(meas) == 11, sorted(meas))
        unb = [v['name'] for v in vs if not json.loads(v['implemented_by_json']).get('atoms') and IV.costs(v)['flash_bytes']['kind'] == 'undetermined']
        check('the routes with no build have flash undetermined (or a labelled lower bound / borrowed number), never a bare guess', len(unb) >= 9 and all(
            IV.costs(v)['flash_bytes']['kind'] in ('undetermined', 'estimated') and ('LOWER BOUND' in IV.costs(v)['flash_bytes']['basis'] or 'same C' in IV.costs(v)['flash_bytes']['basis'] or IV.costs(v)['flash_bytes']['kind'] == 'undetermined')
            for v in vs if not json.loads(v['implemented_by_json']).get('atoms')))
        ow = IV.costs(_by(vs)['read-temperature:one-wire'])
        check('a 1-Wire route counts ONE pin (its read and send profiles are the same pin)', ow['pins']['value'] == 1, ow['pins'])

    def bench_parts():
        vs = _by(IV.variants())
        pb = lambda v: {p['class']: p['on_bench'] for p in IV.parts_of(vs[v])}   # noqa: E731
        sp = pb('read-button:spi-shift-register')
        check('the SPI shift-register button needs a 74HC165-class part that is NOT on the bench; the pushbutton is', sp['74HC165-class parallel-in shift register'] is False and sp['pushbutton'] is True, sp)
        check('the I2C expander button needs a PCF8574-class part that is NOT on the bench; the 4.7 kohm pull-up IS (the kit\'s variant list has it)',
              pb('read-button:i2c-expander')['PCF8574-class I2C I/O expander'] is False and pb('read-button:i2c-expander')['I2C pull-up resistors (4.7 kohm)'] is True)
        check('the TMP36 is on the bench, the DS18B20 / TMP102 / MAX31855 classes are not',
              pb('read-temperature:analog-sensor') == {'TMP36 analog temperature sensor': True}
              and not any(v for k, v in {**pb('read-temperature:one-wire'), **pb('read-temperature:i2c-sensor'), **pb('read-temperature:spi-sensor')}.items() if 'class' in k and v is not False and 'resistor' not in k))
        check('the transistor route finds both a transistor and a MOSFET in the kit', pb('drive-led:transistor-switch')['transistor or MOSFET'] is True)
        wrong = IV.part_on_bench({'class': 'x', 'kit_keys': ['resistors'], 'spec': {'ohms': 999}})
        check('a spec the kit\'s variant list lacks is False (the kit has resistors but no 999 ohm one), not a silent True', wrong['on_bench'] is False, wrong)
        check('a part named by nothing in the kit is False with the count of rows searched; the derivation reads the KitPart rows, not a typed flag',
              'none of the 25 KitPart rows' in IV.part_on_bench({'class': 'y', 'kit_keys': [], 'terms': ['zzz']})['why'])

    def eligibility():
        uno, vs = E.context(UNO), _by(IV.variants())
        e = lambda n, ctx=uno, **kw: E.eligible(vs[n], ctx, **kw)   # noqa: E731
        for n, part in (('read-button:spi-shift-register', '74HC165'), ('read-button:i2c-expander', 'PCF8574'), ('drive-led:spi-shift-register', '74HC595'),
                        ('drive-led:i2c-expander', 'PCF8574'), ('read-temperature:one-wire', 'DS18B20')):
            r = e(n)
            check('%s on the UNO is BLOCKED by the missing bench part, named (%s)' % (n, part), r['state'] == 'blocked' and part in r['summary'] and any(b.startswith('part:') for b in r['blocked_by']), r['summary'][:160])
        check('the SPI / I2C routes\' pins and blocks exist on the UNO (SPI, TWI Peripheral rows, MOSI/SCK/SDA/SCL functions): only the PART blocks them',
              all(c['state'] == 'ok' for c in e('read-button:spi-shift-register')['checks'] if c['check'] in ('pin', 'peripheral', 'runtime'))
              and all(c['state'] == 'ok' for c in e('read-button:i2c-expander')['checks'] if c['check'] in ('pin', 'peripheral', 'runtime')))
        ext_kit = uno['kit'] + [{'name': 'kit:74hc165', 'title': '74HC165', 'what_it_is': 'a parallel-in shift register', 'interface_kind': '', 'connects_to': '', 'driver_needed': ''}]
        check('give the bench a shift-register row and the SPI button route stops being blocked (undetermined: a row only mentions it) - the verdict reads the bench',
              E.eligible(vs['read-button:spi-shift-register'], dict(uno, kit=ext_kit))['state'] == 'undetermined')
        ext_kit2 = uno['kit'] + [{'name': 'arduino-starter-kit:74hc165', 'title': '74HC165', 'what_it_is': '', 'interface_kind': '', 'connects_to': '', 'driver_needed': '', 'kit_quantity': '2', 'variants_json': '[]'}]
        v2 = dict(vs['read-button:spi-shift-register'], parts_json=json.dumps([dict(p, kit_keys=['74hc165']) if '74HC165' in p['class'] else p for p in json.loads(vs['read-button:spi-shift-register']['parts_json'])]))
        check('...and with a KitPart row the route names, it is ok', E.eligible(v2, dict(uno, kit=ext_kit2))['state'] == 'ok', E.eligible(v2, dict(uno, kit=ext_kit2))['summary'][:200])
        cmp_ = e('read-button:analog-comparator')
        check('the analog comparator is OK on the UNO: AIN0 and AIN1 exist as PinFunction rows, the AC block as a Peripheral row, the parts are on the bench',
              cmp_['state'] == 'ok' and any('AIN0' in c['why'] and 'AIN1' in c['why'] for c in cmp_['checks'] if c['check'] == 'pin'), cmp_['summary'])
        check('the direct routes are ok on the UNO: gpio poll, INT0/INT1, PCINT, analog threshold, GPIO out, PWM, transistor, TMP36',
              all(e(n)['state'] == 'ok' for n in ('read-button:gpio-poll', 'read-button:ext-interrupt', 'read-button:pin-change-interrupt', 'read-button:analog-threshold',
                                                 'drive-led:gpio-out', 'drive-led:pwm', 'drive-led:transistor-switch', 'read-temperature:analog-sensor')))
        zep = e('drive-led:gpio-out', tier='zephyr')
        check('the zephyr tier is UNAVAILABLE on the UNO, by name, cited to Zephyr v4.4.2\'s arch/ listing (no AVR architecture)',
              zep['state'] == 'blocked' and 'zephyr' in zep['summary'] and 'no AVR architecture' in zep['summary'] and 'arch/' in zep['summary'], zep['summary'][:300])
        check('freertos and esp-idf are refused on the UNO by their own reasons (2 KB SRAM; Espressif SoCs only); bare-c is ok',
              'SRAM' in e('drive-led:gpio-out', tier='freertos')['summary'] and 'Espressif' in e('drive-led:gpio-out', tier='esp-idf')['summary']
              and e('drive-led:gpio-out', tier='bare-c')['state'] == 'ok')
        check('an unknown tier is refused by name', e('drive-led:gpio-out', tier='linux')['state'] == 'blocked' and 'linux' in e('drive-led:gpio-out', tier='linux')['summary'])
        c3 = E.context(C3)
        check('the ESP32-C3: GPIO out, GPIO poll and the analog routes are ok from its GPIO / ADC functions and devicetree blocks (bare-c rides inside its FreeRTOS tier)',
              all(E.eligible(vs[n], c3)['state'] == 'ok' for n in ('drive-led:gpio-out', 'read-button:gpio-poll', 'read-button:analog-threshold', 'read-temperature:analog-sensor')))
        ex = E.eligible(vs['read-button:ext-interrupt'], c3)
        check('the C3 INT0/INT1 route is OK from its PinFunction rows (c3pf: every pad has GPIO_INT - TRM Register 5.14, datasheet §4.1.3.1 p.36), through the GPIO-interrupt Peripheral row',
              ex['state'] == 'ok' and any(c['check'] == 'pin' and c['state'] == 'ok' for c in ex['checks']) and any(c['check'] == 'peripheral' and c['subject'] == 'exint' and c['state'] == 'ok' and 'esp32c3:GPIO_INT' in c['why'] for c in ex['checks']), [c['why'][:80] for c in ex['checks']])
        cc = E.eligible(vs['read-button:analog-comparator'], c3)
        check('the C3 comparator route is BLOCKED by name (c3pf: the datasheet\'s own peripheral list, p.4 and §4.2 pp.46-50, names no analog comparator) - not an absence from a devicetree list',
              cc['state'] == 'blocked' and cc['blocked_by'] == ['peripheral:comparator'] and 'p.4' in cc['summary'], cc['summary'][:200])
        check('the C3 still lacks the shift register on the bench (blocked by the part, same as the UNO); zephyr is available on the C3',
              E.eligible(vs['read-button:spi-shift-register'], c3)['state'] == 'blocked'
              and [c for c in E.eligible(vs['drive-led:gpio-out'], c3, tier='zephyr')['checks'] if c['check'] == 'runtime'][0]['state'] == 'ok')
        check('unknown boards have no context', E.context('no-such-board') is None and UNO in E.boards() and C3 in E.boards())

    def wasteful_kept():
        vs = _by(IV.variants())
        wasteful = ('read-button:analog-threshold', 'read-button:analog-comparator', 'read-button:spi-shift-register', 'read-button:i2c-expander', 'drive-led:spi-shift-register',
                    'drive-led:i2c-expander', 'sense-led-line:analog-read')
        check('the wasteful routes are PRESENT in the catalogue and in the served rows (an SPI-routed button is a valid candidate, scored worse - never filtered)',
              all(n in vs for n in wasteful) and all(n in {d['name'] for d in (IV.variant_dict(v, E.context(UNO)) for v in IV.variants())} for n in wasteful))
        check('each wasteful route says in plain words when it is a poor default AND when it is the only one left',
              all(vs[n]['wastefulness_note'] and ('only' in vs[n]['wastefulness_note'] or 'left' in vs[n]['wastefulness_note'] or 'fallback' in vs[n]['wastefulness_note'] or 'Right only' in vs[n]['wastefulness_note'])
                  and ('wasteful' in vs[n]['wastefulness_note'].lower() or 'Wasteful' in vs[n]['wastefulness_note']) for n in wasteful),
              [n for n in wasteful if 'asteful' not in vs[n]['wastefulness_note']])
        sp = IV.variant_dict(vs['read-button:spi-shift-register'])
        gp = IV.variant_dict(vs['read-button:gpio-poll'])
        check('the SPI button visibly costs more than the GPIO poll: more pins, more blocks, more parts (the numbers the engine will score)',
              sp['costs']['pins']['value'] > gp['costs']['pins']['value'] and sp['costs']['peripherals']['value'] > gp['costs']['peripherals']['value']
              and sp['costs']['parts']['value'] > gp['costs']['parts']['value'], (sp['costs']['pins']['value'], gp['costs']['pins']['value']))

    def proof_ladder():
        from cmod.custom.selftest_purpose import _manager
        mgr = _manager()
        vs = _by(IV.variants())
        btn = vs['read-button:ext-interrupt']

        def run(scenario, outcome, mode='digital-twin', at='2026-10-18T10:00:00', name=None):
            r = SimpleNamespace(name=name or 'run-%s-%s' % (scenario, at), scenario=scenario, outcome=outcome, ran_at=at, kind='measured',
                                repro_json=json.dumps({'mode': mode}), verdict_words=outcome)
            mgr.objectTables.setdefault('ScenarioRun', {})[len(mgr.objectTables.get('ScenarioRun', {})) + 1] = r
        check('with no live manager the status stops at `compiles` and says there is no run to read', IV.status(btn)['status'] == 'compiles' and 'no live instance' in IV.status(btn)['why'])
        check('with a manager but no ScenarioRun yet, still `compiles`, saying no passing run yet', IV.status(btn, mgr)['status'] == 'compiles' and 'no passing ScenarioRun' in IV.status(btn, mgr)['why'], IV.status(btn, mgr))
        run('light-from-button-acceptance', 'failed')
        check('a FAILED run lifts nothing', IV.status(btn, mgr)['status'] == 'compiles')
        run('light-from-button-acceptance', 'passed', at='2026-10-18T11:00:00')
        st = IV.status(btn, mgr)
        check('a passing twin run of a Purpose whose graph holds the route\'s atoms lifts it to proven-on-twin, naming the run',
              st['status'] == 'proven-on-twin' and 'ScenarioRun' in st['proof'] and st['proof_purposes_used'] and set(st['proof_purposes_used']) <= set(json.loads(btn['implemented_by_json'])['proof_purposes']), st)
        run('light-from-button-acceptance', 'passed', mode='hardware', at='2026-10-18T12:00:00')
        check('a later passing HARDWARE run lifts it to proven-on-hardware', IV.status(btn, mgr)['status'] == 'proven-on-hardware')
        run('light-from-button-acceptance', 'failed', at='2026-10-18T13:00:00')
        check('a newer failing run takes the proof away again (no stale pass carried forward)', IV.status(btn, mgr)['status'] == 'compiles')
        run('temp-sensor-to-os-acceptance', 'passed', at='2026-10-18T14:00:00')
        wrong = dict(btn, implemented_by_json=json.dumps(dict(json.loads(btn['implemented_by_json']), proof_purposes=['temp-sensor-to-os'])))
        check('a passing run of a Purpose whose graph does NOT hold the route\'s atoms lifts nothing (the temperature rig does not exercise the button)', IV.status(wrong, mgr)['status'] == 'compiles')
        check('the temperature route IS lifted by that same run (its graph holds hal_adc_read)', IV.status(vs['read-temperature:analog-sensor'], mgr)['status'] == 'proven-on-twin')
        check('an unimplemented route is never lifted by any run', IV.status(vs['read-button:spi-shift-register'], mgr)['status'] == 'declared')

    def doors_and_cli():
        import falcon
        from falcon import testing
        from cmod.cmod_api import CModAPI
        from cmod.cmod_capability_api import CapabilityAPI
        from cmod.cmod_firmware_api import FirmwareAPI
        from cmod.cmod_mission_api import MissionAPI
        from cmod.cmod_isotope_api import IsotopeVariantAPI
        from cmod.custom.selftest_purpose import _manager
        mgr = _manager()
        app = falcon.App()
        ps = SimpleNamespace(falconServer=app, manager=mgr, idList=[])
        for api in (CModAPI, FirmwareAPI, CapabilityAPI, MissionAPI, IsotopeVariantAPI):
            api(polServer=ps, manager=mgr)     # a route clash would raise right here (a {head}/{atom} route once crash-looped the backend)
        c = testing.TestClient(app)
        r = c.simulate_get('/api/atom-jobs')
        check('GET /api/atom-jobs: six jobs on ONE real falcon.App beside every other cmod door (no route-template conflict), each with atoms and counts',
              r.status_code == 200 and [j['name'] for j in r.json['rows']][:4] == ['read-button', 'drive-led', 'sense-led-line', 'read-temperature']
              and r.json['rows'][0]['variant_count'] == 7 and r.json['rows'][0]['implemented_count'] == 3, r.text[:200])
        r = c.simulate_get('/api/atom-jobs/read-button/variants', params={'board': UNO})
        rows = {x['name']: x for x in r.json['rows']} if r.status_code == 200 else {}
        check('GET /api/atom-jobs/read-button/variants?board=arduino-uno-r3: 7 variants, each with status, costs, parts and its eligibility on the UNO',
              r.status_code == 200 and len(rows) == 7 and all('eligibility' in x and x['eligible'] in ('ok', 'blocked', 'undetermined') and x['status'] for x in rows.values())
              and rows['read-button:spi-shift-register']['eligible'] == 'blocked' and rows['read-button:analog-comparator']['eligible'] == 'ok'
              and rows['read-button:ext-interrupt']['status'] == 'compiles', r.text[:200])
        r = c.simulate_get('/api/atom-jobs/read-button/variants')
        check('without ?board= the variants come with no eligibility (the catalogue alone)', r.status_code == 200 and all('eligibility' not in x for x in r.json['rows']))
        r = c.simulate_get('/api/atom-jobs/read-button/variants', params={'board': UNO, 'tier': 'zephyr'})
        check('?tier=zephyr asks for a runtime tier: every UNO row is blocked by the unavailable tier, named', all(x['eligible'] == 'blocked' and 'no AVR architecture' in x['eligible_why'] for x in r.json['rows']))
        check('an unknown job is 404 and an unknown board is 422, each naming what is known',
              c.simulate_get('/api/atom-jobs/nope/variants').status_code == 404 and c.simulate_get('/api/atom-jobs/read-button/variants', params={'board': 'nope'}).status_code == 422
              and 'arduino-uno-r3' in c.simulate_get('/api/atom-jobs/read-button/variants', params={'board': 'nope'}).json['error'])
        r = c.simulate_get('/api/atom-variants', params={'board': C3})
        check('GET /api/atom-variants?board=esp32-c3: the flat table of all 22 variants for the page', r.status_code == 200 and len(r.json['rows']) == 22 and r.json['board'] == C3)
        r = c.simulate_get('/api/cmod/atoms/uno:hal.hal_led/isotopes')
        check('the older isotope door of the same module still routes (no shadowing)', r.status_code in (200, 404, 422), r.status_code)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = IV.main(['variants', 'read-button', '--board', UNO])
        out = buf.getvalue()
        check('CLI `variants read-button --board arduino-uno-r3`: prints every variant with status, costs, parts and the UNO verdict',
              rc == 0 and 'read-button:spi-shift-register' in out and 'blocked' in out and 'compiles' in out and 'when:' in out, out[:200])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = IV.main(['variants', 'drive-led', '--board', C3, '--json'])
        check('CLI --json prints the same rows as JSON', rc == 0 and len(json.loads(buf.getvalue())['rows']) == 5)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc1 = IV.main(['jobs'])
            rc2 = IV.main(['variants', 'nope'])
        check('CLI `jobs` lists the jobs; an unknown job is refused with the known names', rc1 == 0 and 'read-button' in buf.getvalue() and rc2 == 3 and '[REFUSED]' in buf.getvalue())

    def page_and_manifest():
        from cmod.cmod_page import SEED_CMOD_PAGE_DISPLAYS as P
        pg = next((p for p in P if p['pageRoute'] == 'isotope-variants'), None)
        d = json.loads(pg['definition']) if pg else {'rows': []}
        items = [i for r in d['rows'] for i in r['items']] if pg else []
        check('the Isotope variants page exists: 3 configured tables over the doors (no raw JSON panel, no custom component)',
              pg is not None and len(items) == 3 and all(i['componentProps']['componentName'] == 'class-rows-table' for i in items)
              and [i['componentProps']['inputs']['dataPath'] for i in items][1:] == ['/api/atom-variants?board=%s' % UNO, '/api/atom-variants?board=%s' % C3])
        from cmod.cmod_isotope_page import _COLS
        row = IV.variant_dict(IV.variants()[0], E.context(UNO))
        check('every column the page asks for is a field of the served row', all(col in row for col in _COLS.split(',')), [c for c in _COLS.split(',') if c not in row])
        jrow = IV.job_dict(IV.jobs()[0])
        cols = items[0]['componentProps']['inputs']['columns'].split(',') if items else []
        check('...and of the served job row; every table has a description saying what one row is', all(c in jrow for c in cols) and all(i['description'] and 'One row' in i['description'] for i in items))
        m = json.load(open(os.path.join(os.path.dirname(__file__), 'polari-app.json')))
        f = m['files']
        want = {'objects': ['objects/cmod/AtomJob', 'objects/cmod/IsotopeVariant'], 'api': ['cmod_isotope_api'], 'page': ['cmod_isotope_page'], 'selftests': ['cmod_isotope_variant_selftest'],
                'custom': ['custom/isotope_variants', 'custom/isotope_variants_doors', 'custom/isotope_variants_eligibility', 'custom/isotope_variants_seeds']}
        got = {}
        for key, names in want.items():
            have = f.get(key if key != 'objects' else 'objects', [])
            got[key] = [n for n in names if n not in have]
        check('polari-app.json lists every new file (objects, api, page, selftests, custom)', not any(got.values()), got)
        on_disk = [n for n in sum(want.values(), []) if os.path.isfile(os.path.join(os.path.dirname(__file__), n + '.py'))]
        check('...and each listed file exists on disk', len(on_disk) == sum(len(v) for v in want.values()))
        from polariapps.apps_seed import SEED_POLARI_APPS
        check('the Hardware app nav has its own "Isotope variants" group opening the page', 'Isotope variants' in json.dumps(SEED_POLARI_APPS) and '/display/isotope-variants' in json.dumps(SEED_POLARI_APPS))

    return (catalogue, seeds, implemented, costs_honest, bench_parts, eligibility, wasteful_kept, proof_ladder, doors_and_cli, page_and_manifest)


def main():
    passed = total = 0
    failures = []

    def check(label, cond, detail=None):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
        else:
            failures.append(label)
        print(('PASS ' if cond else 'FAIL ') + label + ('' if cond or detail is None else '   <- %s' % (str(detail)[:300],)))
    for part in isotope_variant_parts(check):
        print('-- %s' % part.__name__)
        part()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
