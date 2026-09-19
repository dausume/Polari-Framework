"""
security.custom.security_objects_view — THE `objects` TOPOLOGY VIEW (ct-5; design
CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §7).

The os / network / app views answer *who can reach what*. None of them has a payload column, so none of them can
answer his actual question: *"we are going to want to make topologies of objects that track how object instances
may propagate between systems"*. This is the fourth view, and the difference is one word — **what** flows, not
only whether something may.

    build(manager, scenario, mode)     nodes + edges, every edge carrying `payload` (the classes it carries)
    simulate(manager, scenario, actor, mode)   everything one class / one profile / this instance can send, and where
    compare(manager, mode)             the same flows across the four MODES (see COMPARE_AXIS below)
    drift(manager)                     declared − observed and observed − declared, per app, with coverage

TWO PROVENANCES, ONE VOCABULARY (design §7).

  **declared** — what somebody SAID may flow:
      · the CONFIRMED `OutboundPolicy` / `InboundPolicy` rows (ct-9, `security_traffic.declared_flows`), which is
        a deployment's statement, ruled on by a person; and
      · every module manifest's `app.flows` stanza (ct-7, design §9), which is the APP AUTHOR's statement, at the
        level an author can honestly make one — a system KIND, never a host.
  **observed** — what the causal map actually recorded (`CausalEdge`): the `external:` and `peer:` effects the
      outbound wrapper wrote (means `rest` / `json-rpc` / `s3` / `sdk` / `shared-db` / `lease-write` /
      `bundle-export` / `bundle-install` / …), and the `ws-publish` / `ws-subscribe` crossings, whose payload is
      the broadcast class itself.

`compare(declared, observed)` is therefore the DRIFT REPORT: a class flowing with nothing declaring it is a
FINDING (dev warns, never blocks — §17), and a declaration nothing has ever exercised is noise to prune.

**"NOT TRACED", NEVER "NOTHING"** (design §2, and the rule this view would be dishonest without). The observed
half exists only for classes that have been a `TraceTarget` — one class at a time, on purpose. So every answer
here carries `coverage` (every class ever armed) and `not_traced` (the classes in this answer that never have
been), and a drift row for an untraced class reads **not traced**, never *nothing flows*.

**NO INSTANCE IDS.** Design §7's last line: the topology is classes and counts. An instance is looked up in the
effect journal, which is dev-only and cleared on the next arm; nothing on this view can identify a row, a person
or an address.

THE MODES, for THIS view (the other three read them as rings of the machine; here they are the traffic policy's
ladder, which is what decides whether an object may leave):

    stock     no Polari traffic policy at all — every flow leaves, which is what an unguarded instance does
    today     what the knob really says here and now (`POLARI_APP_PERMISSIONS` × the policy rows' states)
    complain  dev, suggested-only: a confirmed flow is allowed, everything else is LOGGED and proceeds
    enforce   production, closed by default: only a CONFIRMED row allows; everything else is blocked
"""

#: the view's name in `SecurityTopologyNode/Edge.view` and in `?view=`
VIEW = 'objects'

#: this instance, as a node. Never a hostname — a deployment's name is a deployment's business (D18-1's sibling
#: rule for machines: the rows of this arc carry kinds and configured names, never addresses).
INSTANCE_NODE = 'this instance'
#: where a change BROADCAST goes: to whoever is subscribed, which STOMP does not name
BROADCAST_NODE = 'subscribers (STOMP)'

#: `compare` for this view puts the four MODES on the columns, not the scenarios: an object flow belongs to the
#: INSTANCE (its policies, its manifests, its map), not to the machine layout a scenario describes, so a
#: scenario-per-column table would repeat one answer four times. `scenarios` still carries the column names so
#: the configured panel lines the table up the same way it does for the other three views; `axis` says what they
#: are, so nothing has to guess.
COMPARE_AXIS = 'mode'

#: the systems that decide an object flow. Local to this view rather than added to `security_facts.SYSTEMS`:
#: those are the machine's rings (docker, the kernel, qemu, AppArmor) and every one of them gets a
#: `SecurityControl` row per scenario. These four are Polari code paths, and a row per scenario would say the
#: same thing five times.
OBJECT_SYSTEMS = {
    'app-flows': {'title': 'The app\'s own declaration (manifest `app.flows`)', 'provenance': 'polari',
                  'note': 'what the module SAYS its rows do: a system kind, the classes, the direction. Nothing '
                          'derives it and nothing enforces it — an undeclared flow is a finding, and dev warns.'},
    'traffic-policy': {'title': 'The traffic policy (OutboundPolicy / InboundPolicy)', 'provenance': 'polari',
                       'note': 'closed by default (design §5a): only a row a PERSON confirmed lets traffic '
                               'through under enforce; `suggested` is a proposal, never a grant.'},
    'outbound-wrapper': {'title': 'The outbound wrapper (polariApiServer.outbound)', 'provenance': 'polari',
                         'note': 'the ONE seam every call to another system passes, and therefore the edge of '
                                 'what Polari can see. Past it we notate the system and the wire, nothing more.'},
    'app-permissions': {'title': 'The CRUDE / STOMP permission gate', 'provenance': 'polari',
                        'note': 'a broadcast reaches whoever may `read` the class (ct-6) — per subscriber, so '
                                'this view says LOGGED and names the gate rather than guessing a verdict.'},
    'causal-map': {'title': 'The causal map (CausalEdge — one class at a time)', 'provenance': 'polari',
                   'note': 'records only while a TraceTarget is armed. A class that has never been armed answers '
                           'NOT TRACED, which is not the same as nothing flowing.'},
}

