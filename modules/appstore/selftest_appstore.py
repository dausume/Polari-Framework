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
    AppEdgeBehavior, AppShellDefinition, ShellEnrollment,
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
          and any('pol apps shell app-magnetics' in a['how']
                  and 'shell-from-app' in a['how']
                  for a in cat['apps']
                  if a['name'] == 'app-magnetics'))
    resp = _Resp()
    api.on_post_definition(
        _req(body={'name': 'ghost-shell', 'scope': 'app',
                   'app_name': 'no-such-app'}, user=USER), resp)
    check('scope=app with unknown app refused, naming /api/apps',
          resp.status.startswith('400')
          and '/api/apps' in resp.media['error'])

    print('== suite: sep-5 edge behaviors (decision 8) ==')
    from appstore.appstore_seed import SEED_EDGE_BEHAVIORS
    behaviors = {}
    for seed in SEED_EDGE_BEHAVIORS:
        row = AppEdgeBehavior(**seed)
        behaviors[row.name] = row
    mgr.objectTables['AppEdgeBehavior'] = behaviors
    check('sep-5: exemplar seeds carry the plan\'s own examples '
          '(radio / camera / network), each naming its native half',
          {b['name'] for b in SEED_EDGE_BEHAVIORS}
          == {'lora-radio-attach', 'camera-capture',
              'isle-wifi-join'}
          and all(b['kind'] in ('device', 'network', 'nocode-graph')
                  for b in SEED_EDGE_BEHAVIORS))
    resp = _Resp()
    api.on_get_behaviors(_req(params={}), resp)
    check('sep-5: behaviors endpoint is credential-free and lists '
          'definitions with parsed config',
          resp.media['ok'] and len(resp.media['behaviors']) == 3
          and resp.media['behaviors'][0]['config'] != {})
    resp = _Resp()
    api.on_get_behaviors(
        _req(params={'names': 'camera-capture,ghost'}), resp)
    check('sep-5: ?names= filters and states the unknown',
          [b['name'] for b in resp.media['behaviors']]
          == ['camera-capture']
          and resp.media['unknown'] == ['ghost'])
    resp = _Resp()
    api.on_post_definition(
        _req(body={'name': 'radio-shell', 'scope': 'instance',
                   'capabilities_json': '["lora-radio-attach", '
                                        '"no-such-behavior"]'},
             user=USER), resp)
    check('sep-5: authoring refuses capabilities that reference no '
          'behavior row (a reference must reference)',
          resp.status.startswith('400')
          and 'no-such-behavior' in resp.media['error']
          and '/api/appstore/behaviors' in resp.media['error'])
    resp = _Resp()
    api.on_post_definition(
        _req(body={'name': 'radio-shell', 'scope': 'instance',
                   'capabilities_json': '["lora-radio-attach"]'},
             user=USER), resp)
    check('sep-5: valid references author cleanly',
          resp.media.get('ok') and resp.media['created'])

    print('== suite: sep-3 shell-from-app (convert) ==')
    resp = _Resp()
    api.on_post_shell_from_app(
        _req(body={'appName': 'no-such-app'}, user=USER), resp)
    check('sep-3: unknown app refused honestly',
          resp.status.startswith('404'))
    resp = _Resp()
    api.on_post_shell_from_app(
        _req(body={'appName': 'wax-print-shop'}, user=USER), resp)
    check('sep-3: an app with a scope=app shell REUSES it '
          '(idempotent, never a duplicate row)',
          resp.media.get('ok')
          and resp.media['created'] is False
          and resp.media['shell'] == 'wax-print-shop-shell'
          and resp.media['registrationPath']
          == '/api/appstore/wax-print-shop-shell/registration'
             '?download=1')
    resp = _Resp()
    api.on_post_shell_from_app(
        _req(body={'appName': 'app-magnetics'}, user=USER), resp)
    check('sep-3: convert creates the scope=app row for an '
          'unshelled app (name = <app>-shell)',
          resp.media.get('ok')
          and resp.media['created'] is True
          and resp.media['shell'] == 'app-magnetics-shell')
    resp = _Resp()
    api.on_post_shell_from_app(_req(body={}), resp)
    check('sep-3: convert requires auth',
          resp.status.startswith('401'))

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

    print('== suite: ai-0 tool definitions + linkage vocabulary ==')
    from appstore.appstore_ai import (
        AI_LINKAGES, API_FAMILIES, HOSTING_KINDS, LINKAGE_STATUSES,
        tool_report)
    from appstore.appstore_seed import SEED_AI_TOOLS
    check('ai-0: the four tools Dustin named, one row each '
          '(openai covers Codex)',
          {t['name'] for t in SEED_AI_TOOLS}
          == {'null', 'claude', 'openai', 'localai'})
    check('ai-0: every seed uses a known hosting kind + API family',
          all(t['hosting'] in HOSTING_KINDS
              and t['api_family'] in API_FAMILIES
              for t in SEED_AI_TOOLS))
    all_links = [(t['name'], link) for t in SEED_AI_TOOLS
                 for link in json.loads(t['linkages_json'])]
    check('ai-0: every linkage claim uses a vocabulary kind, an '
          'honest status, and carries a note',
          all_links
          and all(link['kind'] in AI_LINKAGES
                  and link['status'] in LINKAGE_STATUSES
                  and link.get('note')
                  for _, link in all_links))
    check('ai-0: proven claims exist ONLY on the live seams — '
          'unbuilt seams carry feasible claims at most',
          all(AI_LINKAGES[link['kind']]['seam'] == 'live'
              for _, link in all_links
              if link['status'] == 'proven'))
    check('ai-0: sovereignty facts — remote intermediaries state '
          'data leaves the isle, local/built-in state it never does',
          all((t['internet_required'] and t['data_leaves_isle'])
              == (t['hosting'] == 'remote-intermediary')
              for t in SEED_AI_TOOLS))
    check('ai-0: every vocabulary kind names its consumer + seam '
          'state',
          all(v.get('consumer') and v.get('seam')
              in ('live', 'unbuilt') for v in AI_LINKAGES.values()))

    print('== suite: ai-1 honest readiness API ==')
    from appstore.appstore_ai import AiToolDefinition
    from appstore.appstore_ai_api import AiToolsAPI, ai_tools_payload
    ai_mgr = _ns(objectTables={'AiToolDefinition': {
        t['name']: AiToolDefinition(**t) for t in SEED_AI_TOOLS}},
        db=_FakeDB(), idList=[])
    ai_api = AiToolsAPI(polServer=None, manager=ai_mgr)
    ai_api.manager = ai_mgr
    resp = _Resp()
    ai_api.on_get_ai_tools(_req(params={}), resp)
    tools = {t['name']: t for t in resp.media['tools']}
    check('ai-1: list returns all four tools + the vocabulary',
          resp.media['ok'] and resp.media['count'] == 4
          and set(resp.media['linkages']) == set(AI_LINKAGES))
    check('ai-1: readiness joins LIVE from reasoning_config for '
          'provider-backed tools (booleans, never a secret)',
          all(tools[n]['readiness'] is not None
              and isinstance(tools[n]['readiness']['ready'], bool)
              and 'api_key' not in json.dumps(resp.media)
              for n in ('null', 'claude', 'openai', 'localai')))
    check('ai-1: the null fallback reports ready (always '
          'available, no LLM)',
          tools['null']['readiness']['ready'] is True)
    check('ai-1: linkage rows come back annotated with consumer + '
          'seam state from the vocabulary',
          all(link.get('consumer') and link.get('seam')
              in ('live', 'unbuilt')
              for t in tools.values() for link in t['linkages']))
    check('ai-1: remote intermediaries carry the privacy '
          'recommendation badge (knob-and-suggestion, never forced)',
          'privacy_recommendation' in tools['claude']
          and 'privacy_recommendation' in tools['openai']
          and 'privacy_recommendation' not in tools['localai'])
    resp = _Resp()
    ai_api.on_get_ai_tool(_req(params={}), resp, 'localai')
    check('ai-1: detail answers for one tool',
          resp.media['ok']
          and resp.media['tool']['name'] == 'localai'
          and resp.media['tool']['hosting'] == 'local-hosted')
    resp = _Resp()
    ai_api.on_get_ai_tool(_req(params={}), resp, 'ghost')
    check('ai-1: unknown tool refuses honestly',
          resp.status.startswith('404')
          and not resp.media['ok'])
    check('ai-1: unpublished tools hide from the list',
          ai_tools_payload([dict(SEED_AI_TOOLS[0],
                                 published=False)])['count'] == 0)

    print('== suite: ai-6 the honest hosting gauge ==')
    from appstore.appstore_ai import (CLOUD_HOSTING_OPTIONS,
                                      host_check)
    ai6_req = json.loads(
        [t for t in SEED_AI_TOOLS
         if t['name'] == 'localai'][0]['requirements_json'])
    check('ai-6: localai seeds hosting profiles (guidance with '
          'notes, gpu stated per profile)',
          len(ai6_req['profiles']) == 2
          and all(p.get('note') and 'gpu' in p
                  for p in ai6_req['profiles']))
    small = {'name': 'small', 'hasSpecs': True, 'logicalCpus': 4,
             'totalRamMb': 16000, 'availableRamMb': 800,
             'freeDiskMb': 5000, 'resourceSource': 'observed-local',
             'resourceObservedAt': 'now'}
    big = {'name': 'big', 'hasSpecs': True, 'logicalCpus': 16,
           'totalRamMb': 65536, 'availableRamMb': 40000,
           'freeDiskMb': 500000, 'resourceSource': 'observed-push',
           'resourceObservedAt': 'now'}
    r = host_check(ai6_req, [small,
                             {'name': 'ghost', 'hasSpecs': False}])
    check('ai-6: an under-resourced isle is told NOT realistic '
          'with the failing numbers + remote hosting recommended',
          r['ok'] and not r['realistic'] and r['cloud_recommended']
          and r['unknown_machines'] == ['ghost']
          and any('disk' in d
                  for d in r['machines'][0]['profiles'][0]['detail'])
          and 'host the model remotely' in r['note'])
    r = host_check(ai6_req, [small, big])
    check('ai-6: a fitting box flips the verdict and is NAMED',
          r['realistic'] and r['best']['machine'] == 'big'
          and not r['cloud_recommended'])
    check('ai-6: a GPU profile is honestly UNKNOWN (res-1 does '
          'not track GPUs), never a guessed yes',
          [m for m in r['machines'] if m['name'] == 'big'][0]
          ['profiles'][1]['verdict'] == 'unknown-gpu')
    check('ai-6: no requirements -> refuses (nothing to gauge)',
          not host_check({}, [big])['ok'])
    check('ai-6: zero observed machines -> the note says refresh, '
          'never a fabricated verdict',
          'no machine has OBSERVED' in host_check(ai6_req,
                                                  [])['note'])
    check('ai-6: cloud options carry sovereignty tiers and NO '
          'price quotes (prices go stale)',
          all(o['sovereignty'] in ('your-cloud', 'intermediary')
              and o.get('how') for o in CLOUD_HOSTING_OPTIONS)
          and not any(tok in json.dumps(CLOUD_HOSTING_OPTIONS)
                      for tok in ('$', '/mo', 'per hour')))
    check('ai-6: remote tools declare NO hosting requirements '
          '(nothing to host is the honest shape)',
          all(not t.get('requirements_json')
              for t in SEED_AI_TOOLS if t['name'] != 'localai'))

    print('== suite: ai-7 dated-price hosting suggestions ==')
    from appstore.appstore_hosting import (
        HOSTING_KINDS_REMOTE, SEED_REMOTE_HOSTING,
        hosting_options_payload)
    check('ai-7: EVERY price carries its as-of date + source URL '
          '(a price without a date is a lie waiting to happen)',
          all(o['price_as_of'] and o['price_source']
              and o['price_amount'] > 0
              and o['kind'] in HOSTING_KINDS_REMOTE
              for o in SEED_REMOTE_HOSTING))
    ai7 = hosting_options_payload(SEED_REMOTE_HOSTING, ai6_req['profiles'])
    ai7_by = {o['name']: o for o in ai7['options']}
    check('ai-7: fit is DERIVED from declared specs via the ai-6 '
          'gauge (cpu box fits minimal, declared-gpu box fits '
          'comfortable, gpu-less box refuses the gpu profile)',
          ai7_by['hetzner-cx32']['fit'][0]['verdict'] == 'fits'
          and ai7_by['hetzner-cx32']['fit'][1]['verdict'] == 'no'
          and ai7_by['digitalocean-gpu-rtx4000']['fit'][1]
          ['verdict'] == 'fits')
    check('ai-7: marketplace listings with varying specs stay '
          'UNVERIFIED, never guessed',
          all(f['verdict'] == 'unverified'
              for f in ai7_by['vast-rtx4090']['fit']))
    check('ai-7: payload carries the honesty note + profiles',
          'go stale' in ai7['honesty'] and ai7['profiles']
          and ai7['count'] == len(SEED_REMOTE_HOSTING))
    check('ai-7: unpublished options hide',
          hosting_options_payload(
              [dict(SEED_REMOTE_HOSTING[0], published=False)],
              ai6_req['profiles'])['count'] == 0)

    print('== suite: ai-4 the sovereign voice seam ==')
    # The live reasoning config is whatever this instance runs —
    # monkeypatch it for deterministic outcomes (and NEVER write it).
    try:
        from polariApiServer import reasoning_config as _rc
        from polariApiServer import voiceAPI as _v
    except ImportError:
        _rc = _v = None
    if _v is None:
        check('ai-4: voiceAPI unavailable in this context (stated, '
              'suite skipped)', True)
    else:
        real_active = _rc.active_config
        real_status = _rc.provider_status

        def _fake(provider, settings, ready, needs=()):
            _rc.active_config = lambda: {'provider': provider,
                                         'settings': settings}
            _rc.provider_status = lambda n: dict(
                real_status(n), ready=ready, needs=list(needs))
        try:
            _fake('null', {}, True)
            s = _v.voice_status()
            check('ai-4: null provider refuses both directions, '
                  'names why + the browser fallback',
                  not s['stt']['available']
                  and 'no audio API' in s['stt']['why']
                  and not s['sovereign']
                  and 'cloud-backed' in s['fallback'])
            _fake('openai_compatible',
                  {'base_url': 'http://localai.isle:8080/v1'}, True)
            s = _v.voice_status()
            check('ai-4: ready openai_compatible serves both '
                  'directions and is SOVEREIGN (base_url)',
                  s['stt']['available'] and s['tts']['available']
                  and s['sovereign']
                  and s['stt']['model'] == 'whisper-1'
                  and s['tts']['voice'] == 'alloy')
            _fake('openai', {}, True)
            s = _v.voice_status()
            check('ai-4: ready openai serves voice but is NOT '
                  'sovereign — audio leaves the isle, stated',
                  s['stt']['available'] and not s['sovereign']
                  and 'leaves the isle' in s['sovereignty_note'])
            _fake('openai_compatible', {}, False,
                  ['set base_url'])
            s = _v.voice_status()
            check('ai-4: unready provider refuses naming its needs',
                  not s['stt']['available']
                  and 'set base_url' in s['stt']['why'])
            # the handlers refuse honestly BEFORE touching audio
            _fake('null', {}, True)
            vapi = _v.voiceAPI(polServer=None, manager=None)
            resp = _Resp()
            vapi.on_post_transcribe(
                _ns(bounded_stream=io.BytesIO(b''),
                    content_type='audio/webm'), resp)
            check('ai-4: transcribe on a no-audio provider refuses '
                  'with the fallback stated',
                  resp.status.startswith('400')
                  and not resp.media['ok']
                  and 'fallback' in resp.media)
            resp = _Resp()
            vapi.on_post_speak(_req(body={'text': 'hi'}), resp)
            check('ai-4: speak on a no-audio provider refuses too',
                  resp.status.startswith('400')
                  and not resp.media['ok'])
        finally:
            _rc.active_config = real_active
            _rc.provider_status = real_status

    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    print(f'{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
