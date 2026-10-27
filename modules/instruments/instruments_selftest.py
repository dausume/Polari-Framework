"""instruments_selftest — osc-0 (OSCILLOSCOPE_PLAN.md §3a): the DHO804 row equals the datasheet table (DSA36106-1110 pp.6-9) number for
number; unverified fields are -1 / 'unverified' (never a guess); the lineage rows carry no numbers; the card text derives from the numbers;
the bench doors add / list / remove an instrument on a bench (in-memory store, no manager) and refuse a lineage row and an unknown model;
/display/instruments uses only the generic `cards` kind + a configured table and every path is a registered route; the manifest conforms.

    PYTHONPATH=.:modules python3 -m instruments.instruments_selftest      # from polari-framework/
"""
import json
import re
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


def facts():
    from instruments.instruments_seed import SEED_INSTRUMENTS as S
    from instruments.instruments_basis import Instrument, LINEAGES, KINDS
    by = {r['name']: r for r in S}
    d = by['rigol-dho804']
    check('osc-0 DHO804: 4 channels, no EXT, 70 MHz, rise <= 5 ns, 12 bits (datasheet p.6)',
          d['channels'] == 4 and d['ext_trigger'] is False and d['bandwidth_hz'] == 70e6 and d['rise_time_ns'] == 5 and d['resolution_bits'] == 12)
    check('osc-0 DHO804: sample rate 1.25 GSa/s / 625 MSa/s / 312.5 MSa/s with 1 / 2 / 4 channels; depth 25 / 10 / 5 Mpts (datasheet p.6 + p.9)',
          json.loads(d['sample_rate_by_channels_json']) == {'1': 1.25e9, '2': 625e6, '4': 312.5e6}
          and json.loads(d['memory_depth_by_channels_json']) == {'1': 25e6, '2': 10e6, '4': 5e6}
          and d['sample_rate_sps'] == 1.25e9 and d['memory_depth_pts'] == 25e6)
    check('osc-0 DHO804: 1,000,000 wfms/s UltraAcquire, 1 MOhm / 15 pF, 300 Vrms, 500 uV/div .. 10 V/div, 5 ns/div .. 500 s/div (p.6-8)',
          d['capture_rate_wfms'] == 1000000 and 'UltraAcquire' in d['capture_rate_basis'] and d['input_impedance_ohm'] == 1e6 and d['input_capacitance_pf'] == 15
          and d['max_input_v_rms'] == 300 and d['sensitivity_min_v_div'] == 500e-6 and d['sensitivity_max_v_div'] == 10 and d['timebase_min_s_div'] == 5e-9
          and d['timebase_max_s_div'] == 500)
    check('osc-0 DHO804: agilent lineage, the Rigol *IDN? form, LXI unverified, the datasheet + scopehal cited, the forum-sourced ports say so, emulated=True (profile dho804)',
          d['lineage'] == 'agilent' and d['idn_format'].startswith('RIGOL TECHNOLOGIES,') and d['lxi'] == 'unverified' and 'DSA36106-1110' in d['citation']
          and 'scopehal' in d['citation'] and all('forum' in t['basis'] for t in json.loads(d['transports_json']) if t['name'] in ('scpi-raw', 'vxi-11'))
          and d['emulated'] is True and d['emulator_profile'] == 'dho804')
    check('osc-0 siblings: DHO802/812 are 2 + EXT, DHO812/814 are 100 MHz with rise <= 3.5 ns; the two-channel tables carry no 4-channel entry',
          by['rigol-dho802']['channels'] == 2 and by['rigol-dho802']['ext_trigger'] and by['rigol-dho812']['bandwidth_hz'] == 100e6
          and by['rigol-dho812']['rise_time_ns'] == 3.5 and by['rigol-dho814']['channels'] == 4
          and '4' not in json.loads(by['rigol-dho802']['sample_rate_by_channels_json']))
    for name in ('keysight-lineage', 'tektronix-lineage'):
        r = Instrument(**by[name])
        check('osc-0 %s: a vendor-lineage row with NO numbers (every numeric field -1), lineage named, unverified said in the IDN form' % name,
              r.kind == 'vendor-lineage' and all(getattr(r, f) == -1 for f in ('channels', 'bandwidth_hz', 'sample_rate_sps', 'memory_depth_pts', 'resolution_bits', 'price_usd'))
              and r.lineage in LINEAGES and 'unverified' in r.idn_format and all(t['port'] == -1 for t in json.loads(r.transports_json)))
    check('osc-0 every seed row constructs, has a unique kebab name, a known kind + lineage, and a citation',
          len({r['name'] for r in S}) == len(S) and all(re.fullmatch(r'[a-z0-9-]+', r['name']) for r in S)
          and all(Instrument(**r).kind in KINDS and Instrument(**r).lineage in LINEAGES and r.get('citation') for r in S))


