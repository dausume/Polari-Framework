"""
@cross-cutting
@module topology.topology_peering

tpl-2 (AI-Notes/designs/TOPOLOGY_PEERING_DESIGN.md; decisions TAKEN by the user 2026-11-07): Polari backends see each other
WITHOUT an isle. Each backend publishes its own rows; each pulls its peers' and keeps them as marked copies.

    self_description(manager) -> {ok, kind 'polari-topology-self', instance, machine, describedAt, rows: {class: [row]}}
        ONLY rows that describe this backend: its InstanceDefinition, its machine, assignments on it, edges it consumes,
        connections to or from it, and its tpl-1 links (engine workers + their capability rows). Never a peer copy, so
        pulls cannot echo. D-tpl2-a: the door is OPEN for now ("we can secure further later").
    peer_sources(manager) -> [{name, url, sources: [...]}]
        D-tpl2-b, BOTH: PeerNode rows (the agreement handshake: 'agreed') and a configured list a pre-made configuration
        ships, which survives a reboot: knob POLARI_TOPOLOGY_PEERS ('name=url,...' or bare URLs: 'configured-env') and
        the JSON file named by POLARI_TOPOLOGY_PEERS_FILE ([{name, url}]: 'configured-file'). Deduplicated by URL; this
        backend itself is never its own peer.
    pull_peers(manager, fetch=None) -> {ok, peers: [{name, url, sources, ok, words, created, updated, retired, conflicts}],
                                       problems, words}
        GET <url>/api/topology/self through the outbound seam (kind 'peer', verified TLS by default) and merge, D-tpl2-c:
        a copy is the peer's: it is created or updated from the peer, and retired when the peer stops listing it. A row
        that already exists here under that name and is NOT that peer's copy (this backend's own, a person's, the
        example) is KEPT and reported as a conflict, never overwritten. A failed pull keeps the copies and says so.
        Copies carry '(tpl-2 peer:<name> <time>)' in notes; provenance() reads that as 'peer'. Durable first: the
        topology_example_retire helpers (a refused save is reported, memory follows the database).
    peers_report(manager) -> the sources plus each peer's last pull (in memory since this backend started) and age.

  THE CHANGE SIGNAL (instead of a STOMP subscription per peer: works one-way, through proxies, with no long-lived socket):
    self_digest(manager) -> {kind 'polari-topology-self-digest', instance, digest}: a fingerprint of self_description's rows.
    check_peers(manager)  -> GET each peer's /api/topology/self/digest; pull ONLY the peers whose digest changed.
    notify_peers(manager) -> POST {"from": <this instance>} to each named peer's /api/topology/peers/nudge.
    nudge(manager, sender) -> a peer says it changed: pull it now, if it is a peer this backend already names (by name, or
                             the instance its URL last answered as), at most once per NUDGE_MIN_S. Anything else: nothing.
    local_changed()       -> wake the loop now (module admitted / put away, a binding changed), so own changes go out at once.
    tick(manager, state)  -> one loop step: own digest changed -> notify; full pull every PULL_S; else check every CHECK_S.
    start_peer_puller(manager) -> the daemon thread running tick.

Knobs (labelled): POLARI_TOPOLOGY_PEERS, POLARI_TOPOLOGY_PEERS_FILE, POLARI_TOPOLOGY_PEER_PULL_S (full pull, default 300 s;
0 = peering timer OFF), POLARI_TOPOLOGY_PEER_CHECK_S (digest check + own-change detection, default 15 s; 0 = full pulls only),
POLARI_ISLE_EVIDENCE_MAX_AGE_S (a last good pull older than this reads 'stale', the tpl-4 rule).
"""
import json
import os
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from topology.topology_io import PACKAGE_FIELDS, _VOLATILE

KIND = 'polari-topology-self'
PEER_TAG = '(tpl-2 peer:'
CLASSES = ('PolariNodeMachine', 'InstanceDefinition', 'ModuleAssignment', 'ModuleDependencyEdge', 'ServiceConnection')
PEERS_KNOB, FILE_KNOB, PULL_KNOB = 'POLARI_TOPOLOGY_PEERS', 'POLARI_TOPOLOGY_PEERS_FILE', 'POLARI_TOPOLOGY_PEER_PULL_S'
CHECK_KNOB = 'POLARI_TOPOLOGY_PEER_CHECK_S'
DEFAULT_PULL_S, DEFAULT_CHECK_S, NUDGE_MIN_S = 300, 15, 2
DIGEST_KIND = 'polari-topology-self-digest'
_WAKE = threading.Event()
_LAST = {}                      # url -> the last pull result (since this process started)
_PULLER = {'thread': None}


