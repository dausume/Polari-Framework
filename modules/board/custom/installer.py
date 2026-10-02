"""
@module board.custom.installer

THE FIRMWARE INSTALLER, server side (brd-fi, plan §7a): detect → the builds that fit → DRY-RUN → confirm → install →
result, over rows, on the host that holds the port. His intent: "test different kinds of things on the arduino uno to
see if it works" — so the loop is: pick a variant, build it, plan, install, watch it run, pick another.

  document(manager)                 GET  /api/board/installer — one document for the page
  build_variant(manager, variant)   POST /api/board/installer/build — gen (against THIS server's contracts) + build
  plan(manager, instance, build)    POST /api/board/installer/plan  — an InstallPlan row: the exact argv, engine,
                                    adapter, compat, what will be stamped. Nothing is opened.
  run(manager, plan, confirm)       POST /api/board/installer/run   — needs the plan AND confirm=true, re-checks compat,
                                    and runs ONLY on this server's own host (a plan for another host is refused,
                                    naming it). The argv is the plan's — fixed when the plan was made, never taken
                                    from the request. → an InstallRecord row.

Targets: a detected UNO on this host (`board present`, a port) — avrdude through the ladder (board.custom.flash, the
read-back verify) — or THE TWIN (`twin:arduino-uno-r3`): simavr loads the SAME .hex (board.custom.twin); its loaded
flash byte count is the read-back. The twin counts as the device for the proof, and every record says which it was.

Refusals are plain words and map to exit 3 in the CLI (InstallRefused.code): stale-header / unknown-class firmware,
no plan, no confirm, the wrong host, a build that is not on this host.
"""
import datetime
import json
import os
import time

from board.custom import compat, gen, variants as V

UNO = 'arduino-uno-r3'
TWIN = 'twin:%s' % UNO
TWIN_TCP = int(os.environ.get('BOARD_INSTALLER_TWIN_TCP', '9831'))
TWIN_LINK = os.environ.get('BOARD_INSTALLER_TWIN_LINK', '/tmp/polari-uno-twin-uart')


class InstallRefused(RuntimeError):
    code = 3

    def __init__(self, msg, status='409 Conflict', **extra):
        super().__init__(msg)
        self.status = status
        self.extra = extra


def this_host():
    return os.uname().nodename


def _now():
    return datetime.datetime.now().isoformat(timespec='seconds')


def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values()) if manager is not None else []


def _by_name(manager, cls, name):
    return next((r for r in _rows(manager, cls) if getattr(r, 'name', '') == name), None)


