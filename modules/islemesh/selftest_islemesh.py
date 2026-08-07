"""
Selftest for the islemesh module (mac-1).

Run from polari-framework/:
    python3 -m islemesh.selftest_islemesh        (container root)
    PYTHONPATH=modules python3 -m islemesh.selftest_islemesh (host)

Stdlib-only: parsers + mock payloads + vocabulary coherence — no
DB, no falcon, no treeObject machinery. Covers: registry parsing
(isle's registry.sample.json shape incl. modes drift + absent
fields), fragment parsing (https/mtls/redirect blocks, upstream
resolution, brace balance), the mock feed's flag discipline (every
payload declares mock_network — the thing real data never does),
and that the mock exercises the REAL parse pipeline.
"""

import json

from islemesh.islemesh_constants import (
    AVAILABILITY_MODES, CONNECTIVITY_MODES, DOWN_TRIGGERS,
    INGEST_KINDS, MOCK_BANNER, PACKAGE_KINDS, PERMIT_PROTOCOLS,
    PLACEMENTS, REALIZATION_KINDS, UP_TRIGGERS, UPLINK_KINDS,
)
from islemesh.islemesh_mock import mock_ingests, mock_realizations
from islemesh.islemesh_parse import (
    parse_fragment, parse_fragments, parse_registry,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


# ---- fixtures (isle's own registry.sample.json shape) ---------------

SAMPLE_REGISTRY = {
    'domains': {'myapp.local': 'myapp'},
    'subdomains': {'api.myapp.local': 'myapp'},
    'apps': {
        'health': {'domain': 'health.local', 'services': [],
                   'modes': [], 'updated_at': ''},
        'myapp': {
            'domain': 'myapp.local',
            'services': [
                {'name': 'api', 'subdomain': 'api',
                 'container': 'myapp-api-1', 'port': 3000,
                 'protocol': 'http'},
                {'name': 'web', 'subdomain': 'web',
                 'container': 'myapp-web-1', 'port': 8080,
                 'protocol': 'http'},
            ],
            'modes': ['local'],
            'updated_at': '2025-12-19T10:30:45.123456',
        },
        'webapp': {
            'domain': 'webapp.local',
            'availability_mode': 'on-demand',
            'services': [
                {'name': 'frontend', 'subdomain': 'frontend',
                 'container': 'webapp-frontend-1', 'port': 3000,
                 'protocol': 'http'}],
            'modes': ['isle'],
            'updated_at': '2025-12-19T11:15:22.789012',
        },
    },
}

FRAGMENT = """
upstream myapp_backend {
    server backend:8443;
    server backend2:8443;
}
server {
    listen 80;
    server_name myapp.local api.myapp.local;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl http2;
    server_name myapp.local;
    ssl_certificate /etc/nginx/ssl/certs/myapp.local.crt;
    location / {
        proxy_pass https://myapp_backend;
    }
}
server {
    listen 443 ssl http2;
    server_name api.myapp.local;
    ssl_verify_client on;
    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
"""


def main():
    # ---- registry parsing -------------------------------------------
    parsed = parse_registry(SAMPLE_REGISTRY, 'isle-core')
    apps = {a['name']: a for a in parsed['apps']}
    check('all apps parsed (incl. empty health)', len(apps) == 3)
    check('domain carried', apps['myapp']['domain'] == 'myapp.local')
    check('device attributed',
          apps['myapp']['device_name'] == 'isle-core')
    check('absent availability_mode defaults always-available',
          apps['myapp']['availability_mode'] == 'always-available')
    check('present availability_mode kept',
          apps['webapp']['availability_mode'] == 'on-demand')
    check('modes sorted list', apps['webapp']['modes'] == ['isle'])
    services = {s['name']: s for s in parsed['services']}
    check('services keyed app/service',
          'myapp/api' in services and 'myapp/web' in services)
    check('service fields carried',
          services['myapp/api']['container'] == 'myapp-api-1'
          and services['myapp/api']['port'] == 3000)
    check('services carry the device (replace semantics reach '
          'them)', all(s['device_name'] == 'isle-core'
                       for s in parsed['services']))
    check('real data is never mock',
          not apps['myapp']['is_mock']
          and not services['myapp/api']['is_mock'])
    # tolerance: modes as scalar, junk service entries
    drifted = parse_registry(
        {'apps': {'odd': {'modes': 'local',
                          'services': [None, 'junk']}}}, 'dev')
    check('schema drift tolerated (scalar modes, junk services)',
          drifted['apps'][0]['modes'] == ['local']
          and drifted['services'] == [])

    # ---- fragment parsing -------------------------------------------
    permits = parse_fragment(FRAGMENT, 'isle-core',
                             app_name='myapp',
                             fragment_ref='myapp.conf')
    by_key = {(p['server_name'], p['listen_port']): p
              for p in permits}
    check('four permits (2 names x port 80, 2 on 443)',
          len(permits) == 4, str(sorted(by_key)))
    check('redirect block is an http permit',
          by_key[('myapp.local', 80)]['protocol'] == 'http')
    check('ssl listen is https',
          by_key[('myapp.local', 443)]['protocol'] == 'https')
    check('ssl_verify_client makes https-mtls',
          by_key[('api.myapp.local', 443)]['protocol']
          == 'https-mtls')
    check('upstream resolved to members',
          by_key[('myapp.local', 443)]['upstream']
          == 'backend:8443,backend2:8443')
    check('direct proxy_pass kept verbatim',
          by_key[('api.myapp.local', 443)]['upstream']
          == 'http://127.0.0.1:3000')
    check('permit protocols all in vocabulary',
          all(p['protocol'] in PERMIT_PROTOCOLS for p in permits))
    check('fragment provenance carried',
          all(p['fragment_ref'] == 'myapp.conf' for p in permits))
    named = parse_fragments({'other.conf': FRAGMENT}, 'dev')
    check('filename stem attributes the app',
          named and all(p['app_name'] == 'other' for p in named))
    check('empty/garbage fragment yields no permits',
          parse_fragment('', 'dev') == []
          and parse_fragment('server { broken', 'dev') == [])

    # ---- the mock feed ----------------------------------------------
    ingests = mock_ingests()
    check('mock covers every ingest kind',
          {kind for kind, _ in ingests} == set(INGEST_KINDS))
    check('EVERY mock payload declares mock_network '
          '(the flag real data never carries)',
          all(payload.get('mock_network') is True
              for _, payload in ingests))
    check('mock payloads are json-serializable',
          bool(json.dumps([p for _, p in ingests])))
    for kind, payload in ingests:
        if kind == 'registry':
            rows = parse_registry(payload['registry'],
                                  payload['device'], is_mock=True)
            check('mock registry parses through the real parser',
                  len(rows['apps']) == 3
                  and all(a['is_mock'] for a in rows['apps']))
        if kind == 'fragments':
            rows = parse_fragments(payload['fragments'],
                                   payload['device'], is_mock=True)
            check('mock fragments (%s) parse through the real '
                  'parser' % payload['device'],
                  len(rows) >= 1
                  and all(p['is_mock'] for p in rows))
            if payload['device'] == 'isle-core':
                protos = {p['protocol'] for p in rows}
                check('mock matrix shows all three protocol '
                      'classes', protos == set(PERMIT_PROTOCOLS),
                      str(protos))
        if kind == 'device':
            uplinks = payload.get('uplinks') or []
            check('mock uplink kinds valid (%s)'
                  % payload['device'],
                  all(u['kind'] in UPLINK_KINDS for u in uplinks))
            mode = payload['facts'].get('connectivity_mode')
            check('mock connectivity mode valid (%s)'
                  % payload['device'], mode in CONNECTIVITY_MODES)
    realizations = mock_realizations()
    check('mock realizations all flagged + kinds valid',
          all(r['is_mock'] and r['kind'] in REALIZATION_KINDS
              for r in realizations))
    check('mock includes the kvm hardware-pin example',
          any(r['kind'] == 'kvm' and r['hardware_pin_device']
              for r in realizations))
    check('mock package kinds valid',
          all(r.get('package_kind', '') in PACKAGE_KINDS
              for r in realizations))

    # ---- vocabulary coherence ---------------------------------------
    check('availability presets are named modes over the triple',
          AVAILABILITY_MODES == ('always-available', 'on-demand')
          and 'resource-permitting' in UP_TRIGGERS
          and 'resource-pressure' in DOWN_TRIGGERS
          and 'replicated' in PLACEMENTS)
    check('mock banner is loud and self-describing',
          'MOCK NETWORK' in MOCK_BANNER)

    failed = sum(1 for _, ok in _results if not ok)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
