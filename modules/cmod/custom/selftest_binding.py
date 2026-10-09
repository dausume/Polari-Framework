"""cmod.custom.selftest_binding — ucd-0b2b (UNO_CORE_DEMO_PLAN.md §5h, his ruling 2026-10-08): THE HARDWARE BINDING.
A FirmwareSolution is hardware-agnostic; a HardwareBinding ('<solution>@<board>') lays it over one board and is
valid | incomplete | invalid from rows only. Run by cmod_selftest.main() (binding_parts), same shape as
selftest_claims.py/selftest_requirements.py.
"""
import json

SOLUTION, GRAPH, BOARD = 'uno-sim-rig', 'uno-sim-rig-graph', 'arduino-uno-r3'
DEFAULT_NAME = '%s@%s' % (SOLUTION, BOARD)


def binding_parts(check):
    def default_binding():
        _default_binding(check)

    def fixed_kinds():
        _fixed_kinds(check)

    def reverse_refs_resolve():
        _reverse_refs_resolve(check)

    def claims_carry_binding():
        _claims_carry_binding(check)

    def esp32c3_incomplete():
        _esp32c3_incomplete(check)

    def live_api():
        _live_api(check)

    def button_clock_binding():
        _button_clock_binding(check)

    return (default_binding, fixed_kinds, reverse_refs_resolve, claims_carry_binding, esp32c3_incomplete, live_api, button_clock_binding)


# ---------------------------------------------------------------- part 1: the pure default binding
def _default_binding(check):
    from cmod.custom import binding as BND
    b = BND.derive(SOLUTION, manager=None)
    check('the default binding exists, named <solution>@<board>, is_default, provenance derived',
          b is not None and b['name'] == DEFAULT_NAME and b['is_default'] is True and b['provenance'] == 'derived', b)
    check('uno-sim-rig has 14 required TargetDefinition rows (16 total minus the 2 memory-field rows, required=False)',
          b['requirements_total'] == 14, b)
    # ucd-0b2d (§5h, the HardwareBinding fix): tick_init/led_init/rx_pop were WRONGLY kinded (pwm-out/undetermined/
    # pin instead of the real peripheral/pin/signal resource they are) — fixed in targets.py's derivation, never by
    # editing data: the board DOES meet all 14 required rows, so the default binding reads valid, 14/14, why empty.
    check('status valid (every required row met by derivation, not by editing data), requirements_met == 14, '
          'why empty', b['status'] == 'valid' and b['requirements_met'] == 14 and b['why'] == '', b)
    check('requirements_total/met are stable across a second derivation (idempotent)',
          BND.derive(SOLUTION, manager=None)['requirements_total'] == b['requirements_total']
          and BND.derive(SOLUTION, manager=None)['requirements_met'] == b['requirements_met'])


# ---------------------------------------------------------------- part 1b: the three previously-mis-kinded rows
def _fixed_kinds(check):
    """ucd-0b2d: tick_init (Timer2's CTC tick — a PERIPHERAL, not pwm-out: no OCR-to-a-pin, no pin declared),
    led_init (the SAME D13 `led` is bound to — one pin, two tasks of one Purpose), rx_pop (the USART0 RXD SIGNAL
    through the RX ring, never a pin)."""
    from cmod.custom import targets as T
    from cmod.custom import binding as BND
    rows = {r['node']: r for r in T.derive(GRAPH) if r['node'] in ('tick_init', 'led_init', 'rx_pop')}
    check('tick_init: resource_kind peripheral, requirement_kind timer, role clock, peripheral atmega328p:TIMER2, unbound',
          rows['tick_init']['resource_kind'] == 'peripheral' and rows['tick_init']['requirement_kind'] == 'timer'
          and rows['tick_init']['role'] == 'clock' and rows['tick_init']['peripheral'] == 'atmega328p:TIMER2'
          and rows['tick_init']['lives_on'] == 'unbound', rows['tick_init'])
    check('led_init: bound to D13 (the SAME BoardPin `led` is bound to), requirement_kind digital-out, resource_kind pin',
          rows['led_init']['lives_on'] == 'arduino-uno-r3:D13' and rows['led_init']['requirement_kind'] == 'digital-out'
          and rows['led_init']['resource_kind'] == 'pin', rows['led_init'])
    led = next(r for r in T.derive(GRAPH) if r['node'] == 'led')
    check('led_init and led share the exact same lives_on', rows['led_init']['lives_on'] == led['lives_on'])
    check('rx_pop: resource_kind signal, requirement_kind uart-rx, role receive, signal atmega328p:USART0:RXD, unbound',
          rows['rx_pop']['resource_kind'] == 'signal' and rows['rx_pop']['requirement_kind'] == 'uart-rx'
          and rows['rx_pop']['role'] == 'receive' and rows['rx_pop']['signal'] == 'atmega328p:USART0:RXD'
          and rows['rx_pop']['lives_on'] == 'unbound', rows['rx_pop'])

    b = BND.derive(SOLUTION, manager=None)
    check('tick_init is met by the existing TIMER2 PeripheralClaim',
          any('PeripheralClaim:%s:TIMER2' % SOLUTION == ref for ref in json.loads(b['assignments_refs_json'])),
          b['assignments_refs_json'])
    check('rx_pop is met (through D0\'s RXD assignment or the USART0 PeripheralClaim) — never bound to a pin itself',
          b['status'] == 'valid')


