"""
@module board.custom.ingest

INGEST IN (brd-bo, PCB_FROM_SCRATCH_PLAN §2b): read a view back — a KiCad netlist, a Zephyr overlay / board dts, an ESP-IDF
board_pins.h + sdkconfig fragment, a bare-C board_config.h — and COMPARE it with the rows. A disagreement becomes one
`BoardConflict` per (pin, field); the rows are NEVER changed by an ingest (shown, never auto-resolved — his rule). Each ingest is a
`BoardView` row (direction in) carrying the view's sha256 and the board sha it was compared against.

Where rows are written: a server's tables (`manager`, the API door POST /api/board/<board>/ingest), else a local LEDGER
(~/.cache/polari-board/board-object/ledger.json — `pol board ingest|render|conflicts` with no server).

    python3 -m board.custom.board_object_cli ingest <path> --as kicad|zephyr|esp-idf|bare-c [--board B]
"""
import datetime
import hashlib
import json
import os

from board.custom import board_object as bo
from board.custom import views as V


def read_path(path):
    """{name: text} — one file, or every regular file of a directory (a Zephyr board dir, an ESP-IDF pair)."""
    if os.path.isdir(path):
        return {fn: open(os.path.join(path, fn)).read() for fn in sorted(os.listdir(path)) if os.path.isfile(os.path.join(path, fn))}
    return {os.path.basename(path): open(path).read()}


def detect_kind(files):
    names = list(files)
    if any(n.endswith('.net') for n in names):
        return 'kicad'
    if any(n.endswith(('.overlay', '.dts')) for n in names):
        return 'zephyr'
    if any(n == 'board_pins.h' or 'sdkconfig' in n for n in names):
        return 'esp-idf'
    if any(n.endswith('.h') for n in names):
        return 'bare-c'
    raise V.ViewRefused('cannot tell the view kind of %s — pass --as kicad|zephyr|esp-idf|bare-c' % names)


def _norm(field, v):
    if field == 'electrical_json':
        try:
            return json.dumps(json.loads(v or '{}'), sort_keys=True)
        except ValueError:
            return str(v)
    return '' if v is None else str(v)


def compare(r, kind, view):
    """[(pin, field, rows_value, view_value)] — every disagreement between the rows and an ingested view."""
    out = []
    if kind in ('bare-c', 'esp-idf'):
        for vp in view['pins']:
            cur = bo.pin_of_symbol(r, vp['firmware_symbol'])
            if cur is None or cur['canonical'] != vp['canonical']:
                out.append((vp['canonical'], 'firmware_symbol', '%s on %s' % (vp['firmware_symbol'], cur['canonical'] if cur else '(no pin)'),
                            '%s on %s' % (vp['firmware_symbol'], vp['canonical'])))
        if kind == 'esp-idf':
            from board.custom.views.esp_idf import profile_now
            now = profile_now(r)
            for k, v in sorted(view.get('profile', {}).items()):
                if str(now.get(k, '')) != str(v):
                    out.append(('(runtime esp-idf)', 'profile.%s' % k, str(now.get(k, '')), str(v)))
        return out
    if kind == 'zephyr':
        from board.custom.views.zephyr import carried
        rows = {p['canonical']: p for p in r['pins'] if carried(p)}
    else:
        rows = {p['canonical']: p for p in r['pins'] if p.get('soc_pin') and p.get('net')}
    seen = {vp['canonical']: vp for vp in view['pins']}
    for c in sorted(set(rows) | set(seen)):
        if c not in seen:
            out.append((c, 'presence', 'in the rows', 'absent from the view'))
        elif c not in rows:
            out.append((c, 'presence', 'absent from the rows', 'in the view (%s)' % seen[c].get('net', '')))
        else:
            for f in V.CARRIES[kind]:
                a, b = _norm(f, rows[c].get(f)), _norm(f, seen[c].get(f))
                if a != b:
                    out.append((c, f, a, b))
    if kind == 'zephyr' and 'console_uart' in view.get('profile', {}):
        now = (r['profiles'].get('zephyr') or {}).get('console_uart', '')
        if now != view['profile']['console_uart']:
            out.append(('(runtime zephyr)', 'profile.console_uart', now, view['profile']['console_uart']))
    return out


def ingest(board, files, kind=None, tables=None, r=None, path=''):
    """→ {'view': BoardView dict, 'conflicts': [BoardConflict dict], 'pins': [...], 'profile': {...}} — nothing written here."""
    r = r or bo.rows_for(board, tables)
    kind = kind or detect_kind(files)
    view = V.module(kind).ingest(files, r)
    sha, bsha = V.view_sha(files), bo.board_sha(r)
    now = datetime.datetime.now().isoformat(timespec='seconds')
    vname = '%s:%s:in:%s' % (r['board'], kind, sha[:12])
    diffs = compare(r, kind, view)
    conflicts = [{'name': '%s:%s:%s' % (vname, pin, field), 'board': r['board'], 'view': vname, 'view_kind': kind, 'pin': pin, 'field': field,
                  'rows_value': a, 'view_value': b, 'state': 'open', 'detected_at': now,
                  'notes': 'the rows are unchanged — edit the rows or the view\'s source; never auto-resolved'} for pin, field, a, b in diffs]
    vrow = {'name': vname, 'board': r['board'], 'kind': kind, 'direction': 'in', 'path': path, 'sha256': sha, 'board_sha': bsha, 'refused': False,
            'refusal': '', 'conflicts': len(conflicts), 'fields_carried': ', '.join(V.CARRIES[kind]), 'at': now,
            'notes': view.get('notes', '')[:2000]}
    return {'view': vrow, 'conflicts': conflicts, 'pins': view['pins'], 'profile': view.get('profile', {}), 'board_sha': bsha}


def render_row(board, kind, tables=None, r=None, path=''):
    """Render + its BoardView (direction out) — a refusal is a row too. → (result or None, view row)."""
    r = r or bo.rows_for(board, tables)
    now = datetime.datetime.now().isoformat(timespec='seconds')
    try:
        res = V.render(r, kind)
    except V.ViewRefused as e:
        bsha = bo.board_sha(r)
        return None, {'name': '%s:%s:out:refused' % (r['board'], kind), 'board': r['board'], 'kind': kind, 'direction': 'out', 'path': '',
                      'sha256': '', 'board_sha': bsha, 'refused': True, 'refusal': str(e), 'conflicts': 0,
                      'fields_carried': ', '.join(V.CARRIES.get(kind, ())), 'at': now, 'notes': ''}
    return res, {'name': '%s:%s:out:%s' % (r['board'], kind, res['sha256'][:12]), 'board': r['board'], 'kind': kind, 'direction': 'out',
                 'path': path, 'sha256': res['sha256'], 'board_sha': res['board_sha'], 'refused': False, 'refusal': '', 'conflicts': 0,
                 'fields_carried': ', '.join(V.CARRIES[kind]), 'at': now, 'notes': ', '.join(sorted(res['files']))}


# ------------------------------------------------------------------ where the rows go
def ledger_path():
    return os.path.expanduser(os.path.join(os.environ.get('POLARI_BOARD_HOME', '~/.cache/polari-board'), 'board-object', 'ledger.json'))


def ledger_read():
    try:
        return json.load(open(ledger_path()))
    except (OSError, ValueError):
        return {'views': [], 'conflicts': []}


def ledger_write(views=(), conflicts=()):
    led = ledger_read()
    names = {v['name'] for v in views}
    led['views'] = [v for v in led['views'] if v['name'] not in names] + list(views)
    cnames = {c['name'] for c in conflicts}
    led['conflicts'] = [c for c in led['conflicts'] if c['name'] not in cnames] + list(conflicts)
    os.makedirs(os.path.dirname(ledger_path()), exist_ok=True)
    json.dump(led, open(ledger_path(), 'w'), indent=1)
    return led


def save_rows(manager, views=(), conflicts=()):
    """Upsert BoardView / BoardConflict rows on a server (by name)."""
    from board.board_basis import BoardConflict, BoardView
    saved = 0
    for cls, rows in ((BoardView, views), (BoardConflict, conflicts)):
        table = (manager.objectTables or {}).get(cls.__name__, {}) or {}
        by_name = {getattr(x, 'name', ''): x for x in table.values()}
        for row in rows:
            obj = by_name.get(row['name'])
            if obj is None:
                obj = cls(manager=manager, **row)
            else:
                for k, v in row.items():
                    setattr(obj, k, v)
            try:
                manager.db.saveInstanceInDB(obj)
                saved += 1
            except Exception:  # noqa: BLE001 — a server without a DB keeps the in-memory row
                pass
    return saved


def file_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()
