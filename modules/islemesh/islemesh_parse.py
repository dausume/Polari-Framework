"""
@cross-cutting
@module islemesh.islemesh_parse

Stdlib-pure parsers: isle-mesh's native artifacts → row dicts.

Two inputs, both OWNED BY ISLE (we parse, never write):
  - registry.json — the agent's durable desired-state
    (/etc/isle-mesh/agent/registry.json): apps, domains,
    subdomains, services, modes, availability_mode.
  - agent nginx config fragments (configs/<app>.conf) — the
    generated per-app vhosts. THE PROXIES ARE THE POLICY: what
    protocols are permitted between nodes is derived from these,
    never documented separately (handoff §11 protocol matrix).

NO framework imports — selftests run stdlib-only (the
topology_constants discipline). The API layer turns these dicts
into treeObject rows; `pol isle sync` posts the raw artifacts.

@consumers
  - islemesh.islemesh_api (ingest endpoints)
  - islemesh.selftest_islemesh
"""

import re


def parse_registry(registry, device_name, is_mock=False):
    """isle registry.json (parsed dict) → {'apps': [...],
    'services': [...]} row dicts for the given device.

    Tolerant by design: isle's schema has drifted before (modes as
    list, availability_mode arriving with feat/availability-modes)
    — absent fields default, never raise."""
    apps, services = [], []
    for app_name, entry in (registry.get('apps') or {}).items():
        if not isinstance(entry, dict):
            continue
        modes = entry.get('modes') or []
        if not isinstance(modes, list):
            modes = [str(modes)]
        apps.append({
            'name': app_name,
            'domain': entry.get('domain', ''),
            'device_name': device_name,
            'modes': sorted(str(m) for m in modes),
            'availability_mode': entry.get(
                'availability_mode', 'always-available'),
            'updated_at': entry.get('updated_at', ''),
            'status': entry.get('status', ''),
            'is_mock': bool(is_mock),
        })
        for svc in (entry.get('services') or []):
            if not isinstance(svc, dict):
                continue
            svc_name = svc.get('name', '')
            services.append({
                'name': '%s/%s' % (app_name, svc_name),
                'app_name': app_name,
                'service': svc_name,
                'subdomain': svc.get('subdomain', ''),
                'container': svc.get('container', ''),
                'port': int(svc.get('port') or 0),
                'protocol': svc.get('protocol', 'http'),
                'is_mock': bool(is_mock),
            })
    return {'apps': apps, 'services': services}


#: One nginx `server { ... }` block (fragments are generated flat —
#: no nested blocks besides location{}, which the . catches).
_SERVER_RE = re.compile(r'server\s*\{', re.MULTILINE)
_LISTEN_RE = re.compile(r'\blisten\s+(?:[\d.]+:)?(\d+)([^;]*);')
_NAME_RE = re.compile(r'\bserver_name\s+([^;]+);')
_PASS_RE = re.compile(r'\bproxy_pass\s+([^;]+);')
_MTLS_RE = re.compile(r'\bssl_verify_client\s+(on|optional)')
_UPSTREAM_RE = re.compile(
    r'upstream\s+(\S+)\s*\{([^}]*)\}', re.MULTILINE)
_MEMBER_RE = re.compile(r'\bserver\s+([^;\s]+)')


def _server_blocks(text):
    """Yield the text of each server{} block (brace-balanced)."""
    for match in _SERVER_RE.finditer(text):
        depth, start = 0, match.end() - 1
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    yield text[start:i + 1]
                    break


def parse_fragment(text, device_name, app_name='',
                   fragment_ref='', is_mock=False):
    """One agent nginx fragment → IsleProtocolPermit row dicts.

    Each server{} block = one permit per server_name: what may be
    spoken (http / https / https-mtls), on which port, to which
    upstream. Redirect-only blocks (return 301, no proxy_pass)
    still answer the port — they are permits too (http reach)."""
    upstreams = {}
    for m in _UPSTREAM_RE.finditer(text):
        members = _MEMBER_RE.findall(m.group(2))
        upstreams[m.group(1)] = ','.join(members)
    permits = []
    for block in _server_blocks(text):
        listen = _LISTEN_RE.search(block)
        names = _NAME_RE.search(block)
        if not listen or not names:
            continue
        port = int(listen.group(1))
        ssl = 'ssl' in listen.group(2)
        protocol = 'https' if ssl else 'http'
        if ssl and _MTLS_RE.search(block):
            protocol = 'https-mtls'
        targets = []
        for passed in _PASS_RE.findall(block):
            passed = passed.strip()
            # resolve 'http(s)://<upstream-name>' to its members
            bare = re.sub(r'^https?://', '', passed).split('/')[0]
            targets.append(upstreams.get(bare, passed))
        upstream = ','.join(dict.fromkeys(targets))  # ordered dedup
        for server_name in names.group(1).split():
            permits.append({
                'name': '%s/%s:%d' % (device_name, server_name,
                                      port),
                'device_name': device_name,
                'app_name': app_name,
                'server_name': server_name,
                'listen_port': port,
                'protocol': protocol,
                'upstream': upstream,
                'fragment_ref': fragment_ref,
                'is_mock': bool(is_mock),
            })
    return permits


def parse_fragments(fragments, device_name, is_mock=False):
    """{'<app>.conf': '<nginx text>', ...} → permit row dicts.
    App attribution = the fragment filename stem (isle's own
    convention: configs/<app>.conf)."""
    permits = []
    for ref, text in sorted((fragments or {}).items()):
        app = ref[:-5] if ref.endswith('.conf') else ref
        permits.extend(parse_fragment(
            text or '', device_name, app_name=app,
            fragment_ref=ref, is_mock=is_mock))
    return permits
