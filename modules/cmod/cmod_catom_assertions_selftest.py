"""cmod_catom_assertions_selftest — hsp-3a (HARDWARE_SYSTEM_PINS_PLAN.md §7): the Catom assertions on uno-light's atoms hold the vocabulary; every binding of
his notebook draft is present WITH its asserting atom; the committed cycle record sets each status (bridge traffic verified, field changes exercised but
unverified, a missing function false by name); the gaps name the struct field nobody asserts and the draft fields the struct lacks; the StructObjectMap maps
LightState_t onto the LightState class field for field; the door serves the views; the manifest conforms.

    PYTHONPATH=.:modules python3 -m cmod.cmod_catom_assertions_selftest      # from polari-framework/
"""
import inspect
import json
import os
import sys
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def c3(CA, every):
    """2026-10-29: the esp32c3-light assertions - on atoms the C3 manifest has, on the pins its knobs and frame macros name, honest about having no record."""
    from board.custom import board_c3 as B3
    from board.custom import variants_c3 as V3
    from board.objects.board.ButtonClockState import ButtonClockState
    mine = [a for a in every if a['variant'] == CA.C3_VARIANT]
    man = json.load(open(os.path.join(os.path.dirname(os.path.abspath(V3.__file__)), 'firmware', 'esp32c3', 'polari-firmware.json')))
    atoms = {a['name'] for a in man['atoms']}
    check('C3 ATOMS: every esp32c3-light assertion names an atom of the C3 manifest (polari-firmware.json, cmod.custom.c3_atoms), struct ButtonClockState_t, bridge '
          'c3-1-bridge on the bridge kinds, lane task (FreeRTOS) except main\'s boot stores (init)', len(mine) == 9 and {a['atom'] for a in mine} <= atoms
          and {a['struct'] for a in mine} == {CA.C3_STRUCT} and all(a['bridge'] == CA.C3_BRIDGE for a in mine if 'bridge' in a['kind'])
          and {a['lane'] for a in mine if a['atom'] != 'apps/light.polari_app_main'} == {'task'}, sorted({a['atom'] for a in mine} - atoms))
    k = V3.LIGHT_KNOBS
    sym = {v.get('firmware_symbol'): p for p, v in B3.POLARI.items()}
    want = {'GPIO%d' % k['led_pin'], 'GPIO%d' % k['button_pin'], 'GPIO%d' % k['sense_pin'], sym['POLARI_FRAME_TX_GPIO'], sym['POLARI_FRAME_RX_GPIO']}
    pins = {p for a in mine for p in a['pins'].split(',') if p}
    check('C3 PINS come from the variant\'s knobs (LED GPIO%d, button GPIO%d, sense GPIO%d) and the board\'s frame UART symbols (%s TX, %s RX) - never typed apart'
          % (k['led_pin'], k['button_pin'], k['sense_pin'], sym['POLARI_FRAME_TX_GPIO'], sym['POLARI_FRAME_RX_GPIO']), pins == want, (pins, want))
    rows = CA.assertions(CA.C3_VARIANT)
    check('C3 NO RECORD (honest): no committed cycle record for esp32c3-light, so every C3 assertion is unverified and says so - none verified, none false',
          rows and all(a['status'] == 'unverified' and 'no cycle record' in a['status_why'] for a in rows), [(a['atom'], a['status']) for a in rows])
    b = {(x['pin'], x['field'], x['direction'], x['atom']) for x in CA.struct_pin_bindings(CA.C3_VARIANT)}
    want_b = {('GPIO3', 'led_on', 'in', 'apps/light.led_toggle'), ('GPIO3', 'button_presses', 'in', 'apps/light.led_toggle'),
              ('GPIO20', 'led_on', 'in', 'apps/light.apply_command'), ('GPIO0', 'led_on', 'out', 'apps/light.led_follow_task'),
              ('GPIO1', 'sense_rises', 'in', 'apps/light.sense_task'), ('GPIO21', '*', 'to-bridge', 'apps/light.telemetry_task'),
              ('GPIO20', '*', 'from-bridge', 'apps/light.rx_task')}
    check('C3 BINDINGS (derived): button GPIO3 -> button_presses/led_on (task, HW), UART0 RX GPIO20 -> led_on (US over c3-1-bridge), led_on -> LED GPIO0, the sense '
          'line GPIO1 -> sense_rises/falls, the whole struct -> GPIO21, GPIO20 <- the bridge', want_b <= b, sorted(want_b - b))
    g = CA.gaps(CA.C3_VARIANT)
    attrs = [p for p in inspect.signature(ButtonClockState.__init__).parameters if p not in ('self', 'manager')]
    check('C3 GAPS name every unasserted field WITH its reason: the clock-sync half (the light does not use it) and the command fields (decoded into a copy, never '
          'stored); no notebook-draft rows (the draft is the UNO\'s)', [x['field'] for x in g] == [f for f in attrs if f in CA.GAP_WHY[CA.C3_STRUCT]]
          and all(': ' in x['gap'] for x in g) and not any('notebook draft' in x['gap'] for x in g), [x['field'] for x in g])
    m = [r for r in CA.map_rows() if r['map'] == CA.C3_MAP]
    check('C3 STRUCT OBJECT MAP: ButtonClockState_t -> ButtonClockState, field for field in the class\'s order (CA.STRUCT_FIELDS equals the class\'s attributes)',
          [r['field'] for r in m] == list(CA.STRUCT_FIELDS[CA.C3_STRUCT]) == attrs and {a['object_map'] for a in mine} == {CA.C3_MAP}, (attrs, [r['field'] for r in m]))