def _rows(manager, cls):
    return list((getattr(manager, 'objectTables', None) or {}).get(cls, {}).values())


def _now():
    return datetime.now(timezone.utc)


def is_peer_copy(row):
    return PEER_TAG in (getattr(row, 'notes', '') or '') or str(getattr(row, 'source', '') or '').startswith('peer:')


def _val(row, field):
    """A field as the wire carries it: an attribute a row never set reads '' (self_description sends '' for it too)."""
    v = getattr(row, field, '')
    return '' if v is None else v


def _fields(cls):
    return [f for f in PACKAGE_FIELDS[cls] if f not in _VOLATILE and f != 'topology_name']


def self_description(manager):
    from topology.topology_self import _TAG as LINK_TAG, instance_name, machine_name
    me, machine = instance_name(), machine_name()
    out = {c: [] for c in CLASSES}
    for cls in CLASSES:
        for r in _rows(manager, cls):
            if is_peer_copy(r):
                continue
            link = LINK_TAG in (getattr(r, 'notes', '') or '')
            mine = {
                'PolariNodeMachine': bool(machine) and getattr(r, 'name', '') == machine,
                'InstanceDefinition': getattr(r, 'name', '') == me or link,
                'ModuleAssignment': getattr(r, 'instance_name', '') == me or link,
                'ModuleDependencyEdge': getattr(r, 'consumer_instance_name', '') == me,
                'ServiceConnection': me in (getattr(r, 'from_instance_name', ''), getattr(r, 'to_instance_name', '')),
            }[cls]
            if mine:
                out[cls].append({f: _val(r, f) for f in _fields(cls)})
        out[cls].sort(key=lambda d: d.get('name', ''))
    return {'ok': True, 'kind': KIND, 'instance': me, 'machine': machine, 'describedAt': _now().isoformat(), 'rows': out,
            'digest': _digest(me, machine, out)}


def _digest(me, machine, rows):
    import hashlib
    return hashlib.sha256(json.dumps([me, machine, rows], sort_keys=True).encode('utf-8')).hexdigest()


def self_digest(manager):
    d = self_description(manager)
    return {'ok': True, 'kind': DIGEST_KIND, 'instance': d['instance'], 'digest': d['digest']}


def _name_from_url(url):
    host = urlsplit(url).hostname or ''
    if host.startswith('api.') and host.endswith('.isle') and host.count('.') == 2:
        return host[len('api.'):-len('.isle')]
    return host or url


def _norm(url):
    return (url or '').strip().rstrip('/')


def peer_sources(manager):
    from topology.topology_self import instance_name
    me = instance_name()
    found = {}

    def add(name, url, source):
        url = _norm(url)
        if not url.startswith(('http://', 'https://')):
            return
        name = (name or '').strip() or _name_from_url(url)
        if name == me or _name_from_url(url) == me:
            return
        entry = found.setdefault(url, {'name': name, 'url': url, 'sources': []})
        if source not in entry['sources']:
            entry['sources'].append(source)
    for p in _rows(manager, 'PeerNode'):
        add(getattr(p, 'name', ''), getattr(p, 'base_url', ''), 'agreed')
    for item in (os.environ.get(PEERS_KNOB) or '').split(','):
        item = item.strip()
        if item:
            name, _, url = item.partition('=') if '=' in item and not item.startswith('http') else ('', '', item)
            add(name, url, 'configured-env')
    path = (os.environ.get(FILE_KNOB) or '').strip()
    if path:
        try:
            with open(path, encoding='utf-8') as fh:
                for e in json.load(fh) or []:
                    if isinstance(e, dict):
                        add(str(e.get('name') or ''), str(e.get('url') or ''), 'configured-file')
                    elif isinstance(e, str):
                        add('', e, 'configured-file')
        except Exception as exc:  # noqa: BLE001 - a broken file is a finding in words
            found['!file'] = {'name': '', 'url': '', 'sources': ['configured-file'],
                              'error': '%s=%s unreadable (%s: %s)' % (FILE_KNOB, path, type(exc).__name__, exc)}
    return sorted(found.values(), key=lambda e: (e['name'], e['url']))