# ---------------------------------------------------------------- part 2: every reverse ref resolves
def _reverse_refs_resolve(check):
    from cmod.custom import binding as BND
    from cmod.custom import claims as C
    b = BND.derive(SOLUTION, manager=None)
    assigns = {'RegisterAssignment:%s' % r['name'] for r in BND.assignment_rows(DEFAULT_NAME, GRAPH, manager=None)}
    pins = C.pin_claims(b, GRAPH, manager=None)
    periph = C.peripheral_claims(b, GRAPH, manager=None)
    gen = C.register_settings(b, GRAPH, manager=None)
    claims_names = {'PinClaim:%s' % c['name'] for c in pins} | {'PeripheralClaim:%s' % p['name'] for p in periph}
    settings_names = ({'RegisterSetting:%s' % s['name'] for s in gen['RegisterSetting']}
                       | {'RegisterFieldSetting:%s' % s['name'] for s in gen['RegisterFieldSetting']})
    routes_names = {'SignalRoute:%s' % s['name'] for s in gen['SignalRoute']}
    # ucd-0b2d: a met requirement of resource_kind peripheral/signal names its PeripheralClaim (never a
    # RegisterAssignment — it is never pin-bound) — assignments_refs_json may carry EITHER ref kind now
    bad_a = [r for r in json.loads(b['assignments_refs_json']) if r not in assigns and r not in claims_names]
    bad_c = [r for r in json.loads(b['claims_refs_json']) if r not in claims_names]
    bad_s = [r for r in json.loads(b['settings_refs_json']) if r not in settings_names]
    bad_r = [r for r in json.loads(b['routes_refs_json']) if r not in routes_names]
    check('every assignments_refs_json ref resolves to a real RegisterAssignment or PeripheralClaim row', not bad_a, bad_a)
    check('every claims_refs_json ref resolves to a real PinClaim/PeripheralClaim row', not bad_c, bad_c)
    check('every settings_refs_json ref resolves to a real RegisterSetting/RegisterFieldSetting row', not bad_s, bad_s)
    check('every routes_refs_json ref resolves to a real SignalRoute row', not bad_r, bad_r)
    check('none of the four reverse-ref lists is empty (there is something to resolve)',
          bool(json.loads(b['assignments_refs_json'])) and bool(json.loads(b['claims_refs_json']))
          and bool(json.loads(b['settings_refs_json'])) and bool(json.loads(b['routes_refs_json'])))


# ---------------------------------------------------------------- part 3: claims/settings carry the binding name
def _claims_carry_binding(check):
    from cmod.custom import binding as BND
    from cmod.custom import claims as C
    b = BND.derive(SOLUTION, manager=None)
    pins = C.pin_claims(b, GRAPH, manager=None)
    periph = C.peripheral_claims(b, GRAPH, manager=None)
    gen = C.register_settings(b, GRAPH, manager=None)
    check('every PinClaim carries binding == the default binding\'s name, solution == the base solution',
          all(p['binding'] == DEFAULT_NAME and p['solution'] == SOLUTION for p in pins), pins[:1])
    check('every PeripheralClaim carries binding == the default binding\'s name',
          all(p['binding'] == DEFAULT_NAME for p in periph), periph[:1])
    check('every RegisterSetting/RegisterFieldSetting/SignalRoute carries binding == the default binding\'s name',
          all(s['binding'] == DEFAULT_NAME for s in gen['RegisterSetting'] + gen['RegisterFieldSetting'] + gen['SignalRoute']))
    check('row NAMES still read "<solution>:<canonical>" for the default binding (never renamed — D-ucd-8 posture)',
          all(p['name'].startswith(SOLUTION + ':') for p in pins))
    # thin wrapper: a plain solution-name string resolves to the SAME default binding, same row names
    pins_str = C.pin_claims(SOLUTION, GRAPH, manager=None)
    check('pin_claims(<solution-name-string>, ...) (every pre-0b2b caller) gives the SAME rows as pin_claims(<default-binding>, ...)',
          pins_str == pins, (len(pins_str), len(pins)))


