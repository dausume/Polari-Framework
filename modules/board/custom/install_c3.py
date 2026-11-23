"""
@module board.custom.install_c3

ins-c3-1 (AI-Notes/plans/C3_INSTALL_PLAN.md): the ESP32-C3's steps of the firmware installer. installer.py asks board.custom.install_kinds which board a variant, a build or a
target belongs to and, for a C3, calls these (the UNO's own steps stay in installer.py). Nothing here flashes a board by itself: a real flash is flash_c3.flash, reached only
through installer.run (a plan, confirm, this host, a detected board, the gate read again, and the checks below read again).

    work_dir() / build(manager, variant, work, run)      where a C3 build lives / the chip-HAL build of a variant (the call the twin session and `pol firmware prove` make)
    checks(manager, b, gate)                             the three things a REAL plan checks, each `{name, ok, words}`: chip-hal, image-is-the-files, runs-on-this-image
    plan_twin(manager, b, variant) / plan_board(b, port) the plan's command words, engine, programmer and what would be stamped
    run_twin(manager, b) / run_board(manager, p, b, t)   the install itself -> the InstallRecord's fields (a twin session / esptool through flash_c3)
    limits(b) / sizes(b) / twin_status(manager) / MODES  the page document's numbers and words (a limit the build does not state is None: the page says "not stated")
"""
import hashlib
import json
import os

from board.custom import board_engines as be, engine_run, flash as F, flash_c3, gen, gen_c3, light_c3_run as R, twin_kinds, variants_c3 as V3

CHECK_HAL, CHECK_FILES, CHECK_RUNS = 'chip-hal', 'image-is-the-files', 'runs-on-this-image'
ENGINE = 'qemu-esp32c3'   # the engine board_engines names for the pin-model QEMU a twin session runs
CITE = ("the app partition of the template's partitions.csv (build_c3.APP_PARTITION_BYTES); the RAM limit is DRAM total from the build's own idf.py size report "
        "(a build that did not record one states none)")


def work_dir():
    return gen_c3.default_work()


def store_of(b):
    """The build's own store folder (its firmware_build.json, flash_args.txt and the three files), or '' when the record names no image."""
    return os.path.dirname(b.get('hex_path') or '')


def _app(variant):
    try:
        return V3.resolve(V3.find(variant))['app']
    except V3.VariantRefused as e:
        raise gen.GenRefused(str(e))


def build(manager, variant, work=None, run=None):
    """-> the build record. The light app is built exactly as the twin session and `pol firmware prove` build it (chip HAL, pin_shim 0), so the sha256 is the same number;
    another C3 variant has no pads and is built with no knobs. `run` (tests) replaces the engine call of build_c3."""
    work = work or work_dir()
    os.makedirs(work, exist_ok=True)
    light = _app(variant) == 'light'
    try:
        if run is None and light:
            return R.build(work, variant, pin_shim=0)
        gen_c3.gen_c3(variant, work, **({'pin_shim': 0} if light else {}))
        from board.custom import build_c3
        return build_c3.build('c3', work, **({'run': run} if run else {}))
    except engine_run.EngineRefused as e:
        raise gen.GenRefused('no ESP engines can build this here: %s' % e)


# ------------------------------------------------------------------ the checks of a real plan
def _chk(name, ok, words):
    return {'name': name, 'ok': bool(ok), 'words': words}


def _check_hal(b):
    variant = b.get('variant', '')
    try:
        app = V3.resolve(V3.find(variant))['app']
    except V3.VariantRefused:
        return _chk(CHECK_HAL, False, 'the build names the variant %r, which the ESP32-C3 variants do not list, so its pins cannot be told: build a listed variant from the installer' % variant)
    if app != 'light':
        return _chk(CHECK_HAL, True, '%s uses no pad, so it has no shim build: the image the twin ran is the image a board gets' % variant)
    if R.knobs_of(b)['pin_shim'] != 0:
        return _chk(CHECK_HAL, False, 'this is the shim build: its pins are RAM, it drives no pad. A real board needs the chip-HAL build of %s (build it from the installer)' % variant)
    return _chk(CHECK_HAL, True, 'this is the chip-HAL build of %s (pin_shim 0): its pins are the chip\'s pads' % variant)


