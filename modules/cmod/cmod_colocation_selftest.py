"""cmod_colocation_selftest - pp-1: the per-Mission co-location report (cmod.custom.mission_colocation) and its door beside mis-0 / pp-0 / iso-0 routes.
Called from cmod_selftest.main as `colocation_parts(check)`; alone: PYTHONPATH=.:modules python3 -m cmod.cmod_colocation_selftest."""
import contextlib
import io
import json
import os
from types import SimpleNamespace

MISSION = 'uno-light-mission'


def colocation_parts(check):
    def report():
        from cmod.custom import mission_colocation as MC
        r = MC.mission_colocation(MISSION)
        roles = {p['role']: p for p in r['profiles']}   # the two transport profiles share a role name
        check('pp-1: the light Mission co-location reads pp-0\'s 5 profiles (transport rx + tx reserved, the LED, the button, the sense line)',
              len(r['profiles']) == 5 and {'the LED', 'the button', 'the sense line'} <= set(roles) and sum(p['reserved'] for p in r['profiles']) == 2, str(list(roles)))

        def row(a, b, scope, src='pair_rows'):
            return next((x for x in r[src] if {x['pair']} & {'%s + %s' % (a, b), '%s + %s' % (b, a)} and x['scope'] == scope), None)
        led_sense_net = row('the LED', 'the sense line', 'net')
        led_sense_pin = row('the LED', 'the sense line', 'pin')
        check('pp-1 LIGHT DEMO: the LED drive and the sense line CAN share a NET (compatible: one output + one input, rule single_output - the D6 -> D3 wire the bench already has)',
              led_sense_net and led_sense_net['verdict'] == 'compatible' and 'single_output' in led_sense_net['cite'], str(led_sense_net))
        check('pp-1 LIGHT DEMO: on one PIN the sense line could only read the output back (PINx 14.2.4 p.86) or take the interrupt that fires on outputs (13 p.79): conditional, cited - and the note says the demo deliberately uses a real wire',
              led_sense_pin and led_sense_pin['verdict'] == 'conditional' and 'p.79' in led_sense_pin['cite'] and any('REAL WIRE' in n and 'single_output' in n for n in r['notes']), str((led_sense_pin, r['notes'])))
        led_btn_pin, led_btn_net = row('the LED', 'the button', 'pin'), row('the LED', 'the button', 'net')
        check('pp-1 LIGHT DEMO: the button and the LED can NOT share a pin (the pull-up exists only while the pin is an input, Table 14-1 p.86) nor a net (the switch to ground would short a second output)',
              led_btn_pin['verdict'] == 'exclusive' and led_btn_pin['reason'].count('pull-up') >= 1 and 'p.86' in led_btn_pin['cite'] and led_btn_net['verdict'] == 'exclusive' and 'switch' in led_btn_net['reason'],
              str((led_btn_pin, led_btn_net)))
        apart = {(x['a'], x['b'], x['scope']) for x in r['forced_apart']}
        check('pp-1 LIGHT DEMO: the forced-apart list names the LED + button (pin and net), the transport against the LED at pin and net, and the transport pair itself',
              ('the LED', 'the button', 'pin') in apart and ('the LED', 'the button', 'net') in apart and ('the transport', 'the LED', 'pin') in apart
              and ('the transport', 'the transport', 'pin') in apart and ('the transport', 'the transport', 'net') in apart, str(sorted(apart)[:12]))
        trans = [g for g in r['groups'] if g['reserved']]
        check('pp-1 LIGHT DEMO: the transport pair is reserved - each on its own pin, never grouped; the minimum is 4 pins for 5 profiles (the LED and the sense line share one pin, with the self-interrupt condition carried)',
              len(trans) == 2 and all(not g['shared'] for g in trans) and r['pins_without_sharing'] == 5 and r['min_pins'] == 4
              and any(g['shared'] and 'the LED' in ' '.join(g['profiles']) and 'the sense line' in ' '.join(g['profiles']) and g['conditions'] for g in r['groups'])
              and 'PD0' not in next(g for g in r['groups'] if g['shared'])['pin_options'].split(', '), str(r['groups']))
        check('pp-1: every row of the report is plain words with a citation (no raw JSON), and the unresolved tasks are admitted in the notes',
              all(x['cite'] and x['reason'] and not x['reason'].startswith(('{', '[')) for x in r['pair_rows']) and any('gave no profile' in n for n in r['notes']))
        # a made-up Mission: only the first two Purposes' profiles, to prove the grouping is computed, not canned
        r2 = MC.mission_colocation('x', purposes=['ensure-button-controls-light'])
        check('pp-1: any Mission works - an explicit Purpose list (basis named) is grouped the same way: the button stays apart, the sense shares the LED pin',
              r2['basis'] == 'an explicit list of Purposes' and r2['min_pins'] == r2['pins_without_sharing'] - 1 and any(g['shared'] for g in r2['groups']), str((r2['basis'], r2['min_pins'], r2['pins_without_sharing'])))
        try:
            MC.mission_colocation('no-such-mission')
            bad = False
        except ValueError:
            bad = True
        check('pp-1: an unknown Mission is refused naming it (ValueError, the door turns it into a 404)', bad)
        outs = []
        for argv in (['colocation', MISSION], ['colocation', MISSION, '--json'], ['colocation', 'no-such-mission']):
            with contextlib.redirect_stdout(io.StringIO()) as o:
                rc = MC.main(argv)
            outs.append((rc, o.getvalue()))
        check('pp-1 CLI: `colocation <mission> [--purposes a,b] [--json]` prints the pin groups, the nets that could be shared and the forced-apart pairs; --json is valid; an unknown Mission is refused (rc 3)',
              outs[0][0] == 0 and 'most permissive valid sharing needs 4' in outs[0][1] and 'forced apart' in outs[0][1] and json.loads(outs[1][1])['min_pins'] == 4 and outs[2][0] == 3)

    def doors():
        import falcon
        from falcon import testing
        from cmod.cmod_endpoints import construct_cmod_endpoints
        from board.board_endpoints import construct_board_endpoints
        from cmod.custom.selftest_purpose import _manager
        for board_first in (False, True):
            app = falcon.App()
            ps = SimpleNamespace(falconServer=app, manager=_manager(), idList=[])
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    if board_first:
                        construct_board_endpoints(ps)
                    construct_cmod_endpoints(ps)       # CModAPI + firmware + capability + pp-0 + mis-0 + iso-0 + pp-1 doors, all on one app
                    if not board_first:
                        construct_board_endpoints(ps)
                c = testing.TestClient(app)
                co = c.simulate_get('/api/missions/%s/colocation' % MISSION)
                grp = c.simulate_get('/api/missions/%s/colocation?view=groups' % MISSION).json
                apart = c.simulate_get('/api/missions/%s/colocation?view=apart' % MISSION).json
                pp0 = c.simulate_get('/api/missions/%s/pin-profiles' % MISSION)
                mis0 = [c.simulate_get('/api/missions/%s/%s' % (MISSION, s)).status_code for s in ('solution', 'resolution')] + [c.simulate_get('/api/missions').status_code]
                tbl = c.simulate_get('/api/board/socs/atmega328p/profile-overlap?scope=pin')
                nom = c.simulate_get('/api/missions/zzz/colocation')
                viewbad = c.simulate_get('/api/missions/%s/colocation?view=zzz' % MISSION)
                byp = c.simulate_get('/api/missions/anything/colocation?purposes=ensure-button-controls-light')
                ok = (co.status_code == 200 and co.json['min_pins'] == 4 and co.json['count'] == len(co.json['pair_rows']) == 30 and grp['count'] == 4 and apart['count'] > 5
                      and pp0.status_code == 200 and pp0.json['pins_needed'] == 5 and mis0 == [200, 200, 200] and tbl.status_code == 200 and tbl.json['count'] == 153
                      and nom.status_code == 404 and 'zzz' in nom.json['error'] and viewbad.status_code == 400 and byp.status_code == 200)
                why = str((co.status_code, grp.get('count'), pp0.status_code, mis0, tbl.status_code, nom.status_code, byp.status_code))
            except Exception as ex:   # a route clash raises UnacceptableRouteError at add time
                ok, why = False, repr(ex)
            check('pp-1 DOORS: GET /api/missions/{name}/colocation[?purposes=&view=pairs|groups|apart] and /api/board/socs/{soc}/profile-overlap ADD on a real falcon.App with EVERY cmod door (mis-0 solution/resolution/list, pp-0 pin-profiles, iso-0) and every board door (%s registered first) and answer; none shadows another; unknown Mission 404, bad view 400' % ('board' if board_first else 'cmod'), ok, why)

    def manifest():
        root = os.path.dirname(os.path.abspath(__file__))
        man = json.load(open(os.path.join(root, 'polari-app.json')))
        listed = {f for v in man['files'].values() for f in v}
        new = ['cmod_colocation_api', 'cmod_colocation_selftest', 'custom/mission_colocation']
        check('pp-1 MANIFEST: cmod/polari-app.json lists every new cmod file and the door class; each exists', all(n in listed for n in new) and 'ColocationAPI' in man['classes']
              and all(os.path.exists(os.path.join(root, n + '.py')) for n in new))
    return (report, doors, manifest)


if __name__ == '__main__':
    n = [0, 0]

    def _check(label, cond, extra=''):
        n[1] += 1
        n[0] += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, '' if cond else extra))
    for part in colocation_parts(_check):
        part()
    print('\n%d/%d checks passed' % tuple(n))