def cards():
    from instruments.custom import catalog as C
    rows = {r['name']: r for r in C.model_rows(None)}
    d = rows['rigol-dho804']
    check('osc-0 TEXT: the card words derive from the numbers (70 MHz; 1.25 GSa/s with 1 ch / 625 MSa/s with 2 ch / 312.5 MSa/s with 4 ch; 25 Mpts ..; 12 bits; scpi-raw:5555)',
          d['bandwidth'] == '70 MHz' and d['sample_rate'] == '1.25 GSa/s with 1 ch / 625 MSa/s with 2 ch / 312.5 MSa/s with 4 ch'
          and d['memory_depth'].startswith('25 Mpts with 1 ch') and d['resolution'] == '12 bits' and d['channels_text'] == '4'
          and 'scpi-raw:5555' in d['transports'] and d['emulator'] == 'yes (dho804)' and d['price'] == 'USD 454', d)
    check('osc-0 TEXT: the DHO802 says "2 + EXT"; a lineage row says unverified for every number and "dialect proof only (...)" for the emulator (osc-5 part 2: no model claimed)',
          rows['rigol-dho802']['channels_text'] == '2 + EXT' and rows['keysight-lineage']['bandwidth'] == 'unverified'
          and rows['keysight-lineage']['sample_rate'] == 'unverified' and rows['keysight-lineage']['emulator'] == 'dialect proof only (keysight-dialect)'
          and rows['keysight-lineage']['transports'].count('(unverified)') == 3)
    check('osc-0 TEXT: the sensitivity range reads "500 uV/div to 10 V/div"', d['sensitivity'] == '500 uV/div to 10 V/div', d['sensitivity'])