#: means that carry ROWS out of this instance, as the map spells them
OUT_MEANS = ('rest', 'json-rpc', 's3', 'grpc', 'mqtt', 'sdk', 'probe', 'send',
             'shared-db', 'lease-write', 'bundle-export', 'bundle-install')
#: means that carry rows over the change broadcast
WS_MEANS = ('ws-publish', 'ws-subscribe')


# ---- the declared half ------------------------------------------------------------------------------------

#: the manifests are files on disk and do not change while the process runs, and `compare` builds this view once
#: per mode — so the ~60 JSON reads are done ONCE and kept. `refresh=True` re-reads (the selftest, and a dev loop
#: that has just run `manifests generate`).
_MANIFEST_CACHE = {}


def manifest_flows(packages=None, refresh=False):
    """Every module manifest's `app.flows` (ct-7, design §9) as declared flows.

    THE READER ct-5 CONSUMES. It is deliberately tolerant: the stanza is optional, a manifest that is missing or
    unreadable contributes nothing, and a malformed entry is skipped rather than raised on — `moduleService.
    manifests.flow_findings` is where a bad stanza is REPORTED, and a topology view is not a validator."""
    key = tuple(sorted(packages)) if packages is not None else ''
    if not refresh and key in _MANIFEST_CACHE:
        return [dict(f) for f in _MANIFEST_CACHE[key]]
    out = []
    try:
        from moduleService import manifests as M
    except Exception:                       # noqa: BLE001 — no manifest layer: nothing is declared, and we say so
        return out
    try:
        names = list(packages) if packages is not None else M.all_packages()
    except Exception:                       # noqa: BLE001
        return out
    for pkg in sorted(names):
        try:
            manifest = M.load(pkg) or {}
        except Exception:                   # noqa: BLE001
            continue
        flows = ((manifest.get('app') or {}).get('flows'))
        if not isinstance(flows, list):
            continue
        for flow in flows:
            if not isinstance(flow, dict):
                continue
            kind = str(flow.get('to') or '').strip()
            if not kind:
                continue
            classes = sorted({str(c).strip() for c in (flow.get('classes') or []) if str(c).strip()})
            out.append({'provenance': 'declared', 'origin': 'app.flows', 'module': pkg,
                        'kind': kind, 'name': str(flow.get('name') or '').strip(),
                        'means': 'declared', 'direction': str(flow.get('direction') or 'both'),
                        'classes': classes, 'count': 0,
                        'declared_by': 'app.flows:%s' % pkg,
                        'why': str(flow.get('why') or '')})
    _MANIFEST_CACHE[key] = [dict(f) for f in out]
    return out


# ---- the origin, coarsened (D-2, round-5 live proof) ------------------------------------------------------
#
# ct-9 stores an inbound `origin` row as `scheme://host` — deliberately, because a person confirming a source
# has to be able to tell one browser origin from another, and that door is behind an admin bearer. This VIEW is
# not that door. It promises, in its own node description, that *"no hostname and no address appears on this
# view"*, and §67 lists "no instance ids, no addresses, no hostnames anywhere on the view" among its selftested
# checks. The live proof found the promise broken the moment an origin row is confirmed, which is the normal
# outcome of a browser using the stack: `external:origin:https://prf.<lan>.nip.io` appeared as a node, a node
# TITLE, an edge target, a drift entry and a summary row — and on a nip.io host that string is a hostname AND
# the LAN address it encodes.
#
# So the view renders an origin at the only resolution it actually needs: is this one of the hosts this
# deployment configured as its own, or somebody else? The exact origin stays available, signed in, at
# GET /api/security/traffic (and /traffic/declared) where a person rules on it.

#: the `scheme://host` values this deployment calls its own — the CORS allow-list is the authoritative list
#: (it is literally "the origins this API answers"), plus the configured frontend and backend names.
_OWN_ORIGINS = {}


def own_origins(refresh=False):
    """`{host}` — the hosts this instance serves itself on, lower-cased, ports stripped.

    Read from the runtime config: `api.cors_origins` (the CORS allow-list, the one place a deployment states
    which front ends are its own), plus `frontend.url` and `backend.url`. Never raises; an instance that
    configures none of them simply calls every origin `other`, which is the safe answer."""
    if _OWN_ORIGINS and not refresh:
        return set(_OWN_ORIGINS.get('hosts') or ())
    hosts = set()
    try:
        from config_loader import config
        values = []
        raw = config.get('api.cors_origins', []) or []
        values += ([v.strip() for v in raw.split(',')] if isinstance(raw, str) else list(raw))
        for key in ('frontend.url', 'backend.url'):
            one = config.get(key, '')
            if one:
                values.append(str(one))
        for value in values:
            host = _host_of(value)
            if host and host != '*':
                hosts.add(host)
    except Exception:                       # noqa: BLE001 — no config is "nothing is mine", not a failure
        pass
    _OWN_ORIGINS['hosts'] = set(hosts)
    return set(hosts)


def _host_of(value):
    """`https://app.example:4200/x` → `app.example`. '' when there is no host to find."""
    raw = str(value or '').strip()
    if not raw:
        return ''
    rest = raw.partition('://')[2] or raw
    host = rest.split('/')[0].split('?')[0].strip().lower()
    if host.startswith('['):                # [::1]:4200
        return host.split(']')[0] + ']'
    return host.split(':')[0] if host.count(':') == 1 else host