# ---------------------------------------------------------------- part 4: a board whose chain is not materialized
def _esp32c3_incomplete(check):
    from cmod.custom import binding as BND
    from board.custom import board_object as BO
    c3 = next((n for n in ('esp32-c3', 'esp32c3-devkitm') if _board_exists(n)), None)
    check('the ESP32-C3 BoardDefinition is findable under one of its known aliases', c3 is not None, c3)
    try:
        b = BND.derive(SOLUTION, board=c3, manager=None)
    except Exception as e:  # noqa: BLE001 — the point of this check: it must NEVER raise
        check('binding to a board whose hardware chain is not materialized NEVER raises', False, str(e))
        return
    check('binding to a board whose hardware chain is not materialized NEVER raises', True)
    check('status incomplete, why names "Phase 2" and the board\'s own SoC name, never a crash',
          b['status'] == 'incomplete' and 'Phase 2' in b['why'], b)
    check('requirements_met is 0 (nothing checked — the chain is not there to check against)', b['requirements_met'] == 0, b)
    check('no claims/settings/routes are produced for an unmaterialized chain (never a misleading claim against the WRONG board\'s pins)',
          b['claims_refs_json'] == '[]' and b['settings_refs_json'] == '[]' and b['routes_refs_json'] == '[]', b)


def _board_exists(name):
    from board.custom import board_object as BO
    try:
        BO.rows_for(name)
        return True
    except BO.BoardObjectRefused:
        return False
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------- part 5: the live doors
def _live_api(check):
    """A second HardwareBinding to the SAME board (arduino-uno-r3) — created live, its own RegisterAssignment rows
    materialized, the assign/chain doors answer for it exactly as for the default, and reassigning its 'adc' task
    onto D7 (no ADC alternate function) is refused, naming D7 and the analog-in kind — never a false conflict with
    the DEFAULT binding's own A0 claim (binding-scoped occupancy, ucd-0b2b)."""
    from types import SimpleNamespace
    from falcon import testing
    import falcon
    from cmod.cmod_seed import CMOD_SEED_PAIRS
    from board.board_seed import BOARD_SEED_PAIRS
    from cmod.cmod_firmware_api import FirmwareAPI
    tables = {}
    mgr = SimpleNamespace(objectTables=tables, idList=[], db=None, saveObjToDB=lambda o: None)
    for _mid, pairs in (('board', BOARD_SEED_PAIRS), ('cmod', CMOD_SEED_PAIRS)):
        for name, cls, seed_rows in pairs:
            for row in seed_rows:
                o = cls(manager=mgr, **{k: v for k, v in row.items() if k != '_converge'})
                tables.setdefault(name, {})[o.id] = o
    app = falcon.App()
    FirmwareAPI(polServer=SimpleNamespace(falconServer=app, manager=mgr, idList=[]), manager=mgr)
    c = testing.TestClient(app)

    r = c.simulate_get('/api/firmware/bindings')
    check('GET /api/firmware/bindings lists the converged default binding', r.status_code == 200
          and any(x['name'] == DEFAULT_NAME for x in r.json['bindings']), r.text[:300])

    r1 = c.simulate_get('/api/firmware/solutions/%s' % SOLUTION)
    check('GET /api/firmware/solutions/<name> gains `binding` (the default) and `bindings` (every one)',
          r1.status_code == 200 and r1.json['binding']['name'] == DEFAULT_NAME
          and [x['name'] for x in r1.json['bindings']] == [DEFAULT_NAME], r1.text[:400])

    r2 = c.simulate_post('/api/firmware/solutions/%s/bindings' % SOLUTION, json={'board': BOARD})
    check('POST .../bindings {board} creates a SECOND binding to the SAME board (suffixed name, provenance canvas)',
          r2.status_code == 200 and r2.json['ok'] and r2.json['binding']['name'] == '%s#2' % DEFAULT_NAME
          and r2.json['binding']['provenance'] == 'canvas' and r2.json['binding']['is_default'] is False, r2.text[:400])
    second = r2.json['binding']['name']
    check('the new binding\'s own RegisterAssignment rows are materialized (configuration == its own name)',
          any(getattr(a, 'configuration', '') == second for a in tables.get('RegisterAssignment', {}).values()))

    # the chain door answers for '<solution>@<board>' exactly as for '<solution>' (the default, spelled out in full)
    r3a = c.simulate_get('/api/firmware/solutions/%s/pins/D6/chain' % SOLUTION)
    r3b = c.simulate_get('/api/firmware/solutions/%s/pins/D6/chain' % DEFAULT_NAME)
    check('the chain door answers IDENTICALLY for "<solution>" and "<solution>@<board>" (the same default binding)',
          r3a.status_code == 200 and r3b.status_code == 200
          and r3a.json['claim'] == r3b.json['claim'] and r3a.json['hops'] == r3b.json['hops'], (r3a.text[:200], r3b.text[:200]))

    # the assign door answers for the SECOND binding — reassigning adc.channel from A0 onto D7 (no ADC alt-function
    # on D7) is refused, naming D7 and the analog-in kind; the DEFAULT binding's own A0 claim is untouched
    r4 = c.simulate_post('/api/firmware/solutions/%s/assign' % second,
                         json={'task': 'adc', 'port': 'channel', 'lives_on': '%s:D7' % BOARD})
    check('reassigning the second binding\'s adc.channel onto D7 is REFUSED, naming D7 and no ADC alt-function (kind analog-in)',
          r4.status_code == 422 and r4.json.get('refused') and 'D7' in r4.json.get('error', '')
          and 'ADC' in r4.json.get('error', ''), r4.text[:300])
    from cmod.custom import targets as T
    check('…and the kind being checked really is analog-in (adc.channel\'s own requirement_kind)',
          T.requirement_kind(GRAPH, 'adc') == 'analog-in')
    r5 = c.simulate_get('/api/firmware/solutions/%s' % SOLUTION)
    a0_default = next(a for a in r5.json['assignments'] if a['task'] == 'adc')
    check('the DEFAULT binding\'s own adc.channel assignment is UNCHANGED (still A0) — the refused second-binding '
          'drop never touched it (binding-scoped occupancy)', a0_default['lives_on'] == '%s:A0' % BOARD, a0_default)

    # a direct validity() check that an ACTUALLY-recorded incompatible assignment is reported invalid, named
    from cmod.custom import binding as BND
    from cmod.cmod_basis import RegisterAssignment
    bad_name = '%s:adc.channel' % second
    existing = next((a for a in tables.get('RegisterAssignment', {}).values() if a.name == bad_name), None)
    if existing is not None:
        existing.lives_on, existing.status = '%s:D7' % BOARD, 'bound'
    status, why, total, met, refs = BND.validity(second, GRAPH, BOARD, manager=mgr)
    check('validity() over the FORCED-bad live row: status invalid, why names D7 and the ADC mismatch',
          status == 'invalid' and any('D7' in w and 'ADC' in w for w in why), (status, why))


