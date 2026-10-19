"""
@module cmod.custom.glue_build_light

The twin-equivalence proof of `uno-light-graph` (slice ucd-light): the GENERATED glue is built by `make` alone and compared
frame by frame against the hand-written light.c (variant uno-light) on the simavr twin, under ONE stimulus that exercises both
directions — N debounced presses on D2 (the button up) and then SET_LED 1 / SET_LED 0 injected over the serial link (the
command down). Registered in glue_build.STIMULI; same shape as the button-clock graph's proof (glue_build._prove_button_clock).
"""
import datetime

FIELDS = ('boot_session', 'led_on', 'toggles', 'source', 'status', 'name')


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def stimulus():
    """-> (argv, files, seconds): 2 presses, then SET_LED 1, then SET_LED 0 (spaced past the debounce and the frame period)."""
    from board.custom import light_twin as LT
    pinat, end = LT.press_pinat(2)
    on_c, off_c = end + 1600000, end + 6400000
    _, spec = LT._spec()
    files = {'on.bin': LT.cmd_frame(spec, 1, led_on=True), 'off.bin': LT.cmd_frame(spec, 2, led_on=False)}
    seconds = (off_c + 3200000) / 16000000.0
    argv = LT._argv(seconds, pinat + ['--inject', 'on.bin@%d' % on_c, '--inject', 'off.bin@%d' % off_c])
    argv[argv.index('--uart-out') + 2:argv.index('--uart-out') + 2] = ['--uart-tx-log', 'tx.bin']
    return argv, files, seconds


def _frames(r):
    from board.custom import light_twin as LT
    fr, _ = LT.decode(r['uart'])
    return fr


def prove(ref, mk):
    import hashlib
    from cmod.custom import glue_build as GB
    argv, files, seconds = stimulus()
    rr, rg = GB.run_twin(ref['hex'], argv, files), GB.run_twin(mk['hex'], argv, files)
    fa, fb = _frames(rr), _frames(rg)
    diffs = []
    if len(fa) != len(fb):
        diffs.append('frame count %d vs %d' % (len(fa), len(fb)))
    for i, (x, y) in enumerate(zip(fa, fb)):
        for k in ('seq',) + FIELDS:
            if x.get(k) != y.get(k):
                diffs.append('frame %d %s: %r vs %r' % (i, k, x.get(k), y.get(k)))
    sha = lambda b: hashlib.sha256(b).hexdigest()   # noqa: E731
    return {'equivalent': not diffs, 'frames_compared': min(len(fa), len(fb)), 'frames_hand': len(fa), 'frames_glue': len(fb),
            'fields_compared': ['seq'] + list(FIELDS), 'differences': diffs[:20], 'n_differences': len(diffs),
            'raw_uart_identical': rr['uart'] == rg['uart'], 'uart_sha256': {'hand': sha(rr['uart']), 'glue': sha(rg['uart'])},
            'reference': {'variant': 'uno-light-unsensed', 'built_by': 'board gen + board build (the shipped pipeline)',
                          'hex_sha256': ref['hex_sha256'], 'size_text': ref['size_text'], 'size_data': ref['size_data'], 'size_bss': ref['size_bss']},
            'glue': {'hex_sha256': mk['hex_sha256'], 'size_text': mk['sizes'].get('.text', 0), 'size_data': mk['sizes'].get('.data', 0),
                     'size_bss': mk['sizes'].get('.bss', 0), 'built_by': 'make alone (%s %s)' % (mk['how'], mk['where'])},
            'hex_identical': ref['hex_sha256'] == mk['hex_sha256'],
            'cycles': {'total_hand': (rr['final'] or {}).get('cycles'), 'total_glue': (rg['final'] or {}).get('cycles'),
                       'frame_tx_cycle_delta_min': None, 'frame_tx_cycle_delta_max': None,
                       'first_frame_cycle_hand': None, 'first_frame_cycle_glue': None},
            'stimulus': {'seconds': round(seconds, 3), 'seed': '-', 'adc0_ramp_mv': '-',
                         'commands': ['2 press(es) on D2', 'SET_LED led_on=1', 'SET_LED led_on=0'], 'argv': ['polari-avr-twin'] + argv},
            'first_commanded_frame': next((i for i, f in enumerate(fb) if f.get('source') == 'command'), None),
            'samples': [dict(seq=f.get('seq'), **{k: f.get(k) for k in FIELDS}) for f in (fb[:1] + fb[-1:])],
            'twin': {'how': rg.get('how'), 'where': rg.get('where'), 'simulator': 'polari-avr-twin (libsimavr 1.6, prf-board-engines:trixie)'},
            'proven_at': _now()}
