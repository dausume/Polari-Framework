"""
@module board.custom.hwsys_doors

hsp-1 (L9): the bodies of the Hardware System doors, kept out of board_object_api (file size). Each takes the manager and answers (status, payload) over the LIVE rows (the seeds fill what a server lacks, said in
`source`); everything is computed on every read from the owners of each check — nothing is stored, nothing blocks.

GET /api/hardware-systems                        every system: stage, solution, link count, each path's verdict
GET /api/hardware-systems/{name}                 one system: participants, links, path summaries
GET /api/hardware-systems/{name}/links           its SystemLink rows (`rows` for a configured table)
GET /api/hardware-systems/{name}/paths[?path=]   its SignalPath rows with hops (`rows` = paths, `hops` = one row per hop with its path); ?path=<slug> picks one
"""
import json

from board.custom import hardware_system as HS


def _built(manager):
    tables = HS.default_tables(manager)
    live = bool(manager is not None and (getattr(manager, 'objectTables', None) or {}).get('EnclosureContact'))
    return HS.build(tables, manager), ('live' if live else 'seed (the live server has no enclosure rows yet)')


def _summary(res, s):
    ps = [p for p in res['SignalPath'] if p['system'] == s['name']]
    return dict(s, link_count=len(json.loads(s['links_refs_json'])), paths=[{'name': p['name'], 'verdict': p['verdict'], 'hop_count': p['hop_count'], 'gap_free': p['gap_free'],
                                                                             'blocked_at': p['blocked_at']} for p in ps])


def systems(manager):
    res, src = _built(manager)
    rows = [_summary(res, s) for s in res['HardwareSystem']]
    return 200, {'ok': True, 'source': src, 'rows': rows, 'count': len(rows)}


def _find(res, name):
    return next((s for s in res['HardwareSystem'] if s['name'] == name), None)


def system_one(manager, name):
    res, src = _built(manager)
    s = _find(res, name)
    if s is None:
        return 404, {'ok': False, 'error': 'no hardware system %r (GET /api/hardware-systems lists them)' % name}
    from board.custom import twin_sessions as TS   # sim-1: the running twin sessions are participants too (`twin:<board>#<n>`)
    return 200, {'ok': True, 'source': src, 'system': _summary(res, s), 'participants': json.loads(s['participants_json']) + TS.participants(manager),
                 'links': [l for l in res['SystemLink'] if l['system'] == name]}


def links(manager, name):
    res, src = _built(manager)
    if _find(res, name) is None:
        return 404, {'ok': False, 'error': 'no hardware system %r (GET /api/hardware-systems lists them)' % name}
    rows = [l for l in res['SystemLink'] if l['system'] == name]
    return 200, {'ok': True, 'source': src, 'system': name, 'rows': rows, 'count': len(rows)}


def paths(manager, name, path=''):
    res, src = _built(manager)
    if _find(res, name) is None:
        return 404, {'ok': False, 'error': 'no hardware system %r (GET /api/hardware-systems lists them)' % name}
    ps = [p for p in res['SignalPath'] if p['system'] == name and (not path or p['name'].endswith(':' + path))]
    if path and not ps:
        return 404, {'ok': False, 'error': 'no path %r on %s (%s)' % (path, name, ', '.join(p['name'].partition(':')[2] for p in res['SignalPath'] if p['system'] == name))}
    hops = [dict(h, path=p['name']) for p in ps for h in json.loads(p['hops_json'])]
    return 200, {'ok': True, 'source': src, 'system': name, 'rows': ps, 'count': len(ps), 'hops': hops}