def bench_doors():
    from instruments.custom import catalog as C
    from board.custom import bench as B
    from board.custom import bench_seed as S
    B._MEM.clear()
    st, opts = C.get_door(None, {'bench': S.HOME_BENCH}, 'bench-options')
    check('osc-0 OPTIONS: bench-options lists every model with on_bench=0 and can_add only for oscilloscopes',
          st == 200 and {r['name'] for r in opts['rows']} >= {'rigol-dho804', 'keysight-lineage'}
          and all(r['on_bench'] == 0 for r in opts['rows'])
          and {r['name']: r['can_add'] for r in opts['rows']}['rigol-dho804'] is True and {r['name']: r['can_add'] for r in opts['rows']}['keysight-lineage'] is False)
    st, p = C.post_door(None, S.HOME_BENCH, 'add', {'model': 'rigol-dho804'})
    check('osc-0 ADD: 201, the bench lists the DHO804 once with its channels / bandwidth / emulator words', st == 201 and p['ok'] and p['added'] == 'rigol-dho804'
          and p['rows'] == [{'model': 'rigol-dho804', 'title': 'RIGOL DHO804', 'count': 1, 'channels': '4', 'bandwidth': '70 MHz', 'emulator': 'yes (dho804)', 'note': ''}], p)
    st, p = C.post_door(None, S.HOME_BENCH, 'add', {'model': 'rigol-dho804', 'count': 2})
    check('osc-0 ADD again: the count accumulates (3); the bench row counts 3 instruments', st == 201 and p['rows'][0]['count'] == 3
          and next(r for r in B.bench_rows(None) if r['name'] == S.HOME_BENCH)['instruments'] == 3)
    check('osc-0 OPTIONS after add: on_bench=3 for the DHO804', next(r for r in C.get_door(None, {'bench': S.HOME_BENCH}, 'bench-options')[1]['rows'] if r['name'] == 'rigol-dho804')['on_bench'] == 3)
    check('osc-0 REFUSALS: a lineage row (400, names the reason), an unknown model (404 with the known list), a bad count (400), no bench (404), a non-object body (400)',
          C.post_door(None, S.HOME_BENCH, 'add', {'model': 'keysight-lineage'})[0] == 400 and 'lineage' in C.post_door(None, S.HOME_BENCH, 'add', {'model': 'keysight-lineage'})[1]['error']
          and C.post_door(None, S.HOME_BENCH, 'add', {'model': 'nope'})[0] == 404 and 'known' in C.post_door(None, S.HOME_BENCH, 'add', {'model': 'nope'})[1]
          and C.post_door(None, S.HOME_BENCH, 'add', {'model': 'rigol-dho804', 'count': 'x'})[0] == 400
          and C.post_door(None, 'no-such-bench', 'add', {'model': 'rigol-dho804'})[0] == 404 and C.post_door(None, S.HOME_BENCH, 'add', [])[0] == 400)
    st, p = C.post_door(None, S.HOME_BENCH, 'remove', {'model': 'rigol-dho804'})
    check('osc-0 REMOVE: one off (count 2); removing an absent model is 404', st == 200 and p['rows'][0]['count'] == 2
          and C.post_door(None, S.HOME_BENCH, 'remove', {'model': 'rigol-dho814'})[0] == 404)
    C.post_door(None, S.HOME_BENCH, 'remove', {'model': 'rigol-dho804'})
    st, p = C.post_door(None, S.HOME_BENCH, 'remove', {'model': 'rigol-dho804'})
    check('osc-0 REMOVE to zero: the entry is gone and GET /bench lists nothing', st == 200 and p['rows'] == []
          and C.get_door(None, {}, 'bench', S.HOME_BENCH)[1]['rows'] == [])
    st, p = B.post_door(None, '', 'create', {'name': 'osc0-bench'})
    check('osc-0 CREATE (board door) still works and the new bench has an empty instruments list', st == 201 and B.bench('osc0-bench')['instruments_json'] == '[]')
    B._MEM.clear()


def page_and_manifest():
    from instruments.instruments_page import SEED_INSTRUMENTS_PAGE_DISPLAYS as P
    from instruments.instruments_api import InstrumentsAPI  # noqa: F401
    d = json.loads(P[0]['definition'])
    models_tab = next(t for t in d['tabs'] if t['key'] == 'models')
    items = [it for r in models_tab['rows'] for it in r['items']]
    kinds = [it.get('componentProps', {}).get('componentName') for it in items]
    check('osc-0 PAGE: /display/instruments models tab = one `cards` component (grouped by vendor, twelve fields: + Signals / Openness / Data access in osc-6) + one configured table; no api-json-panel',
          P[0]['pageRoute'] == 'instruments' and kinds[0] == 'cards' and items[0]['componentProps']['inputs']['group_by'] == 'vendor'
          and len(items[0]['componentProps']['inputs']['fields']) == 12 and 'api-json-panel' not in P[0]['definition'] and len(items) == 2, kinds)
    sig_tab = next(t for t in d['tabs'] if t['key'] == 'signals')
    sig_items = [it for r in sig_tab['rows'] for it in r['items']]
    check('osc-6 PAGE: a Signals + testability tab (second) = the kinds table, the needs door-form + the verdict table, the options table - every panel configured',
          [t['key'] for t in d['tabs']][1] == 'signals' and [it.get('componentProps', {}).get('componentName') for it in sig_items].count('door-form') == 1 and len(sig_items) == 4
          and all('columns' in (it.get('componentProps') or it) or 'class-rows-table' in json.dumps(it) or it.get('componentProps', {}).get('componentName') == 'door-form' for it in sig_items))
    paths = []
    _walk(d, paths)
    api = open(__file__.replace('instruments_selftest.py', 'instruments_api.py')).read()
    routes = re.findall(r"add\('([^']+)'", api)
    bad = [p for p in paths if not any(re.fullmatch(re.sub(r'\{[^}]+\}', '[^/]+', r), p.split('?')[0]) for r in routes)]
    check('osc-0 PATHS: every path the page uses (%d) is a route in instruments_api.py' % len(paths), paths and not bad, bad)
    from moduleService.manifests import conform
    r = conform('instruments')
    check('osc-0 MANIFEST: pol modules conform instruments is clean (kind library, requires board)', r['ok'] and r.get('kind') == 'library', r.get('findings'))