def main():
    from cmod.custom import catom_assertions as CA
    from board.custom import cycle_records as CR
    every = CA.SEED_ASSERTIONS
    seeds = [a for a in every if a['variant'] == CA.VARIANT]
    bad = {a['name']: CA.problems(a) for a in every if CA.problems(a)}
    check('VOCABULARY: every seeded assertion holds (kind, lane = task-plan lanes + userspace, event, bridge named on bridge kinds, fields on field kinds)', not bad, bad)
    check('VOCABULARY: names are unique <variant>:<atom>:<kind>', len({a['name'] for a in every}) == len(every))
    rows = CA.assertions()
    by = {(a['atom'], a['kind']): a for a in rows}
    rec = CR.load('uno-light')
    check('RECORD: the committed uno-light cycle record is the one judged (USART0 bytes logged, RX + INT0 taken)',
          rec and rec['uart']['bytes_logged'] > 0 and rec['isrs']['USART_RX_vect']['n'] > 0 and rec['isrs']['INT0_vect']['n'] > 0)
    tx, rx = by[('apps/light.telemetry_send', 'sends-to-bridge')], by[('hal.USART_RX_vect', 'receives-from-bridge')]
    check('VERIFIED: telemetry_send sends-to-bridge (the bytes out of USART0 on PD1) and USART_RX_vect receives-from-bridge (RX takes on PD0), each saying the numbers',
          tx['status'] == 'verified' and '%d bytes' % rec['uart']['bytes_logged'] in tx['status_why'] and rx['status'] == 'verified'
          and 'taken %d times' % rec['isrs']['USART_RX_vect']['n'] in rx['status_why'], (tx['status_why'], rx['status_why']))
    fields = [a for a in rows if a['kind'] in ('changes-field', 'reads-field')]
    check('UNVERIFIED (honest): every field assertion is exercised (ran n > 0 times) but unverified - the record carries cycles, not memory writes',
          fields and all(a['status'] == 'unverified' and 'exercised' in a['status_why'] and 'not memory writes' in a['status_why'] for a in fields),
          [(a['atom'], a['status_why'][:60]) for a in fields if a['status'] != 'unverified'])
    check('NONE FALSE: every seeded assertion names an atom the record\'s build has', not [a for a in rows if a['status'] == 'false'])
    ghost = dict(seeds[0], atom='apps/light.no_such_atom', name='uno-light:apps/light.no_such_atom:changes-field')
    st, why = CA.verify(ghost, rec)
    silent = dict(rec, uart=dict(rec['uart'], bytes_logged=0))
    st2, why2 = CA.verify(tx, silent)
    st3, _ = CA.verify(dict(rx, atom='hal.PCINT0_vect'), rec)
    check('FALSE by name: an assertion on a function the build lacks names it; a sender that ran with no UART bytes is false; an ISR never taken is unverified, not false',
          st == 'false' and 'apps/light.no_such_atom' in why and st2 == 'false' and 'no UART bytes' in why2 and st3 == 'unverified', (why, why2, st3))
    check('NO RECORD: every status unverified and saying so', all(a['status'] == 'unverified' and 'no cycle record' in a['status_why'] for a in CA.assertions(rec=None)))
    b = CA.struct_pin_bindings()
    have = {(x['pin'], x['field'], x['direction'], x['atom']) for x in b}
    want = {('PD2', 'led_on', 'in', 'apps/light.led_toggle'), ('PD2', 'source', 'in', 'apps/light.led_toggle'),
            ('PD0', 'led_on', 'in', 'apps/light.apply_command'), ('PD6', 'led_on', 'out', 'apps/light.led_follow_state'),
            ('PD1', '*', 'to-bridge', 'apps/light.telemetry_send'), ('PD0', '*', 'from-bridge', 'hal.USART_RX_vect')}
    check('BINDINGS (derived): his draft\'s couplings are present WITH the asserting atom - button PD2 -> led_on/source (loop, HW), UART RX PD0 -> led_on '
          '(US, via the bridge), led_on -> LED PD6, the whole struct -> PD1 (to the bridge), PD0 <- the bridge', want <= have, sorted(want - have))
    pd2 = next(x for x in b if x['pin'] == 'PD2' and x['field'] == 'led_on')
    cmd = next(x for x in b if x['pin'] == 'PD0' and x['field'] == 'led_on')
    check('BINDINGS carry lane + event + updater + stamps + basis: PD2 = loop / edge-fall / HW, PD0 = loop / uart-rx / US over uno-1-bridge; no timestamp (the struct has none)',
          (pd2['lane'], pd2['event'], pd2['updater'], pd2['stamps']) == ('loop', 'edge-fall', 'HW', 'none') and (cmd['updater'], cmd['bridge']) == ('US', 'uno-1-bridge')
          and pd2['basis'].startswith('derived from the catom assertion'), (pd2, cmd))
    g = CA.gaps()
    gf = [x['field'] for x in g]
    check('GAPS: the struct field no catom changes (name: set by main(), which is not an atom) and the draft fields the struct lacks (HardSwitch, UIswitch, LightId, '
          'timestampHW, timestampUS) - each named; the draft LedOn / lastUpdater map onto led_on / source',
          gf == ['name', 'HardSwitch', 'UIswitch', 'LightId', 'timestampHW', 'timestampUS'] and 'no catom asserts a change of LightState_t.name' in g[0]['gap']
          and {r['draft_field']: r['firmware_field'] for r in CA.draft_rows()}['lastUpdater'] == 'source', gf)
    from board.objects.board.LightState import LightState
    attrs = [p for p in inspect.signature(LightState.__init__).parameters if p not in ('self', 'manager')]
    m = [r for r in CA.map_rows() if r['map'] == CA.MAP]
    check('STRUCT OBJECT MAP (D-hsp-8): LightState_t -> LightState, every struct field onto the Polari class\'s own attribute of the same name, and CA.STRUCT_FIELDS '
          'equals the class\'s fields in order', [r['field'] for r in m] == list(CA.STRUCT_FIELDS['LightState_t']) == attrs and all(r['field'] == r['attribute'] for r in m)
          and {a['object_map'] for a in seeds} == {CA.MAP}, (attrs, [r['field'] for r in m]))
    c3(CA, every)
    from cmod.cmod_catom_api import CatomAssertionAPI
    api = CatomAssertionAPI(polServer=None, manager=None)

    def get(variant, view=''):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        api.on_get(types.SimpleNamespace(get_param=lambda k: view or None), resp, variant)
        return resp
    full, gaps_v, nope, badv = get('uno-light'), get('uno-light', 'gaps'), get('no-such-variant'), get('uno-light', 'json')
    lst = types.SimpleNamespace(status='200 OK', media=None)
    api.on_get_list(types.SimpleNamespace(get_param=lambda k: 'esp32-c3' if k == 'board' else None), lst)
    check('LIST DOOR: GET /api/cmod/catom-assertions?board=esp32-c3 = the one variant asserted on that board (what the pin view loads with no binding chosen)',
          [(r['variant'], r['struct'] if 'struct' in r else r['structs'], r['count']) for r in lst.media['rows']] == [('esp32c3-light', 'ButtonClockState_t', 9)], lst.media)
    check('DOOR: GET /api/cmod/catom-assertions/uno-light = assertions + bindings + gaps; ?view=gaps = rows; unknown variant 404; unknown view 422',
          full.media['ok'] and len(full.media['assertions']) == len(seeds) and full.media['bindings'] and gaps_v.media['count'] == 6
          and nope.status.startswith('404') and badv.status.startswith('422'), (nope.status, badv.status))
    json.dumps(full.media)
    from moduleService.manifests import conform
    r = conform('cmod')
    check('MANIFEST: pol modules conform cmod is clean with the new classes + files listed', r['ok'], r.get('findings'))
    print('\n%d/%d passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