def _default_fetch(name, url, timeout=10):
    from polariApiServer import outbound
    with outbound.http_request('peer', name or 'polari-peer', 'GET', url, means='rest', timeout=timeout, lib='urllib') as resp:
        return json.loads(resp.read().decode('utf-8'))


def _valid(desc, peer_name, me):
    if not isinstance(desc, dict) or desc.get('kind') != KIND or not isinstance(desc.get('rows'), dict):
        return 'not a polari-topology-self description'
    if desc.get('instance') in ('', None):
        return 'the description names no instance'
    if desc.get('instance') == me:
        return 'the description claims to be this backend (%s)' % me
    return ''


def _merge_one(manager, peer, desc, stamp):
    from topology.topology_example_retire import _classes, _delete, _save, _set
    from topology.topology_self import instance_name
    me = instance_name()
    tag = '%s%s %s)' % (PEER_TAG, peer['name'], stamp)
    res = {'created': [], 'updated': [], 'retired': [], 'conflicts': [], 'problems': []}
    topo = next((t for t in _rows(manager, 'TopologyDefinition') if getattr(t, 'is_active', False)), None)
    topo_name = getattr(topo, 'name', '') if topo else ''
    classes = _classes()
    listed = set()
    for cls in CLASSES:
        for entry in (desc['rows'].get(cls) or []):
            if not isinstance(entry, dict) or not entry.get('name'):
                continue
            name = str(entry['name'])
            if cls == 'InstanceDefinition' and name == me:
                res['conflicts'].append({'class': cls, 'name': name, 'why': 'the peer describes this backend; ignored'})
                continue
            listed.add((cls, name))
            fields = {f: entry[f] for f in _fields(cls) if f in entry and f not in ('name', 'notes', 'source')}
            notes = '%s %s' % (tag, str(entry.get('notes') or '').replace('(tpl-0)', '').replace('(tpl-1)', '').strip())
            row = next((r for r in _rows(manager, cls) if getattr(r, 'name', '') == name), None)
            if row is not None and not is_peer_copy(row):
                same = all(_val(row, f) == v for f, v in fields.items())
                res['conflicts'].append({'class': cls, 'name': name, 'why': 'a row here already has this name ('
                                         + ('same values' if same else 'different values') + '); kept, the peer copy not written'})
                continue
            if row is not None and PEER_TAG + peer['name'] + ' ' not in (getattr(row, 'notes', '') or ''):
                res['conflicts'].append({'class': cls, 'name': name, 'why': 'already copied from another peer; kept'})
                continue
            if row is None:
                kw = dict(fields, name=name, notes=notes, topology_name=topo_name)
                if cls == 'PolariNodeMachine':
                    kw['source'] = 'peer:%s' % peer['name']
                row = classes[cls](**kw, manager=manager)
                err = _save(manager, row, cls)
                if err:
                    from topology.topology_example_retire import _forget
                    _forget(manager, cls, row)
                    res['problems'].append(err)
                    continue
                res['created'].append('%s:%s' % (cls, name))
            else:
                changed = {f: v for f, v in fields.items() if _val(row, f) != v}
                old = {f: getattr(row, f, None) for f in list(changed) + ['notes', 'topology_name']}
                for f, v in changed.items():
                    setattr(row, f, v)
                row.notes, row.topology_name = notes, topo_name
                err = _save(manager, row, cls)
                if err:
                    for f, v in old.items():
                        setattr(row, f, v)
                    res['problems'].append(err)
                    continue
                if changed:
                    res['updated'].append('%s:%s' % (cls, name))
    for cls in reversed(CLASSES):                     # what the peer no longer lists: retired here
        for row in _rows(manager, cls):
            if PEER_TAG + peer['name'] + ' ' in (getattr(row, 'notes', '') or '') and (cls, row.name) not in listed:
                err = _delete(manager, cls, row)
                if err:
                    res['problems'].append(err)
                else:
                    res['retired'].append('%s:%s' % (cls, row.name))
    return res