def signals_and_testability():
    """osc-6: the two open-source scope rows (ScopeFun, DSO138) as cited facts; the signal-kind axis on the pin view's vocabulary; the testability rules
    (channels add up with a shared trigger; bandwidth / bits / per-channel rate never; ETS for repetitive signals; a spare analog channel reads digital)."""
    from instruments.instruments_seed import SEED_INSTRUMENTS as S
    from instruments.instruments_basis import Instrument
    from instruments.custom import catalog as C
    from instruments.custom import sources as SRC
    from instruments.custom import testability as T
    from board.custom import signal_kinds as SK
    from board.custom import bench as B
    from board.custom import bench_seed as BS
    by = {r['name']: r for r in S}
    sf, dso = by['scopefun'], by['jyetech-dso138']
    check('osc-6 SCOPEFUN: 2 analog 10-bit, 100 MHz, 500 / 250 MSa/s by channels, ETS 2 GSa/s, 128 Msa per channel, 12 digital at 250 MSa/s, no SCPI (lineage none, usb3 transport), '
          'software GPLv3 said and the hardware licence unverified said, price = the 2019 campaign with availability unverified, not emulated',
          sf['channels'] == 2 and sf['resolution_bits'] == 10 and sf['bandwidth_hz'] == 100e6 and json.loads(sf['sample_rate_by_channels_json']) == {'1': 500e6, '2': 250e6}
          and sf['ets_sample_rate_sps'] == 2e9 and sf['memory_depth_pts'] == 128e6 and sf['digital_channels'] == 12 and sf['digital_max_rate_sps'] == 250e6 and sf['lineage'] == 'none'
          and json.loads(sf['transports_json'])[0]['name'] == 'usb3' and 'GPLv3' in sf['openness'] and 'unverified' in sf['openness'] and sf['price_usd'] == 899 and 'unverified' in sf['price_basis']
          and sf['emulated'] is False and Instrument(**sf).lineage == 'none')
    check('osc-6 DSO138: 1 channel, 200 kHz, 1 MSa/s, 12 bits, 1024 points, 1 MOhm / 20 pF, 10 mV..5 V/div, 10 us..500 s/div (the manual\'s table quoted in the citation), serial-text '
          'transport said third-party, openness PARTLY with the closed library named and no licence found, price -1 with the 2015 report only in its basis, the MCU read off the schematic',
          dso['channels'] == 1 and dso['bandwidth_hz'] == 200e3 and dso['sample_rate_sps'] == 1e6 and dso['resolution_bits'] == 12 and dso['memory_depth_pts'] == 1024
          and dso['input_impedance_ohm'] == 1e6 and dso['input_capacitance_pf'] == 20 and dso['sensitivity_min_v_div'] == 10e-3 and dso['sensitivity_max_v_div'] == 5
          and dso['timebase_min_s_div'] == 10e-6 and dso['timebase_max_s_div'] == 500 and '"Max realtime sample rate 1MSa/s"' in dso['citation'] and 'STM32F103Cx' in dso['citation']
          and json.loads(dso['transports_json'])[0]['name'] == 'serial-text' and 'third-party' in json.loads(dso['transports_json'])[0]['basis'] and dso['openness'].startswith('PARTLY')
          and 'libdso138.a' in dso['openness'] and dso['price_usd'] == -1 and '2015' in dso['price_basis'] and dso['emulated'] is False)
    rows = {r['name']: r for r in C.model_rows(None)}
    check('osc-6 TEXT: the signals words derive from the numbers (ScopeFun analog x2 + digital x12 at 250 MSa/s + A - B + ETS; the DSO138 one channel, digital on the spare channel, no '
          'differential; the DHO804 analog x4, A - B); openness and data access are on the card',
          rows['scopefun']['signals'] == 'analog x2; digital x12 (logic inputs at 250 MSa/s); differential: by A - B of two analog channels; ETS 2 GSa/s for repetitive signals'
          and rows['jyetech-dso138']['signals'] == 'analog x1; digital: on a spare analog channel (no logic inputs); differential: no (one channel, no native input)'
          and rows['rigol-dho804']['signals'] == 'analog x4; digital: on a spare analog channel (no logic inputs); differential: by A - B of two analog channels'
          and rows['scopefun']['openness_text'].startswith('software GPLv3') and 'serial text dump' in rows['jyetech-dso138']['data_access_text'], rows['scopefun']['signals'])
    check('osc-6 KINDS: the axis rides on the pin view\'s family vocabulary (every family mapped: usb -> differential, analog -> analog, the rest digital, power / ground not signals); '
          'ADC0 / INT1 / USB_D+ / VCC classify; SystemLink and task kinds map onto the same words',
          {r['kind'] for r in C.signal_kind_rows()} == set(SK.SIGNAL_KINDS) and SK.kind_of('ADC0')[0] == 'analog' and SK.kind_of('INT1')[0] == 'digital'
          and SK.kind_of('USB_D+')[0] == 'differential' and SK.kind_of('VCC')[0] == 'undetermined' and 'pv_families' in SK.kind_of('ADC0')[1]
          and SK.kind_of_link('usb') == 'differential' and SK.kind_of_link('uart') == 'digital' and SK.kind_of_task_kind('analog-in') == 'analog' and SK.kind_of_task_kind('pwm-out') == 'digital'
          and SK.kind_of_task_kind('transport') == 'undetermined')
    check('osc-6 READINGS: logic_levels holds the previous level inside the hysteresis band; differential = A - B sample by sample (and refuses unequal axes); the digital source is two levels at the bit period',
          SK.logic_levels([0, 1, 1.6, 1.7, 3.3, 1.7, 1.4, 0], 1.65, 0.2) == [0, 0, 0, 0, 1, 1, 0, 0] and SK.differential([3, 2], [1, 1]) == [2, 1]
          and list(SRC.evaluate({'kind': 'digital', 'bits': [1, 0], 'bit_period_s': 1e-3}, [0, 0.0005, 0.0015])) == [3.3, 3.3, 0.0]
          and SRC.describe({'kind': 'digital', 'bits': [1, 0, 1]}) == 'digital: 3 bits at 0.001 s each, 3.3 / 0 V')
    try:
        SK.differential([1], [1, 2])
        unequal = False
    except ValueError:
        unequal = True
    check('osc-6 READINGS: unequal axes refused', unequal)
    # the testability door on the home bench: four DSO138s against needs
    B._MEM.clear()
    C.post_door(None, BS.HOME_BENCH, 'add', {'model': 'jyetech-dso138', 'count': 4})
    st, p = C.post_door(None, BS.HOME_BENCH, 'testability', {'analog': 4, 'bandwidth_hz': 2e4, 'sample_rate_sps': 5e5, 'bits': 10})
    v = {r['need']: r for r in p['rows']}
    check('osc-6 TESTABILITY: 4 x DSO138 for 4 analog signals at 20 kHz / 500 kSa/s / 10 bits -> CAVEAT: channels add up only with a shared trigger (alignment said, jitter -1); bandwidth '
          'and rate ok per unit (never summed, said); bits ok with the sqrt(N) noise note; the whole verdict is caveat; cost -1 rows not summed',
          st == 200 and p['verdict'] == 'caveat' and v['analog channels']['verdict'] == 'caveat' and 'share a trigger' in v['analog channels']['why'] and '-1' in v['analog channels']['why']
          and v['bandwidth (Hz)']['verdict'] == 'ok' and v['sample rate (Sa/s)']['verdict'] == 'ok' and 'never summed' in v['sample rate (Sa/s)']['why']
          and v['vertical resolution (bits)']['verdict'] == 'ok' and 'sqrt(N)' in v['vertical resolution (bits)']['why'] and p['cost']['units_priced'] == 0 and p['cost']['units'] == 4, p['rows'])
    st, p = C.post_door(None, BS.HOME_BENCH, 'testability', {'analog': 2, 'differential': 1, 'bandwidth_hz': 1e6, 'sample_rate_sps': 5e6})
    v = {r['need']: r for r in p['rows']}
    check('osc-6 TESTABILITY: 1 MHz on 200 kHz scopes -> NO ("never adds up"); 5 MSa/s -> NO with "interleaving ... NOT claimed" and the hint to say repetitive; one differential by A - B '
          'of the two spare channels -> caveat naming common mode and skew; the whole verdict no',
          p['verdict'] == 'no' and v['bandwidth (Hz)']['verdict'] == 'no' and 'NEVER adds up' in v['bandwidth (Hz)']['why'] and v['sample rate (Sa/s)']['verdict'] == 'no'
          and 'NOT claimed' in v['sample rate (Sa/s)']['why'] and 'repeats' in v['sample rate (Sa/s)']['why'] and v['differential signals']['verdict'] == 'caveat'
          and 'common mode' in v['differential signals']['why'], p['rows'])
    C.post_door(None, BS.HOME_BENCH, 'add', {'model': 'scopefun'})
    st, p = C.post_door(None, BS.HOME_BENCH, 'testability', {'analog': 1, 'digital': 14, 'sample_rate_sps': 1e9, 'repetitive': 'true'})
    v = {r['need']: r for r in p['rows']}
    st2, g = C.get_door(None, {'analog': '1', 'sample_rate_sps': '1e9'}, 'testability', BS.HOME_BENCH)
    check('osc-6 TESTABILITY: + a ScopeFun: 14 digital = its 12 logic inputs + spare analog channels (caveat, said); 1 GSa/s on a REPETITIVE signal -> caveat by ETS on the ScopeFun; the same '
          'need not repetitive (GET with query params) -> no; options list the models cheapest first with the unverified price last',
          v['digital channels']['verdict'] == 'caveat' and '12 logic input' in v['digital channels']['why'] and v['sample rate (Sa/s)']['verdict'] == 'caveat'
          and 'REPETITIVE' in v['sample rate (Sa/s)']['why'] and st2 == 200 and {r['need']: r['verdict'] for r in g['rows']}['sample rate (Sa/s)'] == 'no'
          and [o['model'] for o in p['options']][:2] == ['rigol-dho804', 'scopefun'] and p['options'][-1]['price_usd'] == -1, (p['rows'], [o['model'] for o in p['options']]))
    check('osc-6 TESTABILITY: refusals - no bench 404, a non-object body 400, nothing asked -> one row saying so',
          C.post_door(None, 'no-such-bench', 'testability', {})[0] == 404 and C.post_door(None, BS.HOME_BENCH, 'testability', [])[0] == 400
          and C.post_door(None, BS.HOME_BENCH, 'testability', {})[1]['rows'][0]['verdict'] == 'nothing asked')
    B._MEM.clear()


def main():
    facts()
    cards()
    bench_doors()
    signals_and_testability()
    page_and_manifest()
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