def _save(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 — an in-memory manager (selftest) has no db
        pass


def upsert(manager, cls_obj, fields):
    """Create or update the row named fields['name'] (constructor fields only)."""
    import inspect
    allowed = set(inspect.signature(cls_obj.__init__).parameters) - {'self', 'manager'}
    f = {k: v for k, v in fields.items() if k in allowed}
    row = _by_name(manager, cls_obj.__name__, f['name'])
    if row is None:
        row = cls_obj(manager=manager, **f)
    else:
        for k, v in f.items():
            setattr(row, k, v)
    _save(manager, row)
    return row


def _fields(row, keys):
    return {k: (row.get(k, '') if isinstance(row, dict) else getattr(row, k, '')) for k in keys}


def work_dir():
    return gen.default_work(UNO)


# ------------------------------------------------------------------ builds
def all_builds(manager, work=None):
    """FirmwareBuild rows ∪ the local build store (a build the CLI made before the server saw it is still installable
    here). The store's record wins for hex_path (it is THIS host's file)."""
    out = {}
    for r in _rows(manager, 'FirmwareBuild'):
        out[r.name] = {k: v for k, v in vars(r).items() if not k.startswith('_')}
    for rec in gen.stored_builds(work or work_dir()):
        out[rec['name']] = dict(out.get(rec['name'], {}), **rec)
    return out


def find_build(manager, name, work=None):
    b = all_builds(manager, work).get(name)
    if b is None:
        raise InstallRefused('no build named %r — build a variant first (POST /api/board/installer/build or pol board gen + build)' % name, '404 Not Found')
    return b


def build_variant(manager, variant, work=None, run=None, instance_index=None):
    """gen the variant against THIS server's contracts (its live exposure, else the pinned snapshot) + build through
    the ladder; the FirmwareBuild row is upserted. Returns the build record. brd-wire: instance_index = this build's
    index among the variant's bridge's bound instances (uno-pair: build it with 0 and with 1)."""
    from board.custom import build as B
    from board.board_basis import FirmwareBuild
    work = work or work_dir()
    try:
        gen.gen('uno', work=work, variant=variant, manager=manager, variant_rows=_rows(manager, 'FirmwareVariant'),
                instance_index=instance_index)
        rec = B.build('uno', work, **({'run': run} if run else {}))
    except gen.GenRefused as e:
        raise InstallRefused(str(e), '400 Bad Request')
    if rec['state'] == 'built':
        rec = gen.read_record(gen.store_dir(work, rec['name']))
    upsert(manager, FirmwareBuild, gen.row_fields(rec))
    return rec


# ------------------------------------------------------------------ targets
def detected(scan=None, manager=None):
    """This host's devices matched against the definitions (a live scan; a container sees no host USB)."""
    from board.custom.detect import match, scan_host
    from board.custom.register_map import board_rows, adapter_rows
    boards = _rows(manager, 'BoardDefinition') or board_rows()
    adapters = _rows(manager, 'AdapterDefinition') or adapter_rows()
    try:
        snap = scan if scan is not None else scan_host()
    except Exception as e:  # noqa: BLE001
        return {'instances': [], 'unadmitted': [], 'summary': {'boards': 0, 'adapters': 0, 'unadmitted': 0}, 'error': str(e)}
    return match(snap, boards, adapters)


def target(instance, scan=None, manager=None):
    """The install target: the twin, or a detected board on THIS host (a live scan first, then BoardInstance rows)."""
    if instance in (TWIN, 'twin'):
        return {'name': TWIN, 'kind': 'twin', 'definition': UNO, 'host': this_host(), 'port': TWIN_LINK, 'adapter': ''}
    inst = next((i for i in detected(scan, manager)['instances'] if i.get('name') == instance), None)
    if inst is None:
        row = _by_name(manager, 'BoardInstance', instance)
        inst = _fields(row, ('name', 'definition', 'definition_kind', 'state', 'host', 'by_id_path', 'port', 'target_board')) if row else None
    if inst is None:
        raise InstallRefused('no device %r is seen — plug it in and detect (pol board detect --push), or install into the twin (%s)' % (instance, TWIN), '404 Not Found')
    if inst.get('definition_kind') == 'adapter':
        if not inst.get('target_board'):
            raise InstallRefused('%s is an adapter with no target named — say which board is wired to it first (BoardInstance.target_board)' % instance)
        board, adapter = inst['target_board'], inst['definition']
    else:
        board, adapter = inst.get('definition'), ''
    if board != UNO:
        raise InstallRefused('%s is a %s — only the UNO has firmware variants so far (plan §8a: the rest are roads)' % (instance, board))
    return {'name': inst['name'], 'kind': 'board', 'definition': board, 'host': inst.get('host', ''), 'adapter': adapter,
            'port': inst.get('by_id_path') or inst.get('port') or '', 'instance': inst}


# ------------------------------------------------------------------ plan
def _twin_argv(hex_path, stim):
    from board.custom import board_engines as be, twin
    adc0, extra = stim
    where = be.resolve('avr-twin')
    args = twin.twin_args(hex_path, TWIN_TCP, adc0, '', True, extra)
    if where['how'] == be.LOCAL_IMAGE:
        wrapper = ['docker', 'run', '-d', '--name', 'prf-board-twin-%s' % UNO, '-p', '127.0.0.1:%d:9831' % TWIN_TCP, '-v',
                   '%s:/fw:ro' % os.path.dirname(hex_path), where['where'], 'polari-avr-twin'] + twin.twin_args('/fw/firmware.hex', 9831, adc0, '', True, extra)
    else:
        wrapper = []
    return ['polari-avr-twin'] + args, wrapper, where


def plan(manager, instance, build_name, work=None, scan=None):
    from board.board_basis import InstallPlan
    b = find_build(manager, build_name, work)
    t = target(instance, scan, manager)
    c = compat.check(b, manager)
    variant = b.get('variant', '')
    n = len([p for p in _rows(manager, 'InstallPlan') if getattr(p, 'build', '') == b['name']]) + 1
    base = {'name': 'plan-%s-%d' % (b['name'], n), 'build': b['name'], 'variant': variant, 'instance': t['name'], 'target_kind': t['kind'],
            'host': t['host'] or this_host(), 'port': t['port'], 'adapter': t['adapter'], 'compat': c['verdict'], 'compat_why': c['plain'],
            'artifact_sha256': b.get('artifact_sha256', ''), 'planned_at': _now()}
    why = []
    if b.get('state') not in ('built', 'flashed') or not b.get('hex_path'):
        why.append('build %s is %r, not built — nothing to install' % (b['name'], b.get('state')))
    elif not os.path.isfile(b['hex_path']):
        why.append('the .hex of %s is not on this host (%s) — build it here' % (b['name'], this_host()))
    if b.get('board_definition') != t['definition']:
        why.append('build %s is for %s, the target is a %s' % (b['name'], b.get('board_definition'), t['definition']))
    if c['verdict'] != 'compatible':
        why.append('REFUSED (%s): %s' % (c['verdict'], c['plain']))
    hex_path = b.get('hex_path') or '{hex}'
    if t['kind'] == 'twin':
        argv, wrapper, where = _twin_argv(hex_path, V.stimulus(_variant(manager, variant)))
        base.update(programmer='simavr-load (the twin)', engine='avr-twin',
                    will_stamp='the twin runs %s (sha256 %s); no BoardInstance is stamped — it is the twin' % (b['name'], base['artifact_sha256'][:16]))
    else:
        from board.custom import flash
        argv = flash.argv_for(UNO, t['port'] or '{port}', hex_path)
        from board.custom import board_engines as be
        where = be.resolve('avrdude', flash=True)
        wrapper = []
        if where['how'] == be.LOCAL_IMAGE:
            from board.custom import engine_run
            dev = os.path.realpath(t['port']) if t['port'] else '{port}'
            wrapper = engine_run.docker_prefix(where['where'], [(dev, flash.INNER_PORT)])(os.path.dirname(hex_path))[:-1] + [where['where']] \
                + flash.argv_for(UNO, flash.INNER_PORT, '/w/firmware.hex')
        base.update(programmer=flash.PROGRAMMER, engine='avrdude',
                    will_stamp='BoardInstance %s: firmware_sha = %s…, last_flash_at = the run time; FirmwareBuild %s → flashed'
                               % (t['name'], base['artifact_sha256'][:16], b['name']))
        if where['how'] == 'refused':
            why.append(where['why'])
    base.update(argv_json=json.dumps(argv), argv_text=' '.join(argv), wrapper_text=' '.join(wrapper), engine_how=where['how'],
                engine_where=where.get('where') or where.get('why', ''), state='refused' if why else 'planned',
                notes='; '.join(why) if why else 'DRY-RUN: nothing was opened. Install needs this plan AND confirm.')
    row = upsert(manager, InstallPlan, base)
    return dict(base, refused=bool(why), why='; '.join(why), compat_detail=c, row=row)


def _variant(manager, name):
    try:
        return V.find(name, _rows(manager, 'FirmwareVariant')) if name else None
    except V.VariantRefused:
        return None


# ------------------------------------------------------------------ run
def run(manager, plan_name, confirm=False, work=None, scan=None, flash_run=None):
    """The confirmed install. Refuses (InstallRefused, exit 3) unless the plan exists, is planned, confirm is true, it
    is for THIS host, and the build is still compatible NOW."""
    from board.board_basis import InstallRecord, FirmwareBuild, BoardInstance
    p = _by_name(manager, 'InstallPlan', plan_name)
    if p is None:
        raise InstallRefused('no plan %r — make one first (POST /api/board/installer/plan); install always shows its DRY-RUN before it runs' % plan_name, '404 Not Found')
    if confirm is not True:
        raise InstallRefused('not confirmed — nothing was run. Read the plan\'s command, then confirm.', '400 Bad Request')
    if p.state != 'planned':
        raise InstallRefused('plan %s is %r: %s' % (p.name, p.state, p.notes))
    if p.host != this_host():
        raise InstallRefused('plan %s is for host %s; this server runs on %s — the install must run on the machine holding the port (open the installer there)'
                             % (p.name, p.host, this_host()), '403 Forbidden')
    b = find_build(manager, p.build, work)
    c = compat.check(b, manager)
    if c['verdict'] != 'compatible':
        p.state, p.notes = 'refused', 'at run time: %s' % c['plain']
        _save(manager, p)
        raise InstallRefused('REFUSED (%s): %s' % (c['verdict'], c['plain']), verdict=c['verdict'])
    t0, started = time.time(), _now()
    n = len([r for r in _rows(manager, 'InstallRecord') if getattr(r, 'build', '') == b['name']]) + 1
    rec = {'name': 'install-%s-%d' % (b['name'], n), 'plan': p.name, 'build': b['name'], 'variant': b.get('variant', ''), 'instance': p.instance,
           'target_kind': p.target_kind, 'started_at': started, 'row_class': (json.loads(b.get('classes_json') or '[]') or [{}])[0].get('class', ''),
           'row_name': (json.loads(b.get('repro_json') or '{}').get('knobs') or {}).get('rig_name', '')}
    try:
        if p.target_kind == 'twin':
            rec.update(_run_twin(manager, b, work))
        else:
            rec.update(_run_board(manager, p, b, work, scan, flash_run))
    except InstallRefused:
        raise
    except Exception as e:  # noqa: BLE001 — the record says what happened, in plain words
        rec.update(verdict='failed', verify='nothing verified', log_tail=str(e)[-1500:], notes='the install failed: %s' % str(e)[:300])
    rec.update(elapsed_s=round(time.time() - t0, 2), finished_at=_now())
    row = upsert(manager, InstallRecord, rec)
    p.state = 'ran'
    _save(manager, p)
    if rec.get('verdict') == 'installed':
        fb = dict(gen.row_fields(b), state='flashed', flashed_to=p.instance)
        upsert(manager, FirmwareBuild, fb)
        if p.target_kind == 'board':
            inst = _by_name(manager, 'BoardInstance', p.instance)
            if inst is not None:
                inst.firmware_sha, inst.last_flash_at = rec['firmware_sha'], rec['finished_at']
                _save(manager, inst)
            else:
                upsert(manager, BoardInstance, dict(rec.get('_instance') or {}, firmware_sha=rec['firmware_sha'], last_flash_at=rec['finished_at']))
    return dict(rec, row=row)


def _run_twin(manager, b, work):
    from board.custom import twin
    work = work or work_dir()
    stim = V.stimulus(_variant(manager, b.get('variant', '')))
    if twin.read_state(work):
        twin.down(UNO, work)   # the twin holds one firmware at a time, like the board
    s = twin.up(UNO, work, tcp=TWIN_TCP, link=TWIN_LINK, adc0_mv=stim[0], build_dir=os.path.dirname(b['hex_path']), adc_mv=stim[1])
    ready = twin.ready_line(s['log']) or {}
    want = twin.hex_data_bytes(b['hex_path'])
    got = int(ready.get('flash_bytes_loaded') or 0)
    ok = s['alive'] and got == want and s['hex_sha256'] == b['artifact_sha256']
    log = open(s['log']).read()
    return {'verdict': 'installed' if ok else 'failed', 'verified_bytes': got, 'firmware_sha': b['artifact_sha256'] if ok else '',
            'verify': ('simavr loaded %d flash bytes from the .hex; the .hex carries %d — they match; the twin runs sha256 %s…'
                       % (got, want, b['artifact_sha256'][:16])) if ok else
                      ('simavr reported %d flash bytes loaded, the .hex carries %d (alive=%s) — not verified' % (got, want, s['alive'])),
            'log_tail': log[-1500:], 'notes': 'installed into THE TWIN (simavr) — it counts as the device for this proof; a real UNO is the same plan with its port'}


def _run_board(manager, p, b, work, scan, flash_run):
    from board.custom import flash, engine_run
    t = target(p.instance, scan, manager)
    if t['port'] != p.port:
        raise InstallRefused('the board moved: the plan says %s, it is now at %s — plan again' % (p.port, t['port']))
    kw = {'run': flash_run} if flash_run else {}
    try:
        res = flash.flash(UNO, os.path.dirname(b['hex_path']), port=p.port, yes=True, instance=t['instance'], **kw)
    except (flash.FlashRefused, engine_run.EngineRefused, gen.GenRefused) as e:
        return {'verdict': 'failed', 'verify': 'avrdude did not verify the write', 'log_tail': str(e)[-1500:], 'notes': 'flash refused: %s' % str(e)[:300]}
    return {'verdict': 'installed', 'verified_bytes': res['verified_bytes'], 'firmware_sha': b['artifact_sha256'],
            'verify': 'avrdude wrote the flash, read it back and compared: %d bytes verified' % res['verified_bytes'],
            'log_tail': (res.get('log') or '')[-1500:], 'notes': 'installed on %s at %s' % (p.instance, p.port), '_instance': t['instance']}


# ------------------------------------------------------------------ the page's document
_BUILD_KEYS = ('name', 'variant', 'state', 'size_text', 'size_data', 'size_bss', 'artifact_sha256', 'header_sha256', 'built_at', 'flashed_to')


def document(manager, work=None, scan=None):
    from board.custom import build as B, twin
    flash_max, ram_max, cite = B.limits(UNO)
    det = detected(scan, manager)
    boards = [i for i in det['instances'] if i.get('definition') == UNO and i.get('state') == 'board present']
    adapters = [i for i in det['instances'] if i.get('definition_kind') == 'adapter']
    builds = []
    for b in sorted(all_builds(manager, work).values(), key=lambda r: r.get('built_at', ''), reverse=True):
        if b.get('board_definition') != UNO:
            continue
        c = compat.check(b, manager)
        engines = json.loads(b.get('engines_json') or '{}') if isinstance(b.get('engines_json'), str) else (b.get('engines_json') or {})
        flash_b = int(b.get('size_text') or 0) + int(b.get('size_data') or 0)
        ram_b = int(b.get('size_data') or 0) + int(b.get('size_bss') or 0)
        builds.append(dict(_fields(b, _BUILD_KEYS), flash_bytes=flash_b, flash_max=flash_max, ram_bytes=ram_b, ram_max=ram_max,
                           flash_pct=round(100.0 * flash_b / flash_max, 1), ram_pct=round(100.0 * ram_b / ram_max, 1),
                           compat=c['verdict'], compat_why=c['plain'], installable=c['verdict'] == 'compatible' and b.get('state') in ('built', 'flashed')
                           and bool(b.get('hex_path')) and os.path.isfile(b.get('hex_path') or ''),
                           engines=', '.join('%s %s' % (k, (v.get('version') or v.get('id') or '')[:40]) for k, v in engines.items())))
    vrows = _rows(manager, 'FirmwareVariant') or [dict(v) for v in V.SEED_FIRMWARE_VARIANTS]
    vlist = [_fields(v, ('name', 'title', 'purpose', 'app', 'classes_json', 'what_to_watch')) for v in vrows]
    ts = twin.status(UNO, work or work_dir())
    recs = sorted(_rows(manager, 'InstallRecord'), key=lambda r: getattr(r, 'started_at', ''), reverse=True)
    plans = sorted(_rows(manager, 'InstallPlan'), key=lambda r: getattr(r, 'planned_at', ''), reverse=True)
    targets = [{'name': TWIN, 'kind': 'twin', 'label': 'the simavr twin of the UNO (this host)', 'port': TWIN_LINK}] + \
        [{'name': i['name'], 'kind': 'board', 'label': 'UNO at %s' % (i.get('by_id_path') or i.get('port')), 'port': i.get('by_id_path') or i.get('port')} for i in boards]
    return {'ok': True, 'host': this_host(), 'board': UNO, 'limits': {'flash_b': flash_max, 'ram_b': ram_max, 'cited': cite},
            'targets': targets, 'boards': boards, 'adapters': adapters, 'unadmitted': det.get('unadmitted', []),
            'scan_note': det.get('error') or ('%d board(s), %d adapter(s), %d unadmitted on %s' % (len(boards), len(adapters), len(det.get('unadmitted', [])), this_host())),
            'variants': vlist, 'builds': builds,
            'twin': {k: ts.get(k) for k in ('state', 'build', 'variant', 'hex_sha256', 'link', 'adc0', 'adc_mv', 'started_at')},
            'plans': [_fields(p, ('name', 'build', 'variant', 'instance', 'target_kind', 'argv_text', 'wrapper_text', 'engine', 'engine_how',
                                  'compat', 'compat_why', 'will_stamp', 'state', 'planned_at', 'notes')) for p in plans[:10]],
            'records': [_fields(r, ('name', 'plan', 'build', 'variant', 'instance', 'target_kind', 'verdict', 'verify', 'verified_bytes', 'firmware_sha',
                                    'elapsed_s', 'bridge_name', 'bridge_state', 'row_class', 'row_name', 'frames_per_s', 'started_at')) for r in recs[:10]],
            'last': _fields(recs[0], ('name', 'verdict', 'verify', 'variant', 'bridge_state', 'row_class', 'row_name')) if recs else None}
