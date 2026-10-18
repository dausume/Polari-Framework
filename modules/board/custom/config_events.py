"""
@module board.custom.config_events

pv-4 (PIN_VIEW_PLAN.md 2.4 / 2.9): CONFIGURATION EVENTS — the real-world changes that alter a board's pin states, as ONE timeline.

    GET  /api/board/{board}/config-events[?instance=&system=&binding=&pins=0]     the timeline: derived + recorded events, oldest first
    POST /api/board/{board}/config-events      {kind, cause, who, when?, board_instance?, refs?, pins?, binding?}   record a real event (a person or a bridge)

THREE SOURCES, one truth each:
  derived   an `InstallRecord` (verdict installed) is read as a `flash`; a `BoardPinNet` row with provenance canvas is read as `wiring-added`. They are READ on every request - never copied into
            ConfigurationEvent rows, so the record stays the only truth. A seed BoardPinNet (the demo bench the module ships) is the DESIGN, not an event.
  recorded  `ConfigurationEvent` rows: what no other row records (a wire removed, a shield attached or detached, another binding chosen, a reset). A recorded event that cites an InstallRecord /
            BoardPinNet ref supersedes the derived event of that row (listed under `covered`, not twice).
Kinds: flash | wiring-added | wiring-removed | shield-attached | shield-detached | binding-chosen | reset. The door refuses any other kind by name.

`pins_changed` is DERIVED from the pin view's own payload difference (pin_view.build twice, never typed): per pin the before / after in plain words (drive and signal kept apart), plus the pins at the ends of
a connection that appeared or vanished. A flash and a binding choice compare stage base with stage firmware-committed of the binding; a reset compares the chosen stage's runtime with the reset phase; a wiring
event compares the payload without and with the BoardPinNet row. The `pins_basis` text says what was compared, or why nothing could be (no binding names the firmware's pin assignments; a shield has no model yet).
Cost: one pin_view build (about 2-5 s) per distinct comparison; `pins=0` skips the difference.
"""
import datetime
import json

from board.custom import board_object as BO
from board.custom import hardware_system as HS

KINDS = ('flash', 'wiring-added', 'wiring-removed', 'shield-attached', 'shield-detached', 'binding-chosen', 'reset')
LABEL = {'flash': 'Firmware flashed', 'wiring-added': 'Wire added', 'wiring-removed': 'Wire removed', 'shield-attached': 'Shield attached', 'shield-detached': 'Shield detached',
         'binding-chosen': 'Binding chosen', 'reset': 'Board reset'}
REF_CLASSES = ('InstallRecord', 'BoardPinNet', 'FirmwareBuild', 'Binding', 'BoardInstance')
NEEDS_REF = {'wiring-added': 'BoardPinNet', 'wiring-removed': 'BoardPinNet', 'binding-chosen': 'Binding'}
PROVENANCE = ('recorded', 'bridge')
LEVELS = ('die', 'package', 'board', 'part', 'bench')
NOT_RECORDED = 'not recorded'


class EventRefused(ValueError):
    def __init__(self, msg, status=400):
        super().__init__(msg)
        self.status = status


# ---------------------------------------------------------------- rows
def _dict(row):
    if isinstance(row, dict):
        return dict(row)
    return {k: v for k, v in vars(row).items() if not k.startswith('_') and k != 'manager'}


