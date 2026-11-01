"""board_clock_skew_selftest - tmp-6: the timing band forced into a firmware run (board.custom.uart_sampling + board.custom.clock_skew_run).
The receiver model against its closed form and the datasheet's equations, the 16U2's divisor from its own firmware, the link band of each
build, then (SKIPPING honestly without a simavr twin) the UNO firmware run at the resonator's band and just inside / outside the link band,
and the door + the Board Details table."""
import json
import tempfile


def run_clock_skew(check):
    from board.custom import uart_sampling as US
    from board.custom import clock_skew_run as C
    models = {u: (US.window(u, phases=64), US.model_limits(u), US.rate_limits(u)) for u in (0, 1)}
    check('TMP-6 THE RECEIVER SAMPLED BIT BY BIT (DS40002061B / 7799D section 20.8 / 18.8: start on a low after a high, samples 8-9-10 or 4-5-6 by '
          'majority, the next start only after the last voting sample) fails exactly where its closed form says: 8N1 94.74 .. 103.90 %, U2X '
          '94.74 .. 102.56 % (bisection over 64 phases, within 2e-4) - one sample from the datasheet\'s own equations (95.36 .. 104.58 %, '
          '96.00 .. 103.90 %), which count the first voting sample for a slow sender and the middle one for a fast one',
          all(abs(w[0] - m[0]) < 2e-4 and abs(w[1] - m[1]) < 2e-4 for w, m, _ in models.values())
          and abs(models[0][2][0] - 144 / 151.0) < 1e-12 and abs(models[1][2][1] - 80 / 77.0) < 1e-12
          and abs(models[0][1][1] - 160 / 154.0) < 1e-12 and abs(models[1][1][0] - 72 / 76.0) < 1e-12, models)
    lim1, lim0 = C.limits(1, 16), C.limits(0, 8)
    check('TMP-6 THE FAR END IS THE UNO\'S 16U2 AS ITS FIRMWARE SETS IT (arduino-usbserial: U2X1 and SERIAL_2X_UBBRVAL, 57600 the exception): '
          'UBRR1 16 at 115200 (117647 Bd, the SAME +2.1 % as the 328P\'s U2X build) -> the shipped build holds for a 328P clock within -2.50 .. '
          '+2.56 % (the resonator\'s +-1.0 % fits); the U2X0 build (111111 Bd) holds only for a clock 1.91 .. 8.60 % FAST - never at nominal',
          C.peer_divisor(115200) == (16, 1) and C.peer_divisor(57600) == (16, 0) and abs(lim1['lo_pct'] + 2.5) < 1e-6
          and abs(lim1['hi_pct'] - 2.5641) < 1e-3 and abs(lim0['lo_pct'] - 1.9118) < 1e-3 and abs(lim0['hi_pct'] - 8.5973) < 1e-3,
          (lim1, lim0))
    hot = C.run_at(85.0)
    rc = C.run_at(25.0, clock='atmega328p-rc-user')
    check('TMP-6 NOTHING IS GUESSED: at 85 C the resonator is unrated (no corner run); an 8 MHz RC clock needs its own build (not run)',
          not hot['ok'] and 'unrated' in hot['why'] and not rc['ok'] and 'own build' in rc['why'], (hot['why'], rc['why']))
    from firmwarefaults.custom import fault_engines as fe
    if not fe.available():
        check('SKIP tmp-6 (the firmware run at temperature): no simavr twin here', True)
        return
    home = tempfile.mkdtemp(prefix='tmp6-')
    a = C.run_at(25.0, u2x=1, home=home)
    rows = {r['corner']: r for r in a.get('rows', [])}
    check('TMP-6 THE SHIPPED FIRMWARE AT 25 C, ITS CLOCK AT -1 / 0 / +1 %% (the resonator\'s band): every byte decoded both ways, the command done '
          'and echoed, and its uptime_ms runs (1+e) x true time - measured within 600 ppm (1 ms over 2 s)',
          a['ok'] and set(rows) == {'low', 'nominal', 'high'} and all(r['verdict'].startswith('link holds') and r['board_did_command'] == 'yes'
                                                                     and r['host_saw_echo'] == 'yes' and abs(r['uptime_drift_ppm'] - r['expected_drift_ppm']) < 600
                                                                     for r in rows.values()),
          [(k, r.get('verdict'), r.get('uptime_drift_ppm'), r.get('expected_drift_ppm')) for k, r in rows.items()])
    b = C.run_at(25.0, u2x=0, home=home)
    nb = {r['corner']: r for r in b.get('rows', [])}
    check('TMP-6 THE U2X0 BUILD AGAINST THE REAL 16U2 FAILS EVEN AT NOMINAL: the 16U2\'s bytes come 5.9 % fast for the 328P\'s 8N1 receiver, so '
          'the command never lands (the twin alone, with no bit timing, never shows this)',
          b['ok'] and all(r['board_did_command'] == 'no' and r['verdict'].startswith('link BROKEN') for r in nb.values()),
          [(k, r.get('verdict'), r.get('cmd_bytes_intact')) for k, r in nb.items()])
    edge = {}
    for name, pct in (('inside-low', lim1['lo_pct'] + 0.3), ('outside-low', lim1['lo_pct'] - 0.3), ('inside-high', lim1['hi_pct'] - 0.3),
                      ('outside-high', lim1['hi_pct'] + 0.3)):
        edge[name] = C.run_at(25.0, u2x=1, ppm=pct * 1e4, home=home)['rows'][0]
    check('TMP-6 THE RUN BREAKS WHERE THE BAND SAYS: 0.3 % inside either edge every byte decodes; 0.3 % outside, bytes break',
          all(edge[k]['verdict'].startswith('link holds') for k in ('inside-low', 'inside-high'))
          and all(not edge[k]['verdict'].startswith('link holds') for k in ('outside-low', 'outside-high')),
          {k: (r['device_clock_pct'], r['verdict']) for k, r in edge.items()})
    import falcon
    import falcon.testing as ft
    from board.footholds_api import FootholdsAPI
    from board.board_details_page import BOARD_DETAILS_PAGES
    app = falcon.App()

    class _S(object):
        falconServer = app
    FootholdsAPI(polServer=_S(), manager=None)
    cl = ft.TestClient(app)
    bad = cl.simulate_post('/api/board/timing-run/arduino-uno-r3', body=json.dumps({'temp_c': 25, 'u2x': 2}))
    other = cl.simulate_post('/api/board/timing-run/feather-m0', body=json.dumps({'temp_c': 25}))
    post = cl.simulate_post('/api/board/timing-run/arduino-uno-r3', body=json.dumps({'temp_c': 25, 'u2x': 1}))
    got = cl.simulate_get('/api/board/details/datasheet/arduino-uno-r3/timing-run')
    corners = cl.simulate_get('/api/board/details/datasheet/arduino-uno-r3/timing-run-corners')
    trow = {r['u2x']: r for r in got.json['rows']}
    tdef = BOARD_DETAILS_PAGES[0]['definition']
    tdef = tdef if isinstance(tdef, str) else json.dumps(tdef)
    tables = [t for t in ('bd-timing-run', 'bd-timing-run-corners') if '"%s"' % t in tdef]
    check('TMP-6 THE DOOR AND THE TAB: POST /api/board/timing-run/{board} refuses u2x 2 (400) and a board with no template firmware (404); the '
          'Board Details timing-run rows carry each build\'s verdict and band, the corners table the newest runs; the tab edits temp_c into '
          'the door with the row\'s u2x',
          bad.status_code == 400 and other.status_code == 404 and post.status_code == 200 and trow[1]['verdict'].startswith('holds at every corner')
          and trow[1]['link_band_pct'] == '-2.50 .. +2.56' and len(corners.json['rows']) == 6 and len(tables) == 2
          and '/api/board/timing-run/{board}' in tdef and '{u2x}' in tdef,
          (bad.status_code, other.status_code, post.status_code, trow, len(corners.json['rows']), len(tables)))
