"""
@module electrodevice.custom.layout_cli

lay-1: `pol board layout ...` and `pol board wire-colors ...`. With --api URL it is a thin client of the layout doors (/api/layout/...), so it works from any machine that reaches the backend; with
no --api it computes from the SEEDS (the same engine, no server) - reading works, writing (copy, set, an edit) needs a server and says so.

  pol board layout <config> [--board B] [--scheme S] [--steps] [--json] [--api URL]      the layout of a built config on a bench board: the gate's verdict, parts, wires; --steps = the walkthrough
  pol board layout boards [--json] [--api URL]                                            the board family (half 400 ties, full 830, the UNO, protoboard + pcb reserved) and the bench's boards
  pol board layout <config> edit <part:REF|wire:NAME> <holes|colour> <value...> [--who W] [--note N] [--dry-run] [--clear] [--board B] --api URL
  pol board wire-colors show [--json] [--api URL]
  pol board wire-colors copy <from> <new> [key=colour ...] --api URL                       (a seeded scheme is copied before an edit)
  pol board wire-colors set <name> <key> <colour> --api URL

Exit 0 ok, 1 refused (the words are printed), 2 bad usage.
"""
import argparse
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


def _call(api, method, path, body=None, timeout=120):
    req = urllib.request.Request(api.rstrip('/') + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json'} if body is not None else {}, method=method)
    from polariApiServer import outbound
    try:
        with outbound.http_request('self', 'electrodevice', method, req, means='rest', timeout=timeout, lib='urllib', context=ssl._create_unverified_context()) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:  # noqa: BLE001
            return {'ok': False, 'error': 'HTTP %s' % e.code}
    except (urllib.error.URLError, OSError) as e:
        return {'ok': False, 'error': 'cannot reach %s: %s' % (api, e)}


def _local(fn):
    from electrodevice.custom.layout_words import LayoutRefused
    try:
        return fn()
    except LayoutRefused as e:
        return {'ok': False, 'error': str(e)}


def _q(**kw):
    return '?' + urllib.parse.urlencode({k: v for k, v in kw.items() if v}) if any(kw.values()) else ''


def get_layout(a, config):
    if a.api:
        return _call(a.api, 'GET', '/api/layout/%s%s' % (urllib.parse.quote(config), _q(board=a.board, scheme=a.scheme)))
    from electrodevice.custom import layout_core as C
    return _local(lambda: C.public(C.layout_place(config, a.board, None, a.scheme)))


def get_steps(a, config):
    if a.api:
        return _call(a.api, 'GET', '/api/layout/%s/steps%s' % (urllib.parse.quote(config), _q(board=a.board, scheme=a.scheme)))
    from electrodevice.custom import layout_core as C
    return _local(lambda: C.steps_of(config, a.board, None, a.scheme))


def render_layout(d):
    b, v = d['board'], d['verdict']
    out = ['layout of %s on %s (%s, %d ties)  sha %s' % (d['config'], b['name'], b['model'], b['ties'], d['sha'][:12]),
           'gate  %s' % v['words']]
    for n in d['notes']:
        out.append('note  ' + n)
    out.append('parts')
    for p in d['placements']:
        out.append('  %-5s %-11s %s' % (p['name'], p['part'], ', '.join('%s %s' % (l['name'], l['hole']) for l in p['legs'])))
    out.append('wires')
    for w in d['wires']:
        ov = ' (override; derived %s)' % w['colour'] if w['colour_override'] else ''
        out.append('  %-14s %s:%s -> %s:%s  %s%s  net %s' % (w['name'], w['from']['board'], w['from']['tie'], w['to']['board'], w['to']['tie'], w['colour_effective'], ov, w['net']))
    if d['edits']['count']:
        out.append('edits  %d kept (%s)%s' % (d['edits']['count'], ', '.join(d['edits']['applied']) or 'none applied', '; ' + ' | '.join(d['edits']['problems']) if d['edits']['problems'] else ''))
    return '\n'.join(out)


def render_boards(d):
    out = ['models']
    for m in d['models']:
        geo = '%d rows, %d rail holes, %d ties (derived) / %d (sold)%s' % (m['rows'], m['rail_holes'], m['derived_ties'], m['nominal_ties'], '' if m['ties_agree'] else ' DISAGREE') if m['kind'] == 'breadboard' else m['note'] or m['board_definition']
        out.append('  %-16s %-10s %s' % (m['name'], m['kind'], geo))
    out.append('boards on the bench')
    for b in d['boards']:
        out.append('  %-14s %-16s %s%s' % (b['name'], b['model'], b['label'], '   (default)' if b['default'] else ''))
    return '\n'.join(out)


def render_schemes(d):
    out = []
    for s in d['rows']:
        out.append('%s%s  [%s]' % (s['name'], ' (seeded: copy before editing)' if s['seeded'] else '', s['edit_words']))
        out.append('   ' + s['colors_text'])
    return '\n'.join(out)


def main(argv):
    ap = argparse.ArgumentParser(prog='pol board layout|wire-colors', add_help=True)
    ap.add_argument('words', nargs='+')
    ap.add_argument('--board')
    ap.add_argument('--scheme')
    ap.add_argument('--steps', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--api')
    ap.add_argument('--who', default='')
    ap.add_argument('--note', default='')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--clear', action='store_true')
    a = ap.parse_args(argv)
    w = a.words
    verb = w[0]
    if verb == 'wire-colors':
        sub = w[1] if len(w) > 1 else 'show'
        if sub == 'show':
            if a.api:
                d = _call(a.api, 'GET', '/api/layout/wire-colors')
            else:
                from electrodevice.custom import layout_colors as LC
                from electrodevice.objects.layout._shared import SCHEME_DEFAULT, WIRE_COLOURS
                rows = [dict(s, colors_text='; '.join('%s %s' % (k, v) for k, v in sorted(s['colors'].items()))) for s in LC.all_schemes(None).values()]
                d = {'ok': True, 'rows': rows, 'default': SCHEME_DEFAULT, 'colours': [{'name': n, 'hex': h} for n, h in sorted(WIRE_COLOURS.items())]}
            text = render_schemes(d) if d.get('ok') else None
        elif sub == 'copy' and len(w) >= 4:
            colors = dict(x.split('=', 1) for x in w[4:] if '=' in x)
            d = _call(a.api, 'POST', '/api/layout/wire-colors', {'copy_of': w[2], 'name': w[3], 'colors': colors}) if a.api else {'ok': False, 'error': 'copying a scheme keeps a row: give --api URL (a backend)'}
            text = 'copied %s as %s: %s' % (w[2], w[3], '; '.join('%s %s' % kv for kv in sorted(d.get('colors', {}).items()))) if d.get('ok') else None
        elif sub == 'set' and len(w) == 5:
            d = _call(a.api, 'POST', '/api/layout/wire-colors', {'name': w[2], 'set': {w[3]: w[4]}}) if a.api else {'ok': False, 'error': 'setting a colour changes a row: give --api URL (a backend)'}
            text = 'scheme %s: %s is now %s' % (w[2], w[3], w[4]) if d.get('ok') else None
        else:
            print('usage: pol board wire-colors show | copy <from> <new> [key=colour ...] | set <name> <key> <colour>   [--api URL] [--json]')
            return 2
    elif verb == 'layout' and w[1:2] == ['boards'] or (verb == 'boards'):
        if a.api:
            d = _call(a.api, 'GET', '/api/layout/boards')
        else:
            from electrodevice.custom import layout_core as C
            d = dict(C.boards_listing(None), ok=True)
        text = render_boards(d) if d.get('ok') else None
    elif verb == 'layout' and len(w) >= 2:
        config = w[1]
        if len(w) >= 3 and w[2] == 'edit':
            if len(w) < 5 or not a.api:
                print('usage: pol board layout <config> edit <part:REF|wire:NAME> <holes|colour> <value...> [--who W] [--note N] [--dry-run] [--clear] --api URL')
                return 2
            raw = w[5:]
            value = None if a.clear else (raw[0] if w[4] == 'colour' else raw)
            d = _call(a.api, 'POST', '/api/layout/%s/edit' % urllib.parse.quote(config), {'board': a.board or '', 'subject': w[3], 'field': w[4], 'value': value, 'who': a.who, 'note': a.note,
                                                                                         'clear': a.clear, 'dry_run': a.dry_run})
            text = ('%s\n%s' % ('edit %s' % ('tried (dry run, not kept)' if a.dry_run else 'cleared' if a.clear else 'kept'), render_layout(d))) if d.get('ok') else None
        elif a.steps:
            d = get_steps(a, config)
            text = '\n'.join(['walkthrough of %s on %s  (steps sha %s)  gate: %s' % (d['config'], d['board'], d['sha'][:12], d['verdict']['words'])] + d['walkthrough']) if d.get('ok') else None
        else:
            d = get_layout(a, config)
            text = render_layout(d) if d.get('ok') else None
    else:
        print(__doc__)
        return 2
    if a.json:
        print(json.dumps(d, indent=2, sort_keys=True, default=str))
    elif d.get('ok'):
        print(text)
    else:
        print('[REFUSED] ' + str(d.get('error')))
    return 0 if d.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