def pull_peers(manager, fetch=None, only=None):
    from topology.topology_self import instance_name
    me = instance_name()
    fetch = fetch or _default_fetch
    peers, problems = [], []
    for peer in peer_sources(manager):
        if only is not None and peer.get('url') not in only:
            continue
        if peer.get('error'):
            problems.append(peer['error'])
            continue
        stamp = _now().isoformat()
        out = dict(peer, ok=False, attemptedAt=stamp, created=[], updated=[], retired=[], conflicts=[])
        try:
            desc = fetch(peer['name'], peer['url'] + '/api/topology/self')
        except Exception as exc:  # noqa: BLE001 - a dead peer is words, never a crash; its copies stay
            out['words'] = 'unreachable (%s: %s); its copies here are kept' % (type(exc).__name__, exc)
        else:
            bad = _valid(desc, peer['name'], me)
            if bad:
                out['words'] = 'refused: %s; its copies here are kept' % bad
            else:
                res = _merge_one(manager, peer, desc, stamp)
                out.update(res)
                out['ok'] = not res['problems']
                out['instance'] = desc.get('instance')
                if out['ok']:
                    out['pulledAt'] = stamp
                    out['digest'] = desc.get('digest', '')
                out['words'] = ('%s (%s): %d created, %d updated, %d retired, %d conflict%s%s'
                                % (desc.get('instance'), peer['url'], len(res['created']), len(res['updated']),
                                   len(res['retired']), len(res['conflicts']), '' if len(res['conflicts']) == 1 else 's',
                                   '; PROBLEMS: ' + '; '.join(res['problems']) if res['problems'] else ''))
                problems.extend(res['problems'])
        prev = _LAST.get(peer['url']) or {}
        if not out.get('pulledAt') and prev.get('pulledAt'):
            out['pulledAt'] = prev['pulledAt']
        _LAST[peer['url']] = out
        peers.append(out)
    ok = not problems and all(p['ok'] for p in peers)
    return {'ok': ok, 'peers': peers, 'problems': problems,
            'words': '%d peer%s pulled: %s' % (len(peers), '' if len(peers) == 1 else 's',
                                                '; '.join(p['words'] for p in peers) or 'none configured or agreed')}


def check_peers(manager, fetch=None):
    """The cheap change check: pull only the peers whose published digest differs from the one last pulled."""
    fetch = fetch or _default_fetch
    changed, words = [], []
    for peer in peer_sources(manager):
        if peer.get('error'):
            continue
        last = _LAST.get(peer['url']) or {}
        try:
            d = fetch(peer['name'], peer['url'] + '/api/topology/self/digest')
        except Exception as exc:  # noqa: BLE001 - a missed check is caught by the next full pull
            words.append('%s: digest unreachable (%s)' % (peer['name'], type(exc).__name__))
            continue
        if not isinstance(d, dict) or d.get('kind') != DIGEST_KIND:
            words.append('%s: no digest door (an older backend); full pulls only' % peer['name'])
            continue
        if d.get('digest') != last.get('digest'):
            changed.append(peer['url'])
    pulled = pull_peers(manager, fetch=fetch, only=set(changed)) if changed else None
    return {'ok': pulled is None or pulled['ok'], 'changed': changed, 'pulled': pulled,
            'words': '; '.join(words + ['%d changed' % len(changed)])}


def _default_send(name, url, body, timeout=5):
    import urllib.request
    from polariApiServer import outbound
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), method='POST',
                                 headers={'Content-Type': 'application/json'})
    with outbound.http_request('peer', name or 'polari-peer', 'POST', req, means='rest', timeout=timeout, lib='urllib') as resp:
        return json.loads(resp.read().decode('utf-8') or '{}')


def notify_peers(manager, send=None):
    """Tell each named peer this backend changed (they pull it at once). Best effort, never raises."""
    from topology.topology_self import instance_name
    send = send or _default_send
    out = []
    for peer in peer_sources(manager):
        if peer.get('error'):
            continue
        try:
            send(peer['name'], peer['url'] + '/api/topology/peers/nudge', {'from': instance_name()})
            out.append('%s nudged' % peer['name'])
        except Exception as exc:  # noqa: BLE001
            out.append('%s not nudged (%s)' % (peer['name'], type(exc).__name__))
    return out


