"""instruments_placement_selftest — osc-8 (OSCILLOSCOPE_PLAN.md §2c): instruments placed on a bench as UNITS with PROBES and used in SIMULATION.

Two DSO138 units + one DHO804 on the home bench (in-memory store, no manager): three unit rows; the DSO138 units get a capability STAND-IN profile
`row:jyetech-dso138` built from the row's cited numbers (1 channel, 1 MSa/s, 12 bits, 1024 points), the DHO804 its own model profile; the probe door
refuses channel 2 on a one-channel scope by name and writes ScopeChannel rows with the signal kind from the pin view's vocabulary; simulate from
`uno-light` starts three emulated endpoints fed from the probes (PD2 / adc0), a capture on a DSO138 unit honours its limits (1024 points, <= 1 MSa/s,
12-bit mid-scale 2048), `*IDN?` says POLARI,DSO138-EMU; a bad line is refused naming the known lines while the other units are fed; simulating again
RESTARTS (still three endpoints, new sessions); the workbench page's new paths are registered routes.

    PYTHONPATH=.:modules python3 -m instruments.instruments_placement_selftest      # from polari-framework/
"""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _walk(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ('dataPath', 'data_path', 'path') and isinstance(v, str) and v.startswith('/api/'):
                out.append(v)
            _walk(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk(v, out)


def run():
    from instruments.custom import placement as P, catalog as C, captures as X
    from instruments.custom.emulator import PROFILES
    from board.custom import bench as BENCH
    bench = C.SEED_HOME()
    BENCH._MEM.clear()
    X._MEM['InstrumentEndpoint'].clear()
    X._MEM['WaveformCapture'].clear()
    X._MEM['ScopeChannel'].clear()
    b = BENCH.bench(bench, None)
    b['instruments_json'] = '[]'
    BENCH._save(None, b)
    # -- units from counts
    st1, _ = C.add_instrument(None, bench, {'model': 'jyetech-dso138', 'count': 2})
    st2, _ = C.add_instrument(None, bench, {'model': 'rigol-dho804', 'count': 1})
    rows = P.units(bench, None)
    names = [r['unit'] for r in rows]
    check('osc-8 UNITS: 2 x DSO138 + 1 x DHO804 on the home bench -> three unit rows named <bench>-<model>-<n>', st1 == 201 and st2 == 201
          and names == ['%s-jyetech-dso138-1' % bench, '%s-jyetech-dso138-2' % bench, '%s-rigol-dho804-1' % bench], names)
    check('osc-8 UNITS: every unit starts "not started" with no probes', all(r['endpoint_status'] == 'not started' and r['probes'] == '(none)' for r in rows), rows)
    # -- stand-in profiles
    dso = [r for r in rows if r['model'] == 'jyetech-dso138']
    check('osc-8 STAND-IN: the DSO138 units use profile row:jyetech-dso138 marked "stand-in (capability only)"; the DHO804 its own model profile dho804',
          all(r['profile'] == 'row:jyetech-dso138' and r['profile_kind'].startswith('stand-in') for r in dso)
          and rows[2]['profile'] == 'dho804' and rows[2]['profile_kind'] == 'model profile', [(r['profile'], r['profile_kind']) for r in rows])
    p = PROFILES['row:jyetech-dso138']
    check('osc-8 STAND-IN numbers = the DSO138 row (1 channel, 12 bits, 1 MSa/s, 1024 points, 10 mV..5 V/div, 10 us..500 s/div)',
          p['channels'] == 1 and p['bits'] == 12 and p['max_srate'] == {1: 1e6} and p['max_depth'] == {1: 1024} and p['default_depth'] == 1024
          and p['scale_min'] == 10e-3 and p['scale_max'] == 5.0 and p['tb_min'] == 10e-6 and p['tb_max'] == 500.0, p)
    check('osc-8 STAND-IN basis says CAPABILITY STAND-IN, names the protocol as Polari\'s (not the serial-text line) and the IDN form',
          'CAPABILITY STAND-IN' in p['basis'] and 'serial-text' in p['basis'] and 'POLARI,DSO138-EMU' in p['basis'], p['basis'])
    sf = P.standin_profile(next(m for m in C.models(None) if m['name'] == 'scopefun'))
    check('osc-8 STAND-IN for ScopeFun: 2 ch, 10 bits, 500 M / 250 MSa/s by channel count, 128 Mpts; the unread timebase takes a default SAID in basis',
          sf['channels'] == 2 and sf['bits'] == 10 and sf['max_srate'] == {1: 500e6, 2: 250e6} and sf['max_depth'] == {1: 128e6, 2: 128e6}
          and 'timebase min s/div' in sf['basis'] and 'defaults said' in sf['basis'], sf)
    # -- probes
    st, r = P.probe(None, bench, {'model': 'jyetech-dso138', 'unit': 1, 'channel': 2, 'line': 'PD2'})
    check('osc-8 PROBE refuses channel 2 on the one-channel DSO138 by name', st == 400 and 'has 1 analog channel' in r['error'], r)
    st, r = P.probe(None, bench, {'model': 'jyetech-dso138', 'unit': 3, 'channel': 1, 'line': 'PD2'})
    check('osc-8 PROBE refuses unit 3 of a count-2 entry', st == 400 and 'unit must be 1..2' in r['error'], r)
    st, r = P.probe(None, bench, {'model': 'rigol-dho812', 'unit': 1, 'channel': 1, 'line': 'PD2'})
    check('osc-8 PROBE refuses a model that is not on the bench, naming the ones that are', st == 404 and r.get('known') == ['jyetech-dso138', 'rigol-dho804'], r)
    st, r = P.probe(None, bench, {'model': 'scopefun', 'unit': 1, 'channel': 3, 'line': 'PD2'})
    check('osc-8 PROBE: a model not on the bench is refused before its channels are looked at', st == 404, r)
    C.add_instrument(None, bench, {'model': 'scopefun', 'count': 1})
    st, r = P.probe(None, bench, {'model': 'scopefun', 'unit': 1, 'channel': 3, 'line': 'PD2'})
    check('osc-8 PROBE: channel 3 on the ScopeFun (2 analog) is refused and the words say its 12 logic inputs are not scope channels',
          st == 400 and 'has 2 analog channel' in r['error'] and '12 logic input' in r['error'], r)
    C.remove_instrument(None, bench, {'model': 'scopefun'})
    st, r1 = P.probe(None, bench, {'model': 'jyetech-dso138', 'unit': 1, 'channel': 1, 'line': 'PD2'})
    st2, r2 = P.probe(None, bench, {'model': 'jyetech-dso138', 'unit': 2, 'channel': 1, 'line': 'adc0'})
    st3, _ = P.probe(None, bench, {'model': 'rigol-dho804', 'unit': 1, 'channel': 1, 'line': 'PD2'})
    st4, _ = P.probe(None, bench, {'model': 'rigol-dho804', 'unit': 1, 'channel': 2, 'line': 'adc0'})
    check('osc-8 PROBE writes ScopeChannel rows: DSO138 #1 ch1 <- PD2 (digital: a port bit), DSO138 #2 ch1 <- adc0 (analog), DHO804 ch1 <- PD2 + ch2 <- adc0',
          st == 201 and st2 == 201 and st3 == 201 and st4 == 201 and r1['signal_kind'] == 'digital' and r2['signal_kind'] == 'analog', (r1, r2))
    chs = {c['name']: c for c in P.channel_rows(None)}
    check('osc-8 ScopeChannel rows keyed by the unit\'s endpoint name (<unit>-ch<n>) with probing = the line and basis "typed"',
          set(chs) == {names[0] + '-ch1', names[1] + '-ch1', names[2] + '-ch1', names[2] + '-ch2'} and chs[names[0] + '-ch1']['probing'] == 'PD2'
          and chs[names[2] + '-ch2']['probing'] == 'adc0' and all(c['basis'].startswith('typed') for c in chs.values()), sorted(chs))
    rows = P.units(bench, None)
    check('osc-8 UNITS show the probes', rows[0]['probes'] == 'ch1 <- PD2' and rows[1]['probes'] == 'ch1 <- adc0' and rows[2]['probes'] == 'ch1 <- PD2; ch2 <- adc0', [r['probes'] for r in rows])
    # -- simulate
    st, r = P.simulate(None, bench, {})
    check('osc-8 SIMULATE needs a stimulus or events', st == 400 and 'stimulus' in r['error'], r)
    st, r = P.simulate(None, bench, {'stimulus': 'uno-light'})
    try:
        check('osc-8 SIMULATE from uno-light: three rows, every unit fed, the window = the stimulus\'s 1.3 s, alignment "exact by construction" on every row',
              st == 200 and r['ok'] and r['units'] == 3 and r['fed'] == 3 and abs(r['seconds'] - 1.3) < 1e-9
              and all(x['ok'] and x['alignment'].startswith('exact by construction') for x in r['rows']), r)
        check('osc-8 SIMULATE rows name the channels fed and the lines', r['rows'][2]['channels_fed'] == 'ch1, ch2' and r['rows'][2]['lines'] == 'PD2, adc0'
              and r['rows'][0]['lines'] == 'PD2', r['rows'])
        eps = X.endpoints(None)
        check('osc-8 three endpoints, one per unit, named like the units, on loopback ports', sorted(e['name'] for e in eps) == sorted(names) and all(e['port'] > 0 for e in eps), eps)
        rows = P.units(bench, None)
        check('osc-8 UNITS now show the endpoint status + port', all(r['endpoint_status'] == 'unchecked' and r['port'] > 0 for r in rows), rows)
        st, idn = X.idn(None, names[0])
        check('osc-8 *IDN? on a DSO138 unit says POLARI,DSO138-EMU (the stand-in never claims to be the instrument)', st == 200 and idn['idn'].split(',')[:2] == ['POLARI', 'DSO138-EMU'], idn)
        st, cap = X.capture(None, names[0], {})
        row = cap['rows'][0] if st == 201 else {}
        check('osc-8 CAPTURE on a DSO138 unit with channels blank asks for channel 1 only (the model has one) -> one row', st == 201 and len(cap['rows']) == 1 and row.get('channel') == 1, cap)
        full = next(c for c in X.captures(None) if c['name'] == row.get('name'))
        check('osc-8 the DSO138 stand-in\'s limits hold: 1024 points, sample rate = 1024 / 1.3 s (<= 1 MSa/s), 12-bit mid-scale y_reference 2048',
              full['points'] == 1024 and abs(full['sample_rate_sps'] - 1024 / 1.3) < 1e-3 and full['y_reference'] == 2048 and full['memory_depth_pts'] == 1024,
              (full['points'], full['sample_rate_sps'], full['y_reference']))
        check('osc-8 the capture is EMULATED and its source_ref names the stimulus', full['source'] == 'emulated' and 'stimulus uno-light' in full['source_ref'], full['source_ref'])
        check('osc-8 the PD2 line on the DSO138: the trace idles at 5 V and dips to 0 V (five presses)', row['v_max'] > 4.9 and row['v_min'] < 0.1, row)
        st, cap4 = X.capture(None, names[2], {})
        check('osc-8 CAPTURE on the DHO804 unit (4 channels) -> four rows; ch2 (adc0, 0.75 V dc) reads 0.75 V within 12 bits at 2 V/div',
              st == 201 and len(cap4['rows']) == 4 and abs(cap4['rows'][1]['v_mean'] - 0.75) < 0.01, cap4)
        # -- a bad line
        P.probe(None, bench, {'model': 'jyetech-dso138', 'unit': 2, 'channel': 1, 'line': 'PB9'})
        st, r = P.simulate(None, bench, {'stimulus': 'uno-light'})
        bad = r['rows'][1]
        check('osc-8 a probe on a line the stimulus does not drive is REFUSED naming the known lines; the other two units are fed; ok is False',
              st == 200 and not r['ok'] and r['fed'] == 2 and not bad['ok'] and 'PB9' in bad['refusal'] and 'known lines: PD2, adc0' in bad['refusal']
              and r['rows'][0]['ok'] and r['rows'][2]['ok'], r)
        P.probe(None, bench, {'model': 'jyetech-dso138', 'unit': 2, 'channel': 1, 'line': 'adc0'})
        # -- simulate again restarts, no duplicates
        sessions = {n: X._EMUS[n].state.session for n in names}
        st, r = P.simulate(None, bench, {'stimulus': 'uno-light'})
        check('osc-8 SIMULATE again: still three endpoints (reused rows, no duplicates), every emulator a NEW session', st == 200 and r['fed'] == 3
              and len(X.endpoints(None)) == 3 and all(X._EMUS[n].state.session != sessions[n] for n in names), (sessions, {n: X._EMUS[n].state.session for n in names}))
        st, r = P.simulate(None, bench, {'stimulus': 'uno-light', 'units': names[1]})
        check('osc-8 SIMULATE a chosen unit only', st == 200 and r['units'] == 1 and r['rows'][0]['unit'] == names[1], r)
        st, r = P.simulate(None, bench, {'stimulus': 'uno-light', 'units': 'nobody'})
        check('osc-8 SIMULATE an unknown unit name is refused naming the units', st == 404 and r['known'] == names, r)
        st, r = P.simulate(None, bench, {'stimulus': 'no-such-variant'})
        check('osc-8 SIMULATE an unknown stimulus: every unit row refused with the words', st == 200 and not r['ok'] and r['fed'] == 0 and all('no stimulus' in x['refusal'] for x in r['rows']), r)
        st, r = P.probe(None, bench, {'model': 'jyetech-dso138', 'unit': 1, 'channel': 1, 'line': ''})
        check('osc-8 PROBE with an empty line takes the probe off', st == 200 and P.units(bench, None)[0]['probes'] == '(none)', r)
        st, r = P.simulate(None, bench, {'stimulus': 'uno-light'})
        check('osc-8 a unit without probes is skipped with words, not started', st == 200 and r['rows'][0]['refusal'].startswith('no probes') and r['fed'] == 2, r)
    finally:
        st, r = P.stop_all(None, bench)
    check('osc-8 STOP stops every running unit emulator', st == 200 and not X._EMUS and all(e['status'] == 'stopped' for e in X.endpoints(None)), r)
    # -- the doors are routed and the page paths are registered routes
    from instruments.custom import catalog as C2
    st, r = C2.get_door(None, {}, 'units', bench)
    check('osc-8 GET units door answers rows', st == 200 and len(r['rows']) == 3, r)
    st, r = C2.post_door(None, bench, 'simulate', {})
    check('osc-8 POST simulate door is routed', st == 400 and 'stimulus' in r['error'], r)
    from board import workbench_page as WB
    import json
    import re
    paths = []
    _walk(json.loads(WB.WORKBENCH_PAGES[0]['definition']), paths)
    api = open(__file__.replace('instruments_placement_selftest.py', 'instruments_api.py')).read()
    routes = re.findall(r"add\('([^']+)'", api)
    mine = [p for p in paths if p.startswith('/api/instruments/')]
    bad = [p for p in mine if not any(re.fullmatch(re.sub(r'\{[^}]+\}', '[^/]+', r), p.split('?')[0].replace('{scope:bench}', 'x')) for r in routes)]
    check('osc-8 PATHS: every instruments path the workbench page uses (%d) is a route in instruments_api.py' % len(mine), mine and not bad, bad)
    norm = {re.sub(r'\?.*$', '', p).replace('{scope:bench}', 'home-bench') for p in paths}
    check('osc-8 workbench page uses the units / probe / simulate doors', {'/api/instruments/bench/home-bench/units', '/api/instruments/bench/home-bench/probe',
                                                                           '/api/instruments/bench/home-bench/simulate'} <= norm, sorted(norm))
    from instruments.instruments_api import InstrumentsAPI
    import inspect
    src = inspect.getsource(InstrumentsAPI.__init__)
    check('osc-8 the API registers the three routes + stop', all(x in src for x in ('/units', '/probe', '/simulate', '/stop')))


if __name__ == '__main__':
    run()
    print('\ninstruments placement selftest: %d/%d passed' % (passed, total))
    sys.exit(0 if passed == total else 1)