#: source names that are already a CLASS rather than an identity — ct-9 writes these on purpose and they carry
#: nothing to leak, so they pass through unchanged.
SAFE_SOURCE_NAMES = ('anonymous', 'ip-literal', 'unregistered', '')


def coarsen_source(kind, name):
    """What this view is allowed to RENDER for an inbound source (D-2).

    An `origin` becomes `<scheme>:this-instance` when its host is one this deployment configured as its own,
    and `<scheme>:other` otherwise — never the host. Every other source kind is already a NAME or a CLASS
    (a `PeerNode`'s name, `anonymous`, `ip-literal`) and is left exactly as ct-9 wrote it."""
    value = str(name or '')
    if str(kind or '') != 'origin':
        return value
    if value in SAFE_SOURCE_NAMES:
        return value
    scheme = (value.partition('://')[0] or '').strip().lower() if '://' in value else ''
    host = _host_of(value)
    if not scheme or not host:
        # not a shape we can read — say so rather than printing whatever it is
        return 'other'
    return '%s:%s' % (scheme, 'this-instance' if host in own_origins() else 'other')


def policy_flows(manager):
    """The CONFIRMED `OutboundPolicy` / `InboundPolicy` rows as declared flows — ct-9's `declared_flows()`,
    which has been waiting for exactly this caller, translated into this view's vocabulary."""
    out = []
    try:
        from security.custom.security_traffic import declared_flows
        rows = declared_flows(manager)
    except Exception:                       # noqa: BLE001 — no traffic module: nothing is declared here
        return out
    for row in rows:
        if row.get('direction') == 'outbound':
            out.append({'provenance': 'declared', 'origin': 'OutboundPolicy', 'module': '',
                        'kind': row.get('system_kind', ''), 'name': row.get('system_name', ''),
                        'means': row.get('means', 'send'), 'direction': 'push',
                        'classes': sorted(row.get('classes') or []), 'count': int(row.get('count') or 0),
                        'declared_by': 'OutboundPolicy (confirmed by %s)' % (row.get('confirmed_by') or '-'),
                        'why': ''})
        else:
            kind = row.get('source_kind', '')
            out.append({'provenance': 'declared', 'origin': 'InboundPolicy', 'module': '',
                        'kind': kind,
                        # D-2: what the view may PRINT. The exact origin is on the row and reaches a person
                        # through GET /api/security/traffic, signed in — never through a topology read.
                        'name': coarsen_source(kind, row.get('source_name', '')),
                        'means': 'request', 'direction': 'pull',
                        'classes': sorted(row.get('classes') or []), 'count': int(row.get('count') or 0),
                        'declared_by': 'InboundPolicy (confirmed by %s)' % (row.get('confirmed_by') or '-'),
                        'why': 'an inbound row carries no classes on purpose: what a caller SENDS is known only '
                               'once it reaches a class, and the map records that as an object edge'})
    return out


def declared(manager):
    """Both declared halves, the manifests first (the app author's statement) then the confirmed policy rows."""
    return manifest_flows() + policy_flows(manager)


# ---- the observed half ------------------------------------------------------------------------------------

def _classes_of(detail):
    """The classes an edge carried. `record_outbound` writes them comma-joined into `detail` and nothing else
    does, so this is a split — but a defensive one: a `detail` that is plainly not a class list is ignored
    rather than turned into a class nobody has."""
    parts = [p.strip() for p in str(detail or '').split(',') if p.strip()]
    return sorted({p for p in parts if p and p[0].isupper() and p.replace('_', '').isalnum()})


def observed(manager):
    """The causal map's flow edges (ct-1/ct-2/ct-3) in this view's vocabulary.

    Only `peer:` / `external:` effects and the two `ws-*` means are flows: a `crude` or `trigger-fire` edge is
    causation INSIDE the instance, which the closure already answers and this view deliberately does not repeat."""
    out = []
    try:
        from security.custom.security_trace import edges as _map_rows
        rows = _map_rows(manager)
    except Exception:                       # noqa: BLE001 — no map: nothing is observed, and `coverage` says why
        return out
    for row in rows:
        effect, means = str(row.get('effect') or ''), str(row.get('means') or '')
        evidence = {'count': int(row.get('count') or 0), 'first_seen': row.get('first_seen', ''),
                    'last_seen': row.get('last_seen', ''), 'sample_trace_id': row.get('sample_trace_id', ''),
                    'target': row.get('target', ''), 'cause': row.get('cause', '')}
        if effect.startswith('peer:') or effect.startswith('external:'):
            rest = effect.split(':', 1)[1]
            if effect.startswith('peer:'):
                name, _, node_means = rest.partition(':')
                kind = 'peer'
            else:
                kind, _, name = rest.partition(':')
                node_means = means
            out.append({'provenance': 'observed', 'origin': 'CausalEdge', 'module': '',
                        'kind': kind or 'other', 'name': name or 'unnamed',
                        'means': means or node_means or 'send', 'direction': 'push',
                        'classes': _classes_of(row.get('detail')), 'count': evidence['count'],
                        'node': effect, 'declared_by': '', 'why': '', 'evidence': evidence})
        elif means in WS_MEANS:
            # ws-publish: `object:C:verb → event:topic:C`. ws-subscribe: `endpoint:SUBSCRIBE /topic/C →
            # object:C:events`. Either way the class is the payload and the counterpart is whoever subscribed.
            cls = ''
            for ref in (effect, str(row.get('cause') or '')):
                if ref.startswith('event:topic:'):
                    cls = ref.split(':', 2)[2]
                elif ref.startswith('object:'):
                    cls = cls or ref.split(':')[1]
            out.append({'provenance': 'observed', 'origin': 'CausalEdge', 'module': '',
                        'kind': 'broadcast', 'name': 'stomp', 'means': means, 'direction': 'push',
                        'classes': [cls] if cls else [], 'count': evidence['count'],
                        'node': BROADCAST_NODE, 'declared_by': '', 'why': '', 'evidence': evidence})
    return out


