"""
Selftest for the Polari App Store (appstore-1).

Run from polari-framework/:  python3 -m appstore.selftest_appstore

Stdlib-only (SimpleNamespace rows, fake Falcon req/resp). Covers the
token lifecycle (hash-at-rest, single-use, expiry, revoke authz),
the registration document + deep-link contracts, catalog coherence
with polariapps, deterministic archive overlay, honest MinIO-absent
refusals, and the topology reachability vocabulary (mesh refused as
named-but-unavailable).
"""

import hashlib
import io
import json
import os
import tarfile
import tempfile
import types

from appstore.appstore_api import AppStoreAPI
from appstore.appstore_basis import (
    AppShellDefinition, ShellEnrollment,
)
from appstore.appstore_payloads import (
    deep_link, identity_payload, registration_document,
)
from appstore.appstore_seed import SEED_APP_SHELLS
from appstore.appstore_tokens import (
    expiry_iso, hash_secret, judge, mint, split_wire,
)
from appstore.shell_project import overlay_tar_gz

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _ns(**fields):
    return types.SimpleNamespace(**fields)


class _Resp:
    def __init__(self):
        self.status = '200 OK'
        self.media = None
        self.content_type = ''
        self.data = b''
        self.downloadable_as = ''
        self.headers = {}

    def set_header(self, key, value):
        self.headers[key] = value


def _req(body=None, params=None, user=None, roles=None):
    raw = json.dumps(body).encode('utf-8') if body is not None \
        else b''
    return _ns(params=params or {},
               bounded_stream=io.BytesIO(raw),
               remote_addr='127.0.0.1',
               context=_ns(user_info=user, roles=roles or []))


class _FakeDB:
    def saveInstanceInDB(self, row):
        pass


def _mgr():
    shells = {}
    for seed in SEED_APP_SHELLS:
        row = AppShellDefinition(**seed)
        shells[row.name] = row
    return _ns(objectTables={
        'AppShellDefinition': shells,
        'ShellEnrollment': {},
        'ShellInstallation': {},
        'ShellArtifact': {},
        'PolariAppDefinition': {
            'wax-print-shop': _ns(name='wax-print-shop',
                                  title='Wax Print Shop'),
            'app-magnetics': _ns(name='app-magnetics',
                                 title='Magnetics'),
        },
        'InstanceDefinition': {
            'prf-a': _ns(name='prf-a', kind='prf',
                         accessibility_scope='local',
                         network_kind='home',
                         network_display_name='Etts home network',
                         network_hint_json=json.dumps(
                             {'expectedCidrs': ['192.168.0.0/24']}),
                         public_base_url='https://prf.test',
                         api_base_url='https://api.prf.test',
                         topology_name='staging-a'),
        },
    }, db=_FakeDB(), objectStore=None, idList=[])


def _api(mgr):
    api = AppStoreAPI(polServer=None, manager=mgr)
    api.manager = mgr
    return api


USER = {'sub': 'sub-dustin', 'preferred_username': 'dustin'}


