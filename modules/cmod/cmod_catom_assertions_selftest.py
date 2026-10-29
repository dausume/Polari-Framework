"""cmod_catom_assertions_selftest — hsp-3a (HARDWARE_SYSTEM_PINS_PLAN.md §7): the Catom assertions on uno-light's atoms hold the vocabulary; every binding of
his notebook draft is present WITH its asserting atom; the committed cycle record sets each status (bridge traffic verified, field changes exercised but
unverified, a missing function false by name); the gaps name the struct field nobody asserts and the draft fields the struct lacks; the StructObjectMap maps
LightState_t onto the LightState class field for field; the door serves the views; the manifest conforms.

    PYTHONPATH=.:modules python3 -m cmod.cmod_catom_assertions_selftest      # from polari-framework/
"""
import inspect
import json
import sys
import types

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from cmod.custom import catom_assertions as CA
    from board.custom import cycle_records as CR
    seeds = CA.SEED_ASSERTIONS
    bad = {a['name']: CA.problems(a) for a in seeds if CA.problems(a)}
    check('VOCABULARY: every seeded assertion holds (kind, lane = task-plan lanes + userspace, event, bridge named on bridge kinds, fields on field kinds)', not bad, bad)
    check('VOCABULARY: names are unique <variant>:<atom>:<kind>', len({a['name'] for a in seeds}) == len(seeds))
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
    m = CA.map_rows()
    check('STRUCT OBJECT MAP (D-hsp-8): LightState_t -> LightState, every struct field onto the Polari class\'s own attribute of the same name, and CA.STRUCT_FIELDS '
          'equals the class\'s fields in order', [r['field'] for r in m] == list(CA.STRUCT_FIELDS['LightState_t']) == attrs and all(r['field'] == r['attribute'] for r in m)
          and {a['object_map'] for a in seeds} == {CA.MAP}, (attrs, [r['field'] for r in m]))
    from cmod.cmod_catom_api import CatomAssertionAPI
    api = CatomAssertionAPI(polServer=None, manager=None)

    def get(variant, view=''):
        resp = types.SimpleNamespace(status='200 OK', media=None)
        api.on_get(types.SimpleNamespace(get_param=lambda k: view or None), resp, variant)
        return resp
    full, gaps_v, nope, badv = get('uno-light'), get('uno-light', 'gaps'), get('no-such-variant'), get('uno-light', 'json')
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