# ---- the policy states that decide a flow -----------------------------------------------------------------

def _policy_states(manager):
    """`{(kind, name, means): state}` for outbound and `{(kind, source): state}` for inbound, read WITHOUT
    healing or writing anything — a topology build is a read."""
    out = {'outbound': {}, 'inbound': {}}
    try:
        from security.custom.security_observe import _all_rows
    except Exception:                       # noqa: BLE001
        return out
    try:
        for row in _all_rows(manager, 'OutboundPolicy'):
            out['outbound'][(str(getattr(row, 'system_kind', '')), str(getattr(row, 'system_name', '')),
                             str(getattr(row, 'means', '')))] = str(getattr(row, 'state', '') or '')
        for row in _all_rows(manager, 'InboundPolicy'):
            out['inbound'][(str(getattr(row, 'source_kind', '')),
                            str(getattr(row, 'source', '')))] = str(getattr(row, 'state', '') or '')
    except Exception:                       # noqa: BLE001
        pass
    return out


def _knob():
    try:
        from accessControl.app_permissions_gate import gate_mode
        return gate_mode()
    except Exception:                       # noqa: BLE001 — an unreadable knob is off
        return 'off'


def _step(system, decision, note=''):
    s = OBJECT_SYSTEMS[system]
    return {'system': system, 'title': s['title'], 'provenance': s['provenance'],
            'decision': decision, 'note': note}


def _verdict(chain):
    """The same rule the other three views use: the first blocker, else anything that logged, else allowed."""
    for st in chain:
        if st['decision'] == 'blocked':
            return 'blocked', st['system'], st['provenance']
    for st in chain:
        if st['decision'] == 'logged':
            return 'logged', st['system'], st['provenance']
    last = next((st for st in reversed(chain) if st['decision'] == 'allowed'), None)
    return 'allowed', (last['system'] if last else ''), (last['provenance'] if last else '')


def _policy_decision(mode, state):
    """What the traffic policy does to a flow under `mode`, given the row's `state` ('' = no row at all)."""
    if mode == 'stock':
        return 'n/a', 'no Polari traffic policy exists in this reading: the send simply leaves'
    if state == 'denied':
        return 'blocked', 'a person DENIED this flow on the record'
    if mode == 'enforce':
        return (('allowed', 'a person confirmed this flow') if state == 'confirmed'
                else ('blocked', 'closed by default: only a CONFIRMED row allows, and this one is %s'
                      % (state or 'not proposed at all')))
    if mode == 'complain':
        return (('allowed', 'a person confirmed this flow') if state == 'confirmed'
                else ('logged', 'dev warns, never blocks: the send proceeds and the would-deny is recorded (%s)'
                      % (state or 'nothing has proposed it yet')))
    knob = _knob()
    if state == 'confirmed':
        return 'allowed', 'a person confirmed this flow (knob %s)' % knob
    if knob == 'off':
        return 'n/a', 'the gate knob is off here: the verdict is computed and nothing acts on it'
    if knob == 'enforce':
        return 'blocked', 'the knob is enforce and this flow is %s' % (state or 'not proposed at all')
    return 'logged', 'the knob is advisory: the send proceeds and rides X-Polari-Traffic-Advisory (%s)' % (
        state or 'nothing has proposed it yet')


def _flow_chain(mode, flow, state, is_declared_by_manifest, traced, inbound_declared=False):
    """The systems consulted for ONE flow, in order, each with its decision under `mode`."""
    chain = []
    if flow['kind'] == 'broadcast':
        chain.append(_step('app-permissions',
                           'allowed' if mode == 'stock' else
                           ('n/a' if (mode == 'today' and _knob() == 'off') else 'logged'),
                           'stock: /topic/<Class> was unauthenticated. Otherwise ct-6 decides PER SUBSCRIBER '
                           'with the same permission_verdict(read) as CRUDE — so this view names the gate '
                           'instead of inventing one verdict for everybody'))
    else:
        if inbound_declared:
            note = ('%s IS the declaration for an inbound flow: `app.flows` is an OUTBOUND vocabulary '
                    '(design §9), so no module can declare who may CALL a deployment — design §7 counts the '
                    'traffic policy a PERSON confirmed as the declaration instead'
                    % (flow.get('declared_by') or 'a confirmed InboundPolicy row'))
        elif is_declared_by_manifest:
            note = '%s declares it' % (flow.get('declared_by') or 'a declaration')
        else:
            note = 'NO manifest declares this flow (design §9): a finding, never a block — dev warns'
        chain.append(_step('app-flows',
                           'n/a' if mode == 'stock' else ('allowed' if is_declared_by_manifest else 'logged'),
                           note))
        decision, note = _policy_decision(mode, state)
        chain.append(_step('traffic-policy', decision, note))
    chain.append(_step('outbound-wrapper', 'allowed',
                       'the call passes the one wrapper, so Polari can name the system and the wire. Beyond it '
                       'Polari cannot see and does not pretend to'))
    chain.append(_step('causal-map', 'allowed' if traced else 'n/a',
                       'the classes on this edge have been traced' if traced else
                       'NOT TRACED: no TraceTarget has ever been armed on these classes, so the map cannot say '
                       'what really flows — that is not the same as nothing flowing'))
    return chain