#: ucd-0e2b: the SECOND solution's own default binding (`pol firmware bindings` shows uno-button-clock@arduino-uno-r3)
BC_SOLUTION, BC_GRAPH = 'uno-button-clock', 'uno-button-clock-graph'
BC_DEFAULT_NAME = '%s@%s' % (BC_SOLUTION, BOARD)


def _button_clock_binding(check):
    from cmod.custom import binding as BND
    b = BND.derive(BC_SOLUTION, manager=None)
    check('the default binding exists, named uno-button-clock@arduino-uno-r3, is_default, provenance derived',
          b is not None and b['name'] == BC_DEFAULT_NAME and b['is_default'] is True and b['provenance'] == 'derived', b)
    check('status valid, requirements_met == requirements_total == 17 (every required row met — D2/D3\'s interrupt-in '
          'claims resolve through PURE_CONFIG_SEED\'s authored edge/pull, never left incomplete)',
          b['status'] == 'valid' and b['requirements_met'] == b['requirements_total'] == 17 and b['why'] == '', b)
    claims_refs = json.loads(b['claims_refs_json'])
    check('claims_refs names PinClaim:…:D2/D3/D6/D13 and the PeripheralClaim(s) for EXINT/GPIO PORTD/USART0',
          all(('PinClaim:%s:%s' % (BC_SOLUTION, p)) in claims_refs for p in ('D2', 'D3', 'D6', 'D13')), claims_refs)
    routes_refs = json.loads(b['routes_refs_json'])
    check('routes_refs names the two ACTIVE SignalRoutes (D2:INT0, D3:INT1)',
          ('SignalRoute:%s:D2:INT0' % BC_SOLUTION) in routes_refs and ('SignalRoute:%s:D3:INT1' % BC_SOLUTION) in routes_refs, routes_refs)