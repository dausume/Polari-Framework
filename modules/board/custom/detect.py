"""
@module board.custom.detect

`pol board detect` (plan §2): hwmap's scanner (`usb_devices()`, `usb_tree()`, `serial_ports()`) runs ON the host;
each USB device is matched by VID:PID — or, failing that, by its /dev/serial/by-id name — against
BoardDefinition.usb_ids and AdapterDefinition.usb_ids. Nothing is guessed:
  * a board match      → a BoardInstance 'board present'
  * an adapter match   → a BoardInstance 'adapter present, target unknown' (+ the boards whose chain names it)
  * no match           → listed 'unadmitted', never stored
Hubs and root hubs are slots, not devices (hwmap's rule) and are skipped. Stdlib only besides the scanner.

    python3 -m board.custom.detect [--json]        # on the host, from polari-framework/ (pol board detect)
"""
import json
import os
import sys
import time


def _sys_usb_of_tty(dev):
    """/dev/ttyUSB0 → {'vendor_id','product_id','serial','bus','dev'} by walking sysfs up to the USB device."""
    name = os.path.basename(dev or '')
    node = '/sys/class/tty/%s/device' % name
    if not name or not os.path.exists(node):
        return {}
    cur = os.path.realpath(node)
    for _ in range(8):
        if os.path.isfile(os.path.join(cur, 'idVendor')):
            def rd(f):
                try:
                    return open(os.path.join(cur, f)).read().strip()
                except OSError:
                    return ''
            return {'vendor_id': rd('idVendor'), 'product_id': rd('idProduct'), 'serial': rd('serial'),
                    'bus': rd('busnum').zfill(3), 'dev': rd('devnum').zfill(3)}
        cur = os.path.dirname(cur)
    return {}


def scan_host():
    """The raw facts, from hwmap's scanner (reused, not copied) + a sysfs tty → usb link per serial port."""
    from hwmap.custom import scanner
    _slots, paths = scanner.usb_tree()
    usb = []
    for d in scanner.usb_devices():
        t = paths.get((d['bus'], d['dev']), {})
        usb.append(dict(d, path=t.get('path', ''), usb_class=t.get('class', '')))
    serial = [dict(s, **_sys_usb_of_tty(s.get('device'))) for s in scanner.serial_ports()]
    return {'host': os.uname().nodename, 'observed_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'usb': usb, 'serial': serial}


def _ids(row):
    v = row.get('usb_ids_json', '[]') if isinstance(row, dict) else getattr(row, 'usb_ids_json', '[]')
    try:
        return [x.lower() for x in json.loads(v or '[]')]
    except ValueError:
        return []


def _field(row, key, default=''):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def _hints(row):
    try:
        return json.loads(_field(row, 'by_id_hints_json', '[]') or '[]')
    except ValueError:
        return []


def _is_hub(d):
    return d.get('vendor_id') == '1d6b' or d.get('usb_class', '').lower() in ('hub', 'root_hub')


def match(snapshot, boards, adapters):
    """snapshot = scan_host()'s shape; boards/adapters = rows or dicts. Returns {'instances', 'unadmitted', 'summary'}."""
    host = snapshot.get('host', '')
    by_usb = {}
    for s in snapshot.get('serial', []):
        if s.get('vendor_id'):
            by_usb.setdefault((s.get('bus', ''), s.get('dev', '')), []).append(s)
    adapter_targets = {}
    for b in boards:
        try:
            for a in json.loads(_field(b, 'adapter_ids_json', '[]') or '[]'):
                adapter_targets.setdefault(a, []).append(_field(b, 'name'))
        except ValueError:
            pass
    instances, unadmitted, used_serial = [], [], set()
    for d in snapshot.get('usb', []):
        if _is_hub(d):
            continue
        vp = '%s:%s' % (d.get('vendor_id', '').lower(), d.get('product_id', '').lower())
        ports = by_usb.get((d.get('bus', ''), d.get('dev', '')), [])
        hit, kind, how = None, '', ''
        for kind_, rows in (('board', boards), ('adapter', adapters)):
            hit = next((r for r in rows if vp in _ids(r)), None)
            if hit is not None:
                kind, how = kind_, 'usb-id'
                break
        if hit is None:
            unadmitted.append({'usb_id': vp, 'description': d.get('description', ''), 'usb_path': d.get('path', '') or 'bus %s dev %s' % (d.get('bus'), d.get('dev')),
                               'why': 'no BoardDefinition or AdapterDefinition lists %s' % vp})
            continue
        port = ports[0] if ports else {}
        if port:
            used_serial.add(port.get('by_id_path'))
        instances.append(_instance(host, hit, kind, how, vp, d.get('path', '') or 'bus%s-dev%s' % (d.get('bus'), d.get('dev')), port,
                                   adapter_targets, d.get('description', ''), snapshot.get('observed_at', '')))
    # by-id fallback: a serial port with no sysfs link (or a fake) is matched by its by-id name, never by guess
    for s in snapshot.get('serial', []):
        if s.get('by_id_path') in used_serial or s.get('vendor_id'):
            continue
        base = os.path.basename(s.get('by_id_path', ''))
        for kind, rows in (('board', boards), ('adapter', adapters)):
            hit = next((r for r in rows if any(h and h in base for h in _hints(r))), None)
            if hit is not None:
                instances.append(_instance(host, hit, kind, 'by-id-hint', '', base, s, adapter_targets, base, snapshot.get('observed_at', '')))
                break
    # identical adapters sharing one by-id name (same USB serial string) — say so instead of pretending a port
    for inst in instances:
        if not inst['by_id_path']:
            twins = [i for i in instances if i is not inst and i['definition'] == inst['definition'] and i['by_id_path']]
            if twins:
                inst['notes'] = (inst['notes'] + ' no /dev/serial/by-id link of its own — identical adapters share one by-id name '
                                 '(same USB serial string); identify it by usb path %s' % inst['usb_path']).strip()
    summary = {'host': host, 'boards': sum(1 for i in instances if i['definition_kind'] == 'board'),
               'adapters': sum(1 for i in instances if i['definition_kind'] == 'adapter'), 'unadmitted': len(unadmitted)}
    return {'instances': instances, 'unadmitted': unadmitted, 'summary': summary}


def _instance(host, row, kind, how, vp, path, port, adapter_targets, description, seen):
    name = _field(row, 'name')
    targets = adapter_targets.get(name, []) if kind == 'adapter' else []
    state = 'board present' if kind == 'board' else 'adapter present, target unknown'
    notes = ''
    if kind == 'adapter':
        notes = 'which target is wired to it is a person\'s answer (target_board); boards whose chain names this adapter: %s' % (', '.join(targets) or 'none yet')
    return {'name': '%s:%s@%s' % (host, name, path), 'definition': name, 'definition_kind': kind, 'state': state, 'host': host,
            'usb_id': vp, 'usb_path': path, 'by_id_path': port.get('by_id_path', ''), 'port': port.get('device', ''),
            'serial_number': port.get('serial', ''), 'matched_by': how, 'target_board': '',
            'possible_targets_json': json.dumps(targets), 'last_seen_at': seen, 'notes': notes, 'description': description}


def seed_definitions():
    """The definitions as the seed builds them (for a host with no server: the CLI)."""
    from board.custom.register_map import board_rows, adapter_rows
    return board_rows(), adapter_rows()


def render(result):
    lines = []
    for i in result['instances']:
        lines.append('%-8s %-28s %-34s %-10s %s%s' % (i['definition_kind'].upper(), i['definition'], i['state'], i['usb_id'] or i['matched_by'],
                                                    i['by_id_path'] or ('usb path ' + i['usb_path']), ('\n         ' + i['notes']) if i['notes'] else ''))
    for u in result['unadmitted']:
        lines.append('%-8s %-28s %-34s %-10s usb path %s' % ('UNADMIT', u['description'][:28], 'no definition (never guessed)', u['usb_id'], u['usb_path']))
    s = result['summary']
    lines.append('host %s: %d board(s), %d adapter(s), %d unadmitted' % (s['host'], s['boards'], s['adapters'], s['unadmitted']))
    return '\n'.join(lines)


def main(argv):
    boards, adapters = seed_definitions()
    snap = scan_host()
    result = match(snap, boards, adapters)
    if '--snapshot' in argv:
        print(json.dumps(snap))
    elif '--json' in argv:
        print(json.dumps(result, indent=1))
    else:
        print(render(result))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