def nudge(manager, sender, fetch=None, now=None):
    sender = str(sender or '').strip()
    now = now or _now()
    known = [p for p in peer_sources(manager) if not p.get('error') and sender and
             (p['name'] == sender or (_LAST.get(p['url']) or {}).get('instance') == sender)]
    if not known:
        return {'ok': False, 'pulled': None, 'words': '%r is not a peer this backend names; nothing pulled' % sender}
    from topology.topology_isle_needs import _ts
    due = []
    for p in known:
        last = _ts((_LAST.get(p['url']) or {}).get('attemptedAt'))
        if last is None or (now - last).total_seconds() >= NUDGE_MIN_S:
            due.append(p['url'])
    if not due:
        return {'ok': True, 'pulled': None, 'words': 'pulled %s less than %d s ago; nothing more to do' % (sender, NUDGE_MIN_S)}
    pulled = pull_peers(manager, fetch=fetch, only=set(due))
    return {'ok': pulled['ok'], 'pulled': pulled, 'words': 'nudged by %s: %s' % (sender, pulled['words'])}


def local_changed():
    """This backend's own rows may have changed: wake the loop so its peers hear now (never raises)."""
    _WAKE.set()


def _check_interval():
    try:
        return max(0, int(os.environ.get(CHECK_KNOB) or DEFAULT_CHECK_S))
    except ValueError:
        return DEFAULT_CHECK_S


def tick(manager, state, fetch=None, send=None, now=None):
    """One loop step. state = {'own': last own digest or None, 'full': monotonic time of the last full pull or None}."""
    now = time.monotonic() if now is None else now
    done = {}
    own = self_digest(manager)['digest']
    if state.get('own') is not None and own != state['own']:
        done['notified'] = notify_peers(manager, send=send)
    state['own'] = own
    if not peer_sources(manager):
        return done
    if state.get('full') is None or now - state['full'] >= _interval():
        done['pull'] = pull_peers(manager, fetch=fetch)
        state['full'] = now
    elif _check_interval():
        done['check'] = check_peers(manager, fetch=fetch)
    return done


def peers_report(manager, now=None):
    from topology.topology_isle_needs import _max_age, _ts
    now = now or _now()
    max_age = _max_age()
    out = []
    for peer in peer_sources(manager):
        last = _LAST.get(peer.get('url', '')) or {}
        pulled = _ts(last.get('pulledAt'))
        age = int((now - pulled).total_seconds()) if pulled else None
        state = ('error' if peer.get('error') else 'not-pulled-yet' if not last
                 else 'stale' if age is None or age > max_age else ('ok' if last.get('ok') else 'failed'))
        copies = sum(1 for cls in CLASSES for r in _rows(manager, cls)
                     if PEER_TAG + peer.get('name', '') + ' ' in (getattr(r, 'notes', '') or ''))
        out.append(dict(peer, state=state, lastAttemptAt=last.get('attemptedAt', ''), pulledAt=last.get('pulledAt', ''),
                        ageSeconds=age, copies=copies, words=peer.get('error') or last.get('words')
                        or 'not pulled since this backend started'))
    return {'ok': True, 'maxAgeS': max_age, 'pullEveryS': _interval(), 'checkEveryS': _check_interval(), 'peers': out,
            'words': '%d peer%s (%s)' % (len(out), '' if len(out) == 1 else 's',
                                        ', '.join('%s %s' % (p['name'], p['state']) for p in out) or
                                        'none: set %s / %s, or agree a peer' % (PEERS_KNOB, FILE_KNOB))}


def _interval():
    try:
        return max(0, int(os.environ.get(PULL_KNOB) or DEFAULT_PULL_S))
    except ValueError:
        return DEFAULT_PULL_S


def start_peer_puller(manager, first_delay_s=5):
    """One daemon thread per process; nothing when the interval is 0. -> words."""
    every = _interval()
    if every == 0:
        return 'peer pulls off (%s=0)' % PULL_KNOB
    if _PULLER['thread'] is not None and _PULLER['thread'].is_alive():
        return 'peer puller already running'

    def run():
        time.sleep(first_delay_s)
        state = {'own': None, 'full': None}
        while True:
            try:
                tick(manager, state)
            except Exception as exc:  # noqa: BLE001 - the puller never dies of one bad cycle
                print('[Topology] peer tick failed: %s: %s' % (type(exc).__name__, exc), flush=True)
            _WAKE.wait(timeout=_check_interval() or every)
            _WAKE.clear()
    t = threading.Thread(target=run, daemon=True, name='topology-peer-pull')
    t.start()
    _PULLER['thread'] = t
    return 'peer pulls every %d s (%s), change checks every %s (%s)' % (every, PULL_KNOB,
                                                                     '%d s' % _check_interval() if _check_interval() else 'never',
                                                                     CHECK_KNOB)