def rows(tables, manager, cls):
    """The rows of one class as dicts: the `tables` in hand when they carry the class, else the live manager's."""
    if tables is not None and cls in tables:
        return [_dict(r) for r in tables[cls]]
    if manager is not None:
        return [_dict(r) for r in ((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values()]
    return []


def _when_key(w):
    try:
        return datetime.datetime.fromisoformat(w).replace(tzinfo=None).isoformat()
    except (TypeError, ValueError):
        return ''


def _board_of_install(ir, builds, variants, instances):
    """The board design an InstallRecord belongs to: its build's, else its variant's, else its instance's. '' when none of them says."""
    b = builds.get(ir.get('build') or '')
    if b and b.get('board_definition'):
        return b['board_definition']
    v = variants.get(ir.get('variant') or '')
    if v and v.get('board_definition'):
        return v['board_definition']
    i = instances.get(ir.get('instance') or '')
    if i:
        return i.get('target_board') or i.get('definition') or ''
    return ''


# ---------------------------------------------------------------- the payload difference
def _drive_text(p):
    return p['drive_status'] + (' (%s)' % p['pull'] if p.get('pull') not in (None, '', 'none') else '')


def _signal_text(p):
    a = p.get('activated')
    return a['function'] if a else 'none activated'


def _state(p):
    return {'drive': _drive_text(p), 'signal': _signal_text(p), 'stage': p['stage']}


def _words(s):
    return 'drive %s; signal %s; %s' % (s['drive'], s['signal'], s['stage'])


def payload_diff(before, after):
    """[{pin, label, level, surface, before, after, what}] — the pins whose state differs between two pin-view payloads, and the pins at the ends of a connection that appeared or vanished."""
    bp, ap = {p['id']: p for p in before['pins']}, {p['id']: p for p in after['pins']}
    out = {}

    def add(pid, p, b, a, what):
        e = out.setdefault(pid, {'pin': pid, 'label': p['label'], 'level': p['level'], 'surface': p.get('surface_title') or p['surface'], 'before': b, 'after': a, 'what': []})
        for w in what:
            if w not in e['what']:
                e['what'].append(w)

    for pid, p in ap.items():
        q = bp.get(pid)
        if q is None:
            add(pid, p, 'not on the board', _words(_state(p)), ['added'])
            continue
        s0, s1 = _state(q), _state(p)
        what = [k for k in ('drive', 'signal', 'stage') if s0[k] != s1[k]]
        if what:
            add(pid, p, _words(s0), _words(s1), what)
    for pid, q in bp.items():
        if pid not in ap:
            add(pid, q, _words(_state(q)), 'not on the board', ['removed'])
    bc, ac = {c['id']: c for c in before['connections']}, {c['id']: c for c in after['connections']}
    for cid in sorted(set(bc) ^ set(ac)):
        gained = cid in ac
        c = ac[cid] if gained else bc[cid]
        pins = ap if gained else bp
        for end, other in ((c['a'], c['b']), (c['b'], c['a'])):
            p = pins.get(end)
            if p is None:
                continue
            o = pins.get(other)
            via = (' via ' + c['via']) if c.get('via') else ''
            note = 'connected to %s%s' % (o['label'] if o else other, via)
            add(end, p, 'no such connection' if gained else note, note if gained else 'no such connection', ['connection'])
    return sorted(out.values(), key=lambda e: (LEVELS.index(e['level']) if e['level'] in LEVELS else 9, e['label'], e['pin']))


class _Builder:
    """pin_view.build with a cache, so one request pays for each distinct comparison once."""

    def __init__(self, board, tables, manager, system):
        self.board, self.tables, self.manager, self.system, self.cache = board, tables, manager, system, {}

    def build(self, key, tables=None, **params):
        from board.custom import pin_view as PV
        k = (key, tuple(sorted(params.items())))
        if k not in self.cache:
            self.cache[k] = PV.build(self.board, dict({'system': self.system}, **params), self.manager, tables=tables if tables is not None else self.tables)
        return self.cache[k]

    def without_net(self, net_name):
        t = dict(self.tables)
        t['BoardPinNet'] = [r for r in self.tables.get('BoardPinNet', []) if r['name'] != net_name]
        return t


def diff_for(kind, b, binding='', refs=(), params=None):
    """-> (pins_changed list, pins_basis words). Never raises on a missing binding: it says so."""
    params = params or {}
    refs = list(refs)
    if kind in ('flash', 'binding-chosen', 'reset'):
        base = b.build('base', stage='base')
        binding = binding or base.get('binding') or ''
        if not binding:
            return [], 'undetermined: no binding names the firmware\'s pin assignments for this board, so nothing can say which pins it changed'
        if kind == 'reset':
            run = b.build('run', binding=binding, stage='firmware-committed')
            rst = b.build('reset', binding=binding, stage='firmware-committed', phase='reset')
            return payload_diff(run, rst), 'compared the runtime state of binding %s (firmware committed) with the reset phase: after a reset every I/O pin is blank until init runs' % binding
        after = b.build('fw', binding=binding, stage='firmware-committed')
        why = 'compared the board as built (stage base: nothing claimed) with binding %s firmware committed' % binding
        if not any(r.startswith('Binding:') for r in refs) and not params.get('binding'):
            why += ' - the record names no binding, so the system\'s binding was used'
        return payload_diff(base, after), why
    if kind in ('wiring-added', 'wiring-removed'):
        net = next((r.partition(':')[2] for r in refs if r.startswith('BoardPinNet:')), '')
        present = any(r['name'] == net for r in b.tables.get('BoardPinNet', []))
        if present:
            with_row = b.build('all', stage='base')
            without = b.build('no-net', tables=b.without_net(net), stage='base')
            d = payload_diff(without, with_row) if kind == 'wiring-added' else payload_diff(with_row, without)
            return d, 'compared the pin view without and with the wire %s (stage base)' % net
        canon = net.partition(':')[2].partition('@')[0]
        base = b.build('all', stage='base')
        p = next((x for x in base['pins'] if x['level'] == 'board' and x['canonical'] == canon), None)
        if p is None:
            return [], 'undetermined: the wire %s is not in the model any more and names no pin of this board' % net
        circuit = net.partition('@')[2]
        before, after = ('on bench net %s' % circuit, 'not on a bench net') if kind == 'wiring-removed' else ('not on a bench net', 'on bench net %s' % circuit)
        return [{'pin': p['id'], 'label': p['label'], 'level': 'board', 'surface': p.get('surface_title') or p['surface'], 'before': before, 'after': after, 'what': ['connection']}], \
            'the wire row %s is gone, so its pin is read from its name (%s); the connections it made cannot be compared' % (net, canon)
    return [], 'undetermined: the model has no description of a shield yet (the pins are those the report names)'


# ---------------------------------------------------------------- the derived events
def _plain_install(ir, b):
    build = b.get('name') if b else ir.get('build')
    what = ('firmware %s' % (ir.get('variant') or build)) if (ir.get('variant') or build) else 'firmware'
    sha = (ir.get('firmware_sha') or '')[:12]
    return '%s was installed%s%s; %s' % (what.capitalize(), (' on %s' % ir['instance']) if ir.get('instance') else '', (' (sha %s)' % sha) if sha else '',
                                          ('verified: %s' % ir['verify']) if ir.get('verify') else 'no read-back is recorded')


def derive(board, tables, manager, builder=None, with_pins=True, binding=''):
    """-> (events, skipped): the InstallRecord flashes and the canvas wirings of `board`, as event dicts. Nothing is written."""
    builds = {r['name']: r for r in rows(tables, manager, 'FirmwareBuild')}
    variants = {r['name']: r for r in rows(tables, manager, 'FirmwareVariant')}
    instances = {r['name']: r for r in rows(tables, manager, 'BoardInstance')}
    events, skipped = [], []
    for ir in sorted(rows(tables, manager, 'InstallRecord'), key=lambda r: r.get('started_at') or ''):
        where = _board_of_install(ir, builds, variants, instances)
        if where != board:
            if not where:
                skipped.append({'source': 'InstallRecord:%s' % ir['name'], 'why': 'its build, variant and instance name no board: which board it flashed is undetermined'})
            continue
        if ir.get('verdict') != 'installed':
            skipped.append({'source': 'InstallRecord:%s' % ir['name'], 'why': 'verdict %s: nothing was installed, so no pin state changed' % (ir.get('verdict') or 'unknown')})
            continue
        refs = ['InstallRecord:%s' % ir['name']] + (['FirmwareBuild:%s' % ir['build']] if ir.get('build') else [])
        ev = {'name': 'derived:InstallRecord:%s' % ir['name'], 'board': board, 'board_instance': ir.get('instance') or '', 'kind': 'flash', 'cause': _plain_install(ir, builds.get(ir.get('build') or '')),
              'refs': refs, 'who': NOT_RECORDED, 'who_note': 'an InstallRecord stores no person', 'when': ir.get('finished_at') or ir.get('started_at') or '', 'provenance': 'derived',
              'source': 'InstallRecord:%s' % ir['name']}
        events.append(ev)
    for n in sorted(rows(tables, manager, 'BoardPinNet'), key=lambda r: r['name']):
        if n.get('board') != board or n.get('provenance') != 'canvas':
            continue
        canon = (n.get('board_pin') or '').rpartition(':')[2]
        role = {'output': 'as an output', 'driver': 'as an output', 'input': 'as an input'}.get(n.get('role'), '(role %s)' % (n.get('role') or 'undetermined'))
        events.append({'name': 'derived:BoardPinNet:%s' % n['name'], 'board': board, 'board_instance': '', 'kind': 'wiring-added',
                       'cause': 'Pin %s was wired to net %s of circuit %s %s (drawn on the canvas)' % (canon or '?', n.get('circuit_net') or '?', n.get('circuit') or '?', role),
                       'refs': ['BoardPinNet:%s' % n['name']], 'who': NOT_RECORDED, 'who_note': 'a BoardPinNet row stores no person', 'when': '', 'when_note': 'a BoardPinNet row stores no time',
                       'provenance': 'derived', 'source': 'BoardPinNet:%s' % n['name']})
    if with_pins and builder is not None:
        for ev in events:
            ev['pins_changed'], ev['pins_basis'] = diff_for(ev['kind'], builder, binding, ev['refs'], {'binding': binding})
    else:
        for ev in events:
            ev['pins_changed'], ev['pins_basis'] = [], 'not computed (pins=0)'
    return events, skipped


def _recorded(tables, manager, board):
    out = []
    for r in rows(tables, manager, 'ConfigurationEvent'):
        if r.get('board') != board:
            continue
        out.append({'name': r['name'], 'board': board, 'board_instance': r.get('board_instance') or '', 'kind': r.get('kind'), 'cause': r.get('cause') or '', 'refs': json.loads(r.get('refs_json') or '[]'),
                    'pins_changed': json.loads(r.get('pins_changed_json') or '[]'), 'pins_basis': r.get('pins_basis') or '', 'who': r.get('who') or NOT_RECORDED, 'when': r.get('when') or '',
                    'provenance': r.get('provenance') or 'recorded', 'source': 'ConfigurationEvent:%s' % r['name']})
    return out


def timeline(board, manager=None, tables=None, instance='', system='', binding='', with_pins=True):
    """-> the GET payload. Raises EventRefused (404) for an unknown board."""
    board = BO.board_name(board)
    tables = tables if tables is not None else HS.default_tables(manager)
    try:
        BO.rows_for(board, tables)
    except BO.BoardObjectRefused as e:
        raise EventRefused(str(e), 404)
    builder = _Builder(board, tables, manager, system)
    recorded = _recorded(tables, manager, board)
    cited = {r for e in recorded for r in e['refs']}
    derived, skipped = derive(board, tables, manager, builder, with_pins, binding)
    covered = [e for e in derived if e['source'] in cited]
    derived = [e for e in derived if e['source'] not in cited]
    events = derived + recorded
    if instance:
        events = [e for e in events if e['board_instance'] in (instance, '')]
    for e in events:
        e['label'] = LABEL.get(e['kind'], e['kind'])
        e['dated'] = bool(_when_key(e['when']))
    events.sort(key=lambda e: (e['dated'], _when_key(e['when']), e['name']))   # undated first (no time is recorded), then oldest to newest
    for i, e in enumerate(events):
        e['seq'] = i + 1
    return {'ok': True, 'board': board, 'instance': instance, 'instance_note': 'events of this instance plus the design-level events (no instance) that apply to every instance' if instance else '',
            'events': events, 'count': len(events), 'derived': sum(1 for e in events if e['provenance'] == 'derived'), 'recorded': sum(1 for e in events if e['provenance'] != 'derived'),
            'covered': [{'source': e['source'], 'by': [r['name'] for r in recorded if e['source'] in r['refs']]} for e in covered], 'skipped': skipped, 'kinds': list(KINDS),
            'note': 'derived events are read from InstallRecord rows and canvas BoardPinNet rows on every request; recorded events are ConfigurationEvent rows. The per-phase pin states are derived, never stored.'}


# ---------------------------------------------------------------- the POST door
def _check_refs(kind, refs, board, tables, manager):
    if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
        raise EventRefused('refs must be a list of "Class:name" strings (classes: %s)' % ', '.join(REF_CLASSES))
    builds = {r['name']: r for r in rows(tables, manager, 'FirmwareBuild')}
    variants = {r['name']: r for r in rows(tables, manager, 'FirmwareVariant')}
    instances = {r['name']: r for r in rows(tables, manager, 'BoardInstance')}
    for ref in refs:
        cls, _, name = ref.partition(':')
        if cls not in REF_CLASSES or not name:
            raise EventRefused('unknown ref %r (a ref is "Class:name", classes: %s)' % (ref, ', '.join(REF_CLASSES)))
        if cls == 'InstallRecord':
            ir = next((r for r in rows(tables, manager, 'InstallRecord') if r['name'] == name), None)
            if ir is None:
                raise EventRefused('no InstallRecord %r' % name, 404)
            if _board_of_install(ir, builds, variants, instances) not in (board, ''):
                raise EventRefused('InstallRecord %s belongs to another board' % name)
        elif cls == 'FirmwareBuild':
            b = builds.get(name)
            if b is None:
                raise EventRefused('no FirmwareBuild %r' % name, 404)
            if b.get('board_definition') not in (board, ''):
                raise EventRefused('FirmwareBuild %s is for another board' % name)
        elif cls == 'BoardInstance':
            if name not in instances:
                raise EventRefused('no BoardInstance %r' % name, 404)
        elif cls == 'BoardPinNet':
            present = any(r['name'] == name for r in rows(tables, manager, 'BoardPinNet'))
            if not present and not (kind == 'wiring-removed' and name.startswith(board + ':') and '@' in name):
                raise EventRefused('no BoardPinNet %r (only a wiring-removed event may cite a wire that is already gone, by its full name "<board>:<pin>@<circuit>:<net>")' % name, 404)
            if present and not name.startswith(board + ':'):
                raise EventRefused('BoardPinNet %s belongs to another board' % name)
        elif cls == 'Binding':
            try:
                from cmod.custom import binding as BND
                BND.resolve(name, manager=manager)
            except Exception as e:   # noqa: BLE001 - an unresolvable binding is a refused ref, with the owner's words
                raise EventRefused('no binding %r (%s)' % (name, str(e)[:160]), 404)


def validate(board, body, manager=None, tables=None, now=None):
    """-> the fields of the ConfigurationEvent to write, with `pins_changed` derived. Raises EventRefused (400 / 404) naming what is wrong."""
    board = BO.board_name(board)
    tables = tables if tables is not None else HS.default_tables(manager)
    try:
        BO.rows_for(board, tables)
    except BO.BoardObjectRefused as e:
        raise EventRefused(str(e), 404)
    if not isinstance(body, dict):
        raise EventRefused('the body must be a JSON object')
    kind = body.get('kind')
    if kind not in KINDS:
        raise EventRefused('unknown kind %r (kinds: %s)' % (kind, ', '.join(KINDS)))
    cause = (body.get('cause') or '').strip() if isinstance(body.get('cause'), str) else ''
    who = (body.get('who') or '').strip() if isinstance(body.get('who'), str) else ''
    if not cause:
        raise EventRefused('cause is required: say in plain words why it happened')
    if not who:
        raise EventRefused('who is required: the person or the bridge that reports it')
    prov = body.get('provenance') or 'recorded'
    if prov not in PROVENANCE:
        raise EventRefused('unknown provenance %r (%s)' % (prov, ', '.join(PROVENANCE)))
    when = body.get('when') or (now or datetime.datetime.now().isoformat(timespec='seconds'))
    try:
        datetime.datetime.fromisoformat(when)
    except (TypeError, ValueError):
        raise EventRefused('when must be an ISO time such as 2026-10-18T09:30:00 (got %r)' % (when,))
    inst = body.get('board_instance') or ''
    if inst:
        row = next((r for r in rows(tables, manager, 'BoardInstance') if r['name'] == inst), None)
        if row is None:
            raise EventRefused('no BoardInstance %r' % inst, 404)
        if (row.get('target_board') or row.get('definition')) != board:
            raise EventRefused('BoardInstance %s is not an instance of %s' % (inst, board))
    refs = body.get('refs') or []
    _check_refs(kind, refs, board, tables, manager)
    need = NEEDS_REF.get(kind)
    if need and not any(r.startswith(need + ':') for r in refs):
        raise EventRefused('a %s event must cite a %s in refs ("%s:<name>")' % (kind, need, need))
    binding = next((r.partition(':')[2] for r in refs if r.startswith('Binding:')), '') or (body.get('binding') or '')
    builder = _Builder(board, tables, manager, body.get('system') or '')
    pins, basis = diff_for(kind, builder, binding, refs, {'binding': binding})
    if kind in ('shield-attached', 'shield-detached'):   # the model has no shield: the report names the pins, validated against the payload
        named = body.get('pins') or []
        if not isinstance(named, list) or not all(isinstance(x, str) for x in named):
            raise EventRefused('pins must be a list of pin ids or labels')
        base = builder.build('all', stage='base')
        for x in named:
            p = next((q for q in base['pins'] if q['id'] == x or (q['level'] == 'board' and q['label'] == x)), None)
            if p is None:
                raise EventRefused('pin %r is not a pin of %s (GET /api/board/%s/pin-view/pins lists them)' % (x, board, board))
            pins.append({'pin': p['id'], 'label': p['label'], 'level': p['level'], 'surface': p.get('surface_title') or p['surface'],
                         'before': 'without the shield' if kind == 'shield-attached' else 'under the shield', 'after': 'under the shield' if kind == 'shield-attached' else 'without the shield',
                         'what': ['connection']})
    return {'board': board, 'board_instance': inst, 'kind': kind, 'cause': cause, 'refs': refs, 'pins_changed': pins, 'pins_basis': basis, 'who': who, 'when': when, 'provenance': prov}


def record(manager, board, body, tables=None, now=None):
    """Validate, derive the pins, write one ConfigurationEvent row. -> the event dict (with its row name). Raises EventRefused."""
    from board.board_basis import ConfigurationEvent
    f = validate(board, body, manager, tables, now)
    taken = {r['name'] for r in rows(None, manager, 'ConfigurationEvent')}
    n = 1
    while '%s:ev-%d' % (f['board'], n) in taken:
        n += 1
    name = '%s:ev-%d' % (f['board'], n)
    row = ConfigurationEvent(manager=manager, name=name, board=f['board'], board_instance=f['board_instance'], kind=f['kind'], cause=f['cause'], refs_json=json.dumps(f['refs']),
                             pins_changed_json=json.dumps(f['pins_changed']), pins_basis=f['pins_basis'], who=f['who'], when=f['when'], provenance=f['provenance'])
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 - an in-memory manager (selftest) has no db
        pass
    return dict(f, name=name, label=LABEL[f['kind']], source='ConfigurationEvent:%s' % name)


# ---------------------------------------------------------------- the door bodies (config_events_api calls these)
def get_door(manager, board, params):
    try:
        return 200, timeline(board, manager, instance=params.get('instance', ''), system=params.get('system', ''), binding=params.get('binding', ''),
                             with_pins=params.get('pins', '1') not in ('0', 'false', 'no'))
    except EventRefused as e:
        return e.status, {'ok': False, 'error': str(e)}


def post_door(manager, board, body):
    try:
        return 201, {'ok': True, 'event': record(manager, board, body)}
    except EventRefused as e:
        return e.status, {'ok': False, 'error': str(e), 'kinds': list(KINDS)}