if __name__ == '__main__':
    os.environ['POLARI_INSTANCE_NAME'] = 'prf-a'
    os.environ['POLARI_INSTANCE_ID'] = 'a'
    os.environ['POLARI_KEYCLOAK_REALM'] = 'Polari'
    os.environ['POLARI_KEYCLOAK_ISSUER_URI'] = \
        'https://auth.test/realms/Polari'
    ca_pem = ('-----BEGIN CERTIFICATE-----\nselftest-ca\n'
              '-----END CERTIFICATE-----\n')
    ca_file = tempfile.NamedTemporaryFile(
        'w', suffix='.crt', delete=False)
    ca_file.write(ca_pem)
    ca_file.close()
    os.environ['POLARI_SHELL_CA_PATH'] = ca_file.name

    print('== suite: tokens ==')
    token = mint()
    check('wire token is <enr-id>.<secret> and splits back',
          split_wire(token['wire']) == (token['name'],
                                        token['secret'])
          and token['name'].startswith('enr-'))
    check('hash at rest is sha256(secret), never the secret',
          token['tokenHash'] == hash_secret(token['secret'])
          and token['secret'] not in token['tokenHash'])
    check('judge accepts the right secret while active',
          judge('active', token['tokenHash'],
                expiry_iso(900), token['secret'])['ok'])
    check('judge refuses a wrong secret as unknown token',
          judge('active', token['tokenHash'], expiry_iso(900),
                'not-the-secret')['error'] == 'unknown token')
    check('expired token refused by expiry timestamp',
          judge('active', token['tokenHash'],
                '2020-01-01T00:00:00+00:00',
                token['secret'])['error'] == 'token expired')
    check('revoked status refused',
          judge('revoked', token['tokenHash'], expiry_iso(900),
                token['secret'])['error'] == 'token revoked')

    print('== suite: enroll/redeem (single-use) ==')
    mgr = _mgr()
    api = _api(mgr)
    resp = _Resp()
    api.on_post_enroll(_req(body={}, user=None), resp,
                       'polari-instance-shell')
    check('enroll without a bearer token is 401',
          resp.status.startswith('401'))
    resp = _Resp()
    api.on_post_enroll(_req(body={'deviceLabel': 'test-laptop'},
                            user=USER), resp,
                       'polari-instance-shell')
    minted = resp.media
    check('mint returns the wire token exactly once',
          minted['ok'] and '.' in minted['token'])
    row = list(mgr.objectTables['ShellEnrollment'].values())[0]
    secret = minted['token'].partition('.')[2]
    leaked = [a for a in vars(row)
              if isinstance(getattr(row, a), str)
              and secret in getattr(row, a)]
    check('no row attribute contains the secret (hash at rest)',
          not leaked, f'leaked via {leaked}')
    check('mint response carries deep link + registration',
          minted['deepLink'].startswith('polari://register?')
          and minted['registration']['kind']
          == 'polari-shell-registration')
    resp = _Resp()
    api.on_post_redeem(
        _req(body={'token': minted['token'],
                   'platform': 'desktop-linux-x64',
                   'deviceLabel': 'test-laptop'}), resp)
    check('redeem returns the registration document',
          resp.media.get('ok')
          and resp.media['kind'] == 'polari-shell-registration'
          and resp.media.get('installation', '').startswith('inst-'))
    check('redeem flipped the row before responding',
          row.status == 'redeemed' and row.redeemed_at)
    resp2 = _Resp()
    api.on_post_redeem(_req(body={'token': minted['token']}), resp2)
    check('SECOND redeem of the same token refused',
          resp2.status.startswith('403')
          and resp2.media['error'] == 'token already redeemed')
    check('one ShellInstallation receipt written',
          len(mgr.objectTables['ShellInstallation']) == 1)

    print('== suite: revoke authz ==')
    resp = _Resp()
    api.on_post_enroll(_req(body={}, user=USER), resp,
                       'polari-instance-shell')
    tok2_id = resp.media['tokenId']
    resp = _Resp()
    api.on_post_enrollments(
        _req(body={'action': 'revoke', 'name': tok2_id},
             user={'sub': 'sub-other'}), resp)
    check('revoke by a non-minter without admin refused',
          resp.status.startswith('403'))
    resp = _Resp()
    api.on_post_enrollments(
        _req(body={'action': 'revoke', 'name': tok2_id},
             user={'sub': 'sub-other'}, roles=['admin']), resp)
    check('revoke by admin succeeds',
          resp.media.get('ok')
          and mgr.objectTables['ShellEnrollment'][
              [k for k, v in
               mgr.objectTables['ShellEnrollment'].items()
               if v.name == tok2_id][0]].status == 'revoked')
    resp = _Resp()
    api.on_get_enrollments(_req(user={'sub': 'sub-other'}), resp)
    check('enrollments list scopes to own rows, no hashes',
          resp.media['scope'] == 'own'
          and resp.media['enrollments'] == [])

    print('== suite: registration document (S1) ==')
    shell = mgr.objectTables['AppShellDefinition'][
        'polari-instance-shell']
    doc = registration_document(mgr, shell, username='dustin')
    inst = doc['instances'][0]
    check('doc: kind/schemaVersion/instances shape',
          doc['kind'] == 'polari-shell-registration'
          and doc['schemaVersion'] == 1 and len(doc['instances']) == 1)
    check('doc: auth block is polari-shell + PKCE S256 + loginHint',
          inst['auth']['clientId'] == 'polari-shell'
          and inst['auth']['pkce'] == 'S256'
          and inst['auth']['loginHint'] == 'dustin'
          and 'offline_access' in inst['auth']['scope'])
    check('doc: reachability block travels (scope/kind/name/hint)',
          inst['reachability']['scope'] == 'local'
          and inst['reachability']['networkKind'] == 'home'
          and inst['reachability']['networkName']
          == 'Etts home network'
          and inst['reachability']['hint']['cidrs']
          == ['192.168.0.0/24']
          and inst['reachability']['hint']['probeUrl'].endswith(
              '/api/appstore/identity'))
    check('doc: CA pem + matching sha256 fingerprint',
          inst['tls']['caPem'] == [ca_pem]
          and inst['tls']['caSha256']
          == hashlib.sha256(ca_pem.encode()).hexdigest())
    check('doc: credential-free without an enrollment',
          doc['enrollment'] is None)
    check('sep-2: app block carries capabilities (list, from '
          'capabilities_json; absent field = [])',
          doc['app']['capabilities'] == [])
    caps_shell = type(shell)(
        name='caps-shell', title='Caps', scope='app',
        app_name='wax-print-shop',
        capabilities_json='["camera", "lora-radio"]')
    caps_doc = registration_document(mgr, caps_shell)
    check('sep-2: capabilities_json rides the wire as a list',
          caps_doc['app']['capabilities']
          == ['camera', 'lora-radio'])
    urls_gone = _mgr()
    urls_gone.objectTables['InstanceDefinition'] = {}
    saved_env = dict(os.environ)
    os.environ.pop('POLARI_PUBLIC_BASE_URL', None)
    refusal = registration_document(urls_gone, shell)
    check('doc refuses honestly when URLs undeclared, naming knob',
          not refusal.get('ok')
          and 'public_base_url' in refusal['suggestion']['knob'])
    os.environ.update(saved_env)

    print('== suite: identity + deep link ==')
    ident = identity_payload(mgr)
    check('identity: unauthenticated probe shape',
          ident['ok'] and ident['instanceName'] == 'prf-a'
          and ident['instanceId'] == 'a'
          and ident['reachability']['scope'] == 'local'
          and ident['serverTime'])
    link = deep_link(mgr, 'enr-abc.secret')['deepLink']
    check('deep link carries api/t/ca/scope/nk/nn',
          all(part in link for part in
              ('polari://register?', 'api=', 't=enr-abc.secret',
               'ca=', 'scope=local', 'nk=home', 'nn=Etts')))

    print('== suite: catalog ==')
    resp = _Resp()
    api.on_get_catalog(_req(), resp)
    cat = resp.media
    check('catalog lists published shells + derives per-app rows',
          {s['name'] for s in cat['shells']}
          == {'polari-instance-shell', 'wax-print-shop-shell'}
          and {a['name'] for a in cat['apps']}
          == {'wax-print-shop', 'app-magnetics'})
    check('un-shelled app still installable via instance shell, '
          'with the publish affordance named',
          all(a['installable'] for a in cat['apps'])
          and any('POST /api/appstore/definition' in a['how']
                  for a in cat['apps']
                  if a['name'] == 'app-magnetics'))
    resp = _Resp()
    api.on_post_definition(
        _req(body={'name': 'ghost-shell', 'scope': 'app',
                   'app_name': 'no-such-app'}, user=USER), resp)
    check('scope=app with unknown app refused, naming /api/apps',
          resp.status.startswith('400')
          and '/api/apps' in resp.media['error'])

    print('== suite: overlay determinism ==')
    src = io.BytesIO()
    with tarfile.open(fileobj=src, mode='w:gz') as tar:
        for name, text in (('polari-app-shell/gradlew', '#!/bin/sh\n'),
                           ('polari-app-shell/settings.gradle.kts',
                            'rootProject.name = "polari-app-shell"\n')):
            data = text.encode()
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mtime = 1754400000  # wall-clock mtime on purpose
            tar.addfile(info, io.BytesIO(data))
    extras = {'config/polari-shell.json': '{"schemaVersion": 1}',
              'README.md': '# shell\n'}
    one = overlay_tar_gz(src.getvalue(), extras)
    two = overlay_tar_gz(src.getvalue(), extras)
    check('overlay is byte-deterministic across runs',
          one['ok']
          and hashlib.sha256(one['data']).hexdigest()
          == hashlib.sha256(two['data']).hexdigest())
    out = tarfile.open(fileobj=io.BytesIO(one['data']), mode='r:gz')
    names = out.getnames()
    cfg = out.extractfile(
        'polari-app-shell/config/polari-shell.json').read()
    out.close()
    check('overlay placed config under the archive root',
          'polari-app-shell/config/polari-shell.json' in names
          and cfg == b'{"schemaVersion": 1}'
          and 'polari-app-shell/gradlew' in names)

    print('== suite: MinIO-absent honesty ==')
    resp = _Resp()
    api.on_get_download(
        _req(params={'platform': 'gradle-project'}), resp,
        'polari-instance-shell')
    check('gradle-project download without an archive refuses, '
          'naming the upload flow',
          not resp.media.get('ok')
          and 'srcDistTar' in json.dumps(resp.media))
    resp = _Resp()
    api.on_post_artifacts(
        _req(body={'action': 'presign-put',
                   'shellName': 'polari-instance-shell',
                   'platform': 'gradle-project', 'version': '0.1.0'},
             user=USER, roles=['admin']), resp)
    check('presign-put with no object store refuses with the knob',
          not resp.media.get('ok')
          and resp.media['suggestion']['knob'].startswith('MINIO'))
    resp = _Resp()
    api.on_post_artifacts(_req(body={'action': 'presign-put'},
                               user=USER), resp)
    check('artifacts endpoint requires the admin role',
          resp.status.startswith('403'))

    print('== suite: topology reachability vocabulary ==')
    from topology.topology_analysis import validate_topology
    topo_mgr = _ns(objectTables={
        'TopologyDefinition': {
            't': _ns(name='staging-a', default_target='compose')},
        'PolariNodeMachine': {},
        'OrchestrationTarget': {},
        'InstanceDefinition': {
            'prf-a': _ns(name='prf-a', kind='prf',
                         topology_name='staging-a',
                         machine_name='', env_tier='staging',
                         orchestration_target='compose',
                         db_backend='sqlite', cache_backend='',
                         blob_backend='', service_kinds_json='[]',
                         replicas=1,
                         accessibility_scope='mesh',
                         network_kind='campus'),
        },
        'ServiceConnectionDefinition': {},
        'ModuleAssignment': {},
    })
    report = validate_topology(topo_mgr, 'staging-a')
    kinds = {f.get('kind', f.get('check', '')) for f in
             report.get('findings', [])}
    flat = json.dumps(report)
    check('validate refuses mesh as named-but-unavailable',
          'scope-unavailable' in flat)
    check('validate refuses an unknown network_kind',
          'unknown-network-kind' in flat)
    topo_mgr.objectTables['InstanceDefinition']['prf-a'] \
        .accessibility_scope = 'web'
    topo_mgr.objectTables['InstanceDefinition']['prf-a'] \
        .network_kind = ''
    flat2 = json.dumps(validate_topology(topo_mgr, 'staging-a'))
    check("web + empty network_kind is legal",
          'scope-unavailable' not in flat2
          and 'unknown-network-kind' not in flat2)

    os.unlink(ca_file.name)
    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    print(f'{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