def _check_files(b):
    store, path = store_of(b), b.get('hex_path') or ''
    fa = os.path.join(store, 'flash_args.txt') if store else ''
    if not (path and os.path.isfile(path)):
        return _chk(CHECK_FILES, False, 'the merged image of this build is not on this host, so it cannot be compared with the files esptool would write: build it here')
    if not os.path.isfile(fa):
        return _chk(CHECK_FILES, False, 'no flash_args.txt beside the build (%s), so the files esptool would write are not known: build it again from the installer' % store)
    image = open(path, 'rb').read()
    if b.get('artifact_sha256') and hashlib.sha256(image).hexdigest() != b['artifact_sha256']:
        return _chk(CHECK_FILES, False, 'the merged image on disk is not the one this build recorded (sha256 %s…, the record says %s…): what was simulated is not what would be written; build it again'
                    % (hashlib.sha256(image).hexdigest()[:16], b['artifact_sha256'][:16]))
    pairs = flash_c3.parse_flash_args(open(fa).read())[1]
    total = 0
    for off, name in pairs:
        fp = os.path.join(store, name)
        if not os.path.isfile(fp):
            return _chk(CHECK_FILES, False, 'the file %s that esptool writes at 0x%x is missing from the build store: what was simulated cannot be compared with what would be written; build it again' % (name, off))
        data = open(fp, 'rb').read()
        if image[off:off + len(data)] != data:
            return _chk(CHECK_FILES, False, 'the file %s (esptool writes it at 0x%x) differs from the same place in the image the twin ran: what was simulated is not what would be written'
                        % (name, off))
        total += len(data)
    return _chk(CHECK_FILES, True, 'the %d files esptool writes are the image the twin ran, byte for byte (%d bytes at %s)' % (len(pairs), total, ', '.join('0x%x' % o for o, _ in pairs)))


def _run_sha(manager, name):
    from board.custom.installer import _by_name
    r = _by_name(manager, 'ScenarioRun', name) if name else None
    try:
        return json.loads(getattr(r, 'observed_json', '') or '{}').get('sha256', '') if r is not None else ''
    except ValueError:
        return ''


def _check_runs(manager, b, gate):
    from board.custom import sim_gate as G
    sha, bad, n = b.get('artifact_sha256', ''), [], 0
    for p in gate.get('purposes') or []:
        if p.get('status') not in G.PROVEN:
            continue   # not proven at all: the gate's own words
        n += 1
        got = _run_sha(manager, p.get('run', ''))
        if got != sha:
            bad.append('Purpose %s was proved on another image (%s…), not this one (%s…)' % (p['purpose'], got[:16], sha[:16]) if got
                       else 'Purpose %s: its run %s names no image, so it does not count for this one (%s…)' % (p['purpose'], p.get('run') or '-', sha[:16]))
    if bad:
        return _chk(CHECK_RUNS, False, '%s. Run them again on this image: %s' % ('; '.join(bad), G.prove_command(b.get('variant', ''))))
    return _chk(CHECK_RUNS, True, ('the %d proving runs name this image (sha256 %s…)' % (n, sha[:16])) if n else 'no Purpose has a passed run yet, so there is nothing to compare (the gate says which)')


def checks(manager, b, gate):
    """The checks of a REAL plan (and of its run). runs-on-this-image only when the gate holds this config."""
    out = [_check_hal(b), _check_files(b)]
    if gate and gate.get('gated'):
        out.append(_check_runs(manager, b, gate))
    return out


# ------------------------------------------------------------------ plans
def plan_twin(manager, b, variant):
    where = be.resolve_sessions('esp')
    sha = b.get('artifact_sha256', '')
    refused = ''
    try:
        twin_kinds.admit(twin_kinds.C3, variant)
    except twin_kinds.KindRefused as e:
        refused = str(e)
    if not refused and where['how'] != be.REMOTE:
        refused = where['why']
    return {'argv': [], 'wrapper': [], 'where': where, 'programmer': 'twin session (the pin-model QEMU)', 'engine': ENGINE, 'refused': refused,
            'argv_text': ('no command line: the backend asks the ESP engines worker for a twin session with this image (sha256 %s…), the chip\'s pin layout and the LED-to-sense wire' % sha[:16]),
            'will_stamp': 'the twin session runs %s (sha256 %s); no BoardInstance is stamped, it is the twin' % (b['name'], sha[:16])}


def plan_board(b, port, instance_name=''):
    store, sha = store_of(b), b.get('artifact_sha256', '')
    stamp = 'BoardInstance %s: firmware_sha = %s…, last_flash_at = the run time; FirmwareBuild %s → flashed' % (instance_name or '<the detected board>', sha[:16], b['name'])
    out = {'argv': [], 'text': '', 'wrapper': [], 'programmer': flash_c3.PROGRAMMER, 'engine': 'esptool', 'will_stamp': stamp, 'refused': '',
           'where': be.resolve('esptool', flash=True)}
    if not store or not os.path.isfile(os.path.join(store, 'firmware_build.json')):
        out['refused'] = 'the build store of %s holds no record of this build (%s), so esptool\'s command cannot be made: build it again from the installer' % (b['name'], store or 'no folder named')
        return out
    try:
        p = flash_c3.plan(store, port or '')
    except (gen.GenRefused, F.FlashRefused) as e:
        out['refused'] = 'esptool\'s command cannot be made for %s: %s' % (b['name'], e)
        return out
    return dict(out, argv=p['argv'], text=p['text'], where=p['engine'])


# ------------------------------------------------------------------ runs
def _failed(verify, why):
    return {'verdict': 'failed', 'verified_bytes': 0, 'firmware_sha': '', 'verify': verify, 'log_tail': str(why)[-1500:], 'notes': '%s: %s' % (verify, str(why)[:300])}