# ---- the build --------------------------------------------------------------------------------------------

def _counterpart(flow):
    if flow['kind'] == 'broadcast':
        return BROADCAST_NODE
    if flow.get('node'):
        return flow['node']
    if flow['kind'] == 'peer':
        return 'peer:%s' % (flow.get('name') or 'a peer')
    if not flow.get('name'):
        return 'external:%s' % flow['kind']
    return 'external:%s:%s' % (flow['kind'], flow['name'])


def _traced_classes(manager):
    try:
        from security.custom.security_trace import coverage
        return {str(c.get('class_name') or '') for c in coverage(manager)}, coverage(manager)
    except Exception:                       # noqa: BLE001
        return set(), []


def build(manager, scenario='', mode='today'):
    """The `objects` view: nodes (this instance, its classes, its counterparts, the deciding systems) and edges
    (one per class × counterpart × means) each carrying `payload` — the classes, with their counts.

    `scenario` is accepted and echoed for the door's sake and does NOT change the answer: an object flow belongs
    to the instance's policies, manifests and map, not to the machine layout a scenario describes. Saying so is
    better than pretending four identical columns mean something (see COMPARE_AXIS)."""
    flows = declared(manager) + observed(manager)
    states = _policy_states(manager)
    traced, coverage_rows = _traced_classes(manager)
    manifest_kinds = {f['kind'] for f in flows if f.get('origin') == 'app.flows'}

    nodes, edges = [], []
    seen_nodes, class_nodes, counterparts = set(), {}, {}

    def _node(name, kind, layer, title, description='', system=''):
        if name in seen_nodes:
            return
        seen_nodes.add(name)
        nodes.append({'node': name, 'kind': kind, 'layer': layer, 'title': title,
                      'description': description, 'system': system})

    _node(INSTANCE_NODE, 'instance', 0, 'This Polari instance',
          'every flow below starts or ends here; no hostname and no address appears on this view — an '
          'inbound browser ORIGIN is coarsened to this-instance / other, and the exact one is read signed in '
          'at GET /api/security/traffic')
    for system, meta in OBJECT_SYSTEMS.items():
        _node(system, 'boundary', 2, meta['title'], meta['note'], system=system)

    # N-3 (round-5 live proof): a manifest declaration speaks at system-KIND level — an app author cannot know
    # which Keycloak realm or which Odoo a deployment runs. When it names no system, it therefore matches EVERY
    # system of that kind this instance really talks to, instead of standing up a second node of its own
    # (`external:keycloak:realm` beside `external:keycloak:Polari`, which is what the live proof found and which
    # no traffic could ever match).
    named_by_kind = {}
    for f in flows:
        if f['kind'] != 'broadcast' and f.get('name') and f.get('origin') != 'app.flows':
            named_by_kind.setdefault(f['kind'], set()).add(_counterpart(f))

    for flow in flows:
        targets = [_counterpart(flow)]
        if flow.get('origin') == 'app.flows' and not flow.get('name'):
            targets = sorted(named_by_kind.get(flow['kind'], ())) or targets
        state = ('' if flow['kind'] == 'broadcast' else
                 states['outbound'].get((flow['kind'], flow.get('name') or '', flow.get('means') or ''), ''))
        if flow.get('origin') == 'InboundPolicy':
            # `declared_flows()` emits CONFIRMED inbound rows and nothing else, so the state is known without
            # looking the row up by name — which matters because the name this view carries is COARSENED (D-2)
            # and could no longer find the row anyway. `states['inbound']` stays keyed by the real source and
            # is only consulted where the exact source is legitimately in hand.
            state = 'confirmed'
        # N-4: `app.flows` is an OUTBOUND vocabulary, so no module can ever declare who may CALL a deployment —
        # which used to leave every inbound edge logging a permanent finding even after a person had confirmed
        # it. Design §7 counts "a traffic policy a person confirmed" as a declaration in its own right, and for
        # an inbound flow it is the ONLY one there can be.
        inbound_declared = flow.get('origin') == 'InboundPolicy' and state == 'confirmed'
        is_declared = (flow.get('origin') == 'app.flows' or flow['kind'] in manifest_kinds
                       or inbound_declared)
        classes = flow.get('classes') or []
        chain = _flow_chain(mode, flow, state, is_declared, bool(set(classes) & traced) if classes else False,
                            inbound_declared=inbound_declared)
        verdict, decided_by, provenance = _verdict(chain)
        for counterpart in targets:
            counterparts.setdefault(counterpart, flow)
            for cls in (classes or [None]):
                source = INSTANCE_NODE if cls is None else 'class:%s' % cls
                if cls is not None:
                    class_nodes.setdefault(cls, 0)
                    class_nodes[cls] += int(flow.get('count') or 0)
                payload = (('%s×%d' % (cls, int(flow.get('count') or 0)))
                           if (cls and flow.get('count')) else (cls or ''))
                edges.append({
                    'source': source, 'target': counterpart,
                    'means': '%s (%s)' % (flow.get('means') or 'send', flow.get('direction') or 'both'),
                    'chain': chain, 'verdict': verdict, 'decided_by': decided_by, 'provenance': provenance,
                    'payload': payload,
                    'flow_provenance': flow['provenance'],
                    'declared_by': flow.get('declared_by', ''),
                    'count': int(flow.get('count') or 0),
                    'traced': bool(cls and cls in traced),
                    'why': _why(flow, cls, traced),
                })

    for cls, count in sorted(class_nodes.items()):
        _node('class:%s' % cls, 'class', 1, cls,
              'a class carried across a boundary%s; %s'
              % ((' %d time(s)' % count) if count else ' (declared, never yet observed)',
                 'traced' if cls in traced else 'NOT TRACED — no TraceTarget has ever been armed on it'))
    for counterpart, flow in sorted(counterparts.items()):
        kind = flow['kind']
        _node(counterpart, 'peer' if kind == 'peer' else ('broadcast' if kind == 'broadcast' else 'external'), 3,
              counterpart,
              {'peer': 'another Polari instance', 'broadcast': 'whoever is subscribed to the change topic — '
                                                               'STOMP does not name them, and this view does not guess'}
              .get(kind, 'an external system: %s' % kind))

    counts = {'allowed': 0, 'logged': 0, 'blocked': 0}
    for e in edges:
        counts[e['verdict']] = counts.get(e['verdict'], 0) + 1
    report = drift(manager, flows=flows, traced=traced, coverage_rows=coverage_rows)
    return {
        'view': VIEW, 'scenario': scenario, 'route': '', 'mode': mode,
        'title': 'Objects — where the rows go',
        'description': ('the fourth security view (design §7): nodes are this instance, its classes and the '
                        'systems it talks to; every edge says WHICH CLASSES cross it. Declared = the manifests\' '
                        'app.flows and the confirmed traffic policies; observed = the causal map. The difference '
                        'is the drift report. Classes and counts only — an instance id never appears here, and '
                        'neither does a hostname: an inbound origin reads `origin:<scheme>:this-instance` or '
                        '`origin:<scheme>:other`.'),
        'mac_attach': '', 'apps_run': '', 'scenario_source': '',
        'counts': counts, 'layers': sorted({n['layer'] for n in nodes}), 'nodes': nodes, 'edges': edges,
        'payload_column': True,
        'legend': {'declared': 'somebody said it may flow (a manifest app.flows entry, or a traffic policy row a '
                               'person confirmed)',
                   'observed': 'the causal map recorded it flowing, while a TraceTarget was armed',
                   'polari': 'Polari decides this'},
        'drift': report, 'coverage': coverage_rows, 'not_traced': report['not_traced'],
        'summary': [{'source': e['source'], 'means': e['means'], 'target': e['target'], 'payload': e['payload'],
                     'provenance': e['flow_provenance'], 'verdict': e['verdict'], 'decided_by': e['decided_by'],
                     'why': e['why']} for e in edges],
        'how': HOW_OBJECTS,
    }


def _why(flow, cls, traced):
    if flow['provenance'] == 'declared':
        return ('%s declares %s may cross (%s); the map has not recorded it%s'
                % (flow.get('declared_by') or 'a declaration',
                   cls or 'this call, which carries no rows of its own',
                   flow.get('direction') or 'both',
                   ('' if (cls is None or cls in traced) else
                    ' — and %s has never been traced, so "not observed" here means NOT TRACED' % cls)))
    return ('the causal map recorded %s crossing %d time(s) by %s%s'
            % (cls or 'a call carrying no rows', int(flow.get('count') or 0), flow.get('means') or 'send',
               '' if flow.get('declared_by') else ' — nothing declares it (design §9 finding)'))


# ---- the drift report -------------------------------------------------------------------------------------

def drift(manager, flows=None, traced=None, coverage_rows=None):
    """DECLARED − OBSERVED and OBSERVED − DECLARED, per app, with the coverage that keeps it honest (design §7).

    Matching is deliberately at two levels, because the two declarers can honestly say different things:
      · a `app.flows` stanza names a system KIND (an app author cannot know which Odoo a deployment runs), so it
        covers any observed flow of that kind carrying one of its classes;
      · a confirmed `OutboundPolicy` names the CONFIGURED system and the wire, so it covers exactly that.
    An observed flow matched by neither is a FINDING; a declaration nothing has ever exercised is noise to prune.
    Neither is a refusal: dev warns, never blocks (§17).
    """
    if flows is None:
        flows = declared(manager) + observed(manager)
    if traced is None:
        traced, coverage_rows = _traced_classes(manager)
    if coverage_rows is None:
        coverage_rows = []
    decls = [f for f in flows if f['provenance'] == 'declared']
    obs = [f for f in flows if f['provenance'] == 'observed']

    kind_classes, exact = {}, {}
    for d in decls:
        if d.get('origin') == 'app.flows':
            kind_classes.setdefault(d['kind'], set()).update(d['classes'] or [])
            kind_classes.setdefault(d['kind'], set())
        else:
            exact[(d['kind'], d.get('name') or '', d.get('means') or '')] = d

    undeclared, matched = [], set()
    for o in obs:
        if o['kind'] == 'broadcast':
            continue                        # a broadcast is not a send: ct-6's gate declares it, not app.flows
        hit = exact.get((o['kind'], o.get('name') or '', o.get('means') or ''))
        by_kind = o['kind'] in kind_classes and (not o['classes']
                                                 or bool(set(o['classes']) & kind_classes[o['kind']]))
        if hit is not None or by_kind:
            matched.add((o['kind'], o.get('name') or '', o.get('means') or ''))
            continue
        undeclared.append({'kind': o['kind'], 'name': o.get('name') or '', 'means': o.get('means') or 'send',
                           'classes': o['classes'], 'count': o['count'],
                           'app': sorted({_app_of(c) for c in o['classes']} - {''}) or ['(core)'],
                           'evidence': o.get('evidence') or {},
                           'finding': ('OBSERVED FLOWING, DECLARED BY NOTHING: no manifest app.flows entry and no '
                                       'confirmed traffic policy covers %s:%s by %s. Design §9: a finding the '
                                       'first time something flows, never a block — dev warns.'
                                       % (o['kind'], o.get('name') or 'unnamed', o.get('means') or 'send'))})

    observed_kinds = {(o['kind'], o.get('name') or '', o.get('means') or '') for o in obs}
    observed_kind_only = {o['kind'] for o in obs}
    unexercised = []
    for d in decls:
        if d.get('origin') == 'app.flows':
            if d['kind'] in observed_kind_only:
                continue
        elif (d['kind'], d.get('name') or '', d.get('means') or '') in observed_kinds:
            continue
        untraced = sorted(c for c in (d['classes'] or []) if c not in traced)
        unexercised.append({'kind': d['kind'], 'name': d.get('name') or '', 'means': d.get('means') or 'send',
                            'classes': d['classes'], 'declared_by': d.get('declared_by', ''),
                            'module': d.get('module', ''),
                            'app': [d['module']] if d.get('module') else ['(deployment)'],
                            'not_traced': untraced,
                            'finding': ('DECLARED, NEVER OBSERVED: %s says %s may cross, and the map has never '
                                        'recorded it.%s'
                                        % (d.get('declared_by') or 'a declaration',
                                           ', '.join(d['classes']) or 'a call carrying no rows',
                                           (' But %s %s never been armed as a TraceTarget, so this reads NOT '
                                            'TRACED rather than "noise to prune" — arm one and ask again.'
                                            % (', '.join(untraced), 'has' if len(untraced) == 1 else 'have'))
                                           if untraced else
                                           (' Every class here HAS been traced, so this is noise to prune.'
                                            if d['classes'] else
                                            ' It names no classes, so there is nothing for the map to have '
                                            'recorded — the declaration is about the CALL, not about rows.')))})

    by_app = {}
    for item, bucket in ([(u, 'undeclared') for u in undeclared]
                         + [(u, 'unexercised') for u in unexercised]):
        for app in item['app']:
            entry = by_app.setdefault(app, {'app': app, 'undeclared': 0, 'unexercised': 0, 'classes': [],
                                            'not_traced': []})
            entry[bucket] += 1
            for cls in item['classes']:
                if cls not in entry['classes']:
                    entry['classes'].append(cls)
                if cls not in traced and cls not in entry['not_traced']:
                    entry['not_traced'].append(cls)
    for app in sorted({_app_of(c) for f in flows for c in (f['classes'] or [])} - {''}):
        by_app.setdefault(app, {'app': app, 'undeclared': 0, 'unexercised': 0, 'classes': [], 'not_traced': []})
    for entry in by_app.values():
        entry['coverage'] = ('none' if entry['classes'] and len(entry['not_traced']) == len(entry['classes'])
                             else ('full' if not entry['not_traced'] else 'partial'))
        entry['reading'] = ('%s: %d observed flow(s) nothing declares, %d declaration(s) never exercised; '
                            'trace coverage %s%s'
                            % (entry['app'], entry['undeclared'], entry['unexercised'], entry['coverage'],
                               (' (never traced: %s)' % ', '.join(entry['not_traced']))
                               if entry['not_traced'] else ''))

    all_classes = sorted({c for f in flows for c in (f['classes'] or []) if c})
    not_traced = [c for c in all_classes if c not in traced]
    return {
        'observed_not_declared': undeclared,
        'declared_not_observed': unexercised,
        'by_app': [by_app[k] for k in sorted(by_app)],
        'coverage': coverage_rows,
        'not_traced': not_traced,
        'not_traced_detail': [{'class_name': c,
                               'reading': 'never armed as a TraceTarget — NOT TRACED, which is not the same as '
                                          'nothing flowing'} for c in not_traced],
        'counts': {'declared': len(decls), 'observed': len(obs), 'undeclared': len(undeclared),
                   'unexercised': len(unexercised), 'classes': len(all_classes), 'not_traced': len(not_traced)},
        'reading': ('%d declared flow(s), %d observed; %d observed flow(s) nothing declares (a finding, never a '
                    'block) and %d declaration(s) nothing has exercised. %s'
                    % (len(decls), len(obs), len(undeclared), len(unexercised),
                       ('%d of the %d class(es) here have NEVER been traced (%s) — for those the answer is NOT '
                        'TRACED, not "nothing flows"' % (len(not_traced), len(all_classes), ', '.join(not_traced)))
                       if not_traced else
                       ('every class here has been traced' if all_classes else
                        'no class has crossed a boundary yet, and none is declared'))),
        'how': HOW_DRIFT,
    }


def _app_of(class_name):
    try:
        from security.custom.security_observe import app_of_class
        return app_of_class(class_name) or ''
    except Exception:                       # noqa: BLE001
        return ''


# ---- simulate + compare -----------------------------------------------------------------------------------

def simulate(manager, scenario, actor, mode='today'):
    """Everything ONE actor can send out of this instance, and where (design §7's `simulate`).

    `actor` is a node on the view — `this instance`, a `class:<C>` — or, the reading design §7 actually asks for,
    `profile:<name>`: what can leave from a PERSON holding that `AppPermissionProfile`. A profile is expanded to
    its explicit classes, so the answer is the union of those classes' flows, and the reading says how many of
    them have never been traced (because for those the map cannot answer at all)."""
    g = build(manager, scenario, mode)
    # the actors are the view's NODES, not only the sources of edges: `this instance` with nothing flowing yet is
    # a real answer ("nothing leaves") and must not read as "no such actor".
    actors = sorted({n['node'] for n in g['nodes'] if n['kind'] in ('instance', 'class')})
    wanted, note = {str(actor or '')}, ''
    if str(actor or '') == INSTANCE_NODE:
        # the instance is the ORIGIN of every flow on this view, class-carrying or not — "what can leave this
        # instance and to where" (design §7) is all of it, not only the calls with no class attached.
        wanted = {e['source'] for e in g['edges']} | {INSTANCE_NODE}
        note = 'everything that leaves this instance, whichever class it belongs to'
    elif str(actor or '').startswith('profile:'):
        name = str(actor).split(':', 1)[1]
        try:
            from security.custom.security_closure import profile_start
            start = profile_start(manager, name)
        except Exception as exc:            # noqa: BLE001
            start = {'ok': False, 'refusal': '%s: %s' % (type(exc).__name__, exc)}
        if not start.get('ok'):
            return {'ok': False, 'view': VIEW, 'scenario': scenario, 'mode': mode, 'actor': actor,
                    'error': start.get('refusal', ''), 'actors': actors}
        wanted = {'class:%s' % c for c in start['classes']}
        note = ('the profile %r grants %d class(es); this is what those classes are known to send'
                % (name, len(start['classes'])))
    elif str(actor or '') not in actors:
        return {'ok': False, 'view': VIEW, 'scenario': scenario, 'mode': mode, 'actor': actor,
                'error': 'no such actor in this view; one of %s, or profile:<AppPermissionProfile name>' % actors,
                'actors': actors}
    steps = [{'target': e['target'], 'means': e['means'], 'payload': e['payload'], 'verdict': e['verdict'],
              'decided_by': e['decided_by'], 'provenance': e['flow_provenance'], 'traced': e['traced'],
              'chain': ' → '.join('%s:%s' % (s['system'], s['decision']) for s in e['chain']
                                  if s['decision'] != 'n/a'),
              'why': e['why']}
             for e in g['edges'] if e['source'] in wanted]
    reach = {v: sorted({s['target'] for s in steps if s['verdict'] == v})
             for v in ('allowed', 'logged', 'blocked')}
    untraced = sorted({s['payload'].split('×')[0] for s in steps if not s['traced'] and s['payload']})
    return {'ok': True, 'view': VIEW, 'scenario': scenario, 'mode': mode, 'actor': actor, 'actors': actors,
            'reach': reach, 'steps': steps, 'note': note,
            'not_traced': untraced,
            'reading': ('%s under mode %s: %d flow(s) allowed, %d logged (would be refused under enforce), '
                        '%d blocked%s%s'
                        % (actor, mode, len(reach['allowed']), len(reach['logged']), len(reach['blocked']),
                           ('. %s' % note) if note else '',
                           ('. NOT TRACED: %s — the map cannot say what those classes really send'
                            % ', '.join(untraced)) if untraced else ''))}


def compare(manager, mode='today'):
    """The same flows across the four MODES — one row per (source, means, target), one column per mode.

    The columns are MODES and not scenarios (COMPARE_AXIS): the other three views compare machines, and this one
    compares postures, because an object flow is the instance's and does not change with the machine layout."""
    from security.custom.security_topology import MODES
    rows = {}
    for m in MODES:
        g = build(manager, '', m)
        for e in g['edges']:
            key = (e['source'], e['means'], e['target'], e['payload'])
            row = rows.setdefault(key, {'source': e['source'], 'means': e['means'], 'target': e['target'],
                                        'payload': e['payload'], 'provenance': e['flow_provenance']})
            row[m] = '%s (%s)' % (e['verdict'], e['decided_by'] or '—')
    for row in rows.values():
        for m in MODES:
            row.setdefault(m, '—')
    return {'view': VIEW, 'mode': mode, 'axis': COMPARE_AXIS, 'modes': list(MODES),
            'scenarios': list(MODES), 'rows': [rows[k] for k in sorted(rows)],
            'how': ('the columns are the four MODES, not the scenarios: what may leave this instance is decided '
                    'by its traffic policies and its manifests, not by which machine it runs on. `stock` is what '
                    'an instance with no policy at all does; `enforce` is production, closed by default.')}


HOW_OBJECTS = ('the fourth security view (design §7). DECLARED edges come from the modules\' manifest `app.flows` '
               'stanzas (ct-7) and the traffic policy rows a person CONFIRMED (ct-9); OBSERVED edges come from '
               'the causal map, which records only while a TraceTarget is armed — one class at a time, dev '
               'posture only. Every edge carries its PAYLOAD (the classes, with counts) and never an instance id: '
               'an instance is looked up in the effect journal, not here. `drift` is declared − observed and '
               'observed − declared; an undeclared flow is a FINDING and dev warns, never blocks. An inbound '
               'browser ORIGIN is rendered coarsened (this-instance / other): the exact one is a person\'s to '
               'rule on at GET /api/security/traffic, not a topology read\'s to print.')

HOW_DRIFT = ('an observed flow nothing declares is a finding for the app author (add the `app.flows` stanza) or '
             'for the deployment (confirm the traffic policy row); a declaration nothing has exercised is noise '
             'to prune — UNLESS its classes have never been traced, in which case the honest reading is NOT '
             'TRACED and the next step is to arm one of them and ask again.')