def run_twin(manager, b):
    """A twin session started with this build's own image. Installed when it is running and its firmware sha256 is the build's. Other sessions are left alone; no token is kept."""
    from board.custom import twin_sessions as TS
    try:
        v = TS.start(manager, b['variant'], hex_bytes=open(b['hex_path'], 'rb').read(), owner='installer')
    except TS.SessionRefused as e:
        return _failed('the ESP engines worker did not start a twin session', e)
    v.pop('token', None)
    fw, sha = v.get('firmware') or {}, b.get('artifact_sha256', '')
    if v.get('state') != 'running' or fw.get('sha256') != sha:
        try:
            TS.stop(manager, v['name'])
        except TS.SessionRefused:
            pass
        return _failed('the twin session is not running this build', 'session %s is %s with sha256 %s…, the build is %s…' % (v['name'], v.get('state'), str(fw.get('sha256'))[:16], sha[:16]))
    return {'verdict': 'installed', 'verified_bytes': int(fw.get('bytes') or 0), 'firmware_sha': sha,
            'verify': 'the ESP engines worker started twin session %s with this image: %d bytes, sha256 %s… — the same number as the build' % (v['name'], int(fw.get('bytes') or 0), sha[:16]),
            'log_tail': '', 'notes': 'installed into THE TWIN session %s (the pin-model QEMU): it is the twin with the pin model, not a chip. Press it on the Sim bench or with '
                                     '`pol board twin session inject %s set GPIO3 0`' % (v['name'], v['name'])}


def run_board(manager, p, b, t, flash_run=None):
    kw = {'run': flash_run} if flash_run else {}
    store = store_of(b)
    try:
        res = flash_c3.flash(store, port=p.port, yes=True, instance=t['instance'], **kw)
        pairs = flash_c3.parse_flash_args(open(os.path.join(store, 'flash_args.txt')).read())[1]
        n = sum(os.path.getsize(os.path.join(store, f)) for _, f in pairs)
    except (F.FlashRefused, engine_run.EngineRefused, gen.GenRefused) as e:
        return {'verdict': 'failed', 'verify': 'esptool did not verify the write', 'log_tail': str(e)[-1500:], 'notes': 'flash refused: %s' % str(e)[:300]}
    return {'verdict': 'installed', 'verified_bytes': n, 'firmware_sha': b['artifact_sha256'], 'verify': 'esptool wrote %d files and verified the hash of each: %d bytes' % (len(pairs), n),
            'log_tail': (res.get('log') or '')[-1500:], 'notes': 'installed on %s at %s' % (p.instance, p.port), '_instance': t['instance']}


# ------------------------------------------------------------------ the page's document
def limits(b=None):
    """(flash_max, ram_max, cite): the app partition; the RAM limit is the build's own DRAM total (None = not stated)."""
    ram = None
    try:
        ram = (json.loads((b or {}).get('repro_json') or '{}').get('conditions', {}).get('limits', {}).get('dram_total_b')) or None
    except (ValueError, AttributeError):
        pass
    from board.custom import build_c3
    return build_c3.APP_PARTITION_BYTES, ram, CITE


def sizes(b):
    return (int(b['flash_bytes']) if b.get('flash_bytes') else None), (int(b['ram_bytes']) if b.get('ram_bytes') else None)


def twin_status(manager):
    from board.custom import twin_sessions as TS
    rows = sorted((TS.view(r) for r in TS._rows(manager) if r.board == V3.BOARD and r.state == 'running'), key=lambda v: v['started_at'])
    last = rows[-1] if rows else {}
    return {'state': 'up' if rows else 'down', 'session': last.get('name'), 'variant': last.get('config'), 'hex_sha256': (last.get('firmware') or {}).get('sha256'),
            'started_at': last.get('started_at'), 'sessions': [v['name'] for v in rows]}


MODES = [{'name': 'sim', 'title': 'Sim install', 'target_kind': 'twin', 'words': 'a twin session on the pin-model QEMU (the ESP engines worker), running the chip-HAL image: the image a '
                                                                             'chip is flashed with. Install here first, run the four Purposes, press it on the Sim bench, then tick what you saw.'},
         {'name': 'real', 'title': 'Real install', 'target_kind': 'board', 'words': 'a detected board over USB. Offered after the four Purposes passed on this image and a person '
                                                                               'ticked it; esptool writes the three files and checks the hash of each.'}]

#: ins-c3-2: the words the Install Firmware page shows for a C3. No bridge is attached after a twin install: the record names the session and how to press it.
PAGE = {'twin_note': 'The twin session runs the very same flash image a real ESP32-C3 is flashed with (the chip-HAL build, on the pin-model QEMU). A real install '
                     'is offered only after the four Purposes passed on this image here and you confirmed what you saw.',
        'no_board': 'No ESP32-C3 has been plugged in here yet. Plug one in and press Refresh, or do the sim install first. A real plan can still be read with '
                    '`pol board install c3 --real`: it shows the command and its checks and runs nothing.',
        'artifact': 'flash image', 'on_twin': 'the twin session (pin-model QEMU)', 'attach': False}
