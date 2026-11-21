"""
@module islemesh.islemesh_storage_doors_selftest

Controls for the stm-2b storage doors (docs/STORAGE-MIGRATION-CONTRACT.md 2.6, 5, 6, 9): placement view,
receipt and witness doors, the receipt-derived planned-action status, and agent_address on the devices door.
Isolated like the ingest concurrency selftest: fake manager + fake DB, real row classes and handlers, a
temporary PlanStore, no Falcon server, no network. Run from polari-framework/:

  PYTHONPATH=.:modules python3 -m islemesh.islemesh_storage_doors_selftest
"""
import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from islemesh.islemesh_api import IsleMeshAPI
from islemesh.custom import islemesh_storage_plan as sp
from islemesh.custom.islemesh_planning import PlanStore

_results = []
FIX = Path(__file__).parent / 'custom' / 'fixtures'
TOKEN = 'SECRET-TOKEN-VALUE'
FINGERPRINT = hashlib.sha256(TOKEN.encode()).hexdigest()


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra and not cond else ''))


class Sink:
    def __init__(self):
        self.status, self.media = '200 OK', None


class Request:
    def __init__(self, body=None, token=TOKEN, **params):
        data = json.dumps(body).encode() if body is not None else b''
        self.bounded_stream = SimpleNamespace(read=lambda: data)
        self._headers = {'Authorization': 'Bearer ' + token} if token else {}
        self._params = params

    def get_header(self, name):
        return self._headers.get(name)

    def get_param(self, name):
        return self._params.get(name)


class FakeDB:
    def __init__(self):
        self.saves, self.deletes = [], []

    def saveInstanceInDB(self, row):
        self.saves.append((type(row).__name__, getattr(row, 'name', None)))
        return True

    def deleteRowsWhere(self, cls, column, value):
        self.deletes.append((cls, value))
        return 1


def new_api(db=None):
    manager = SimpleNamespace(objectTables={}, db=db or FakeDB(), idList=[], objectTyping=[])
    api = IsleMeshAPI.__new__(IsleMeshAPI)
    api.manager = manager
    return api, manager


def call(api, name, body=None, **kw):
    sink = Sink()
    getattr(api, name)(Request(body, **kw), sink)
    return sink


def rows(manager, cls):
    return list(manager.objectTables.get(cls, {}).values())


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def main():
    vector = json.loads((FIX / 'storage-digest-vector.json').read_text())
    item = dict(vector['item'], hostingRelease=vector['hostingRelease'], title='APT to pol-core', access='frequent')
    tmp = tempfile.mkdtemp()
    os.environ['DATABASE_PATH'] = os.path.join(tmp, 'polari.db')
    saved = PlanStore().save({'revision': 0, 'title': 'T', 'items': [item]}, as_new=True)
    plan_id, revision = saved['id'], saved['revision']
    stored_item = next(i for i in saved['items'] if i['id'] == item['id'])
    digest = sp.storage_digest(plan_id, revision, stored_item)
    dataset, domain = 'apt-public-repo', 'apt.isle'
    migrate_id = 'isle.storage.migrate:%s@pol-core:%s' % (dataset, digest)
    authorize_id = 'isle.storage.authorize:%s@isle-core:%s' % (dataset, digest)
    cutover_id = 'isle.storage.cutover:%s@isle-core:%s' % (dataset, digest)

    def receipt(**over):
        r = {'kind': 'isle.storage.migrate', 'schemaVersion': 2, 'phase': 'A', 'actionId': migrate_id,
             'operation': 'op-1', 'attempt': 1, 'at': '2026-11-09T12:00:00+00:00', 'ok': True,
             'plan': {'id': plan_id, 'revision': revision, 'itemId': item['id'], 'digest': digest},
             'dataset': dataset, 'domain': domain, 'target': {'device': 'pol-core'},
             'contentSha': 'c' * 64, 'manifestSha': 'd' * 64, 'epoch': 1, 'contentVerified': True,
             'stagedDeploy': True, 'readinessVerified': True, 'stage': 'verifying-readiness'}
        r.update(over)
        return r

    def view(**over):
        v = {'dataset': dataset, 'domain': domain, 'device': 'pol-core', 'state': 'authorized', 'generation': 1,
             'plan': {'id': plan_id, 'revision': revision, 'digest': digest}, 'pending': None,
             'sourceDevice': 'isle-core'}
        v.update(over)
        return v

    db = FakeDB()
    api, manager = new_api(db)

    # ---- 0. doors: serialized writers, lock-free readers ----
    for name in ('on_post_storage_placement', 'on_post_storage_receipt', 'on_post_storage_witness'):
        check('%s is @_serialized' % name, hasattr(getattr(IsleMeshAPI, name), '__wrapped__'))
    for name in ('on_get_storage_placement', 'on_get_storage_receipts', 'on_get_storage_witnesses'):
        check('%s is lock-free (not wrapped)' % name, not hasattr(getattr(IsleMeshAPI, name), '__wrapped__'))

    # ---- 1. agent_address flows from the device ingest to the devices door ----
    s = call(api, 'on_post_ingest_device', {'device': 'isle-core', 'facts': {'agent_mode': 'core', 'agent_address': '10.10.0.5'}})
    check('core device ingest with agent_address accepted', s.media.get('ok') is True, str(s.media))
    call(api, 'on_post_ingest_device', {'device': 'pol-core', 'facts': {'agent_mode': 'remote'}})
    call(api, 'on_post_ingest_device', {'device': 'bad-addr', 'facts': {'agent_address': 'not-an-ip'}})
    s = call(api, 'on_get_devices')
    by_name = {d['name']: d for d in s.media['devices']}
    check('devices door returns agent_address for the reporting device', by_name['isle-core']['agent_address'] == '10.10.0.5')
    check('devices door returns None when the device reported none', by_name['pol-core']['agent_address'] is None)
    check('a non-IPv4 agent_address is ignored (None), not refused', by_name['bad-addr']['agent_address'] is None)
    check('the IsleDevice row stores agent_address', next(r for r in rows(manager, 'IsleDevice') if r.name == 'isle-core').agent_address == '10.10.0.5')
    call(api, 'on_post_ingest_device', {'device': 'isle-core', 'facts': {'agent_mode': 'core'}})
    check('a later report without it does not erase the address',
          {d['name']: d for d in call(api, 'on_get_devices').media['devices']}['isle-core']['agent_address'] == '10.10.0.5')

    # ---- 2. planned actions before anything is stored ----
    def actions():
        media = {'ok': True, 'plan': PlanStore().read(plan_id, revision)}
        sp.attach_planned_actions(media, api)
        return {a['kind'].split('.')[-1]: a for a in media['plannedActions']}
    a = actions()
    check('nothing stored: authorize planned with the argv text', a['authorize']['status'] == 'planned'
          and a['authorize']['operatorCommand'] == 'sudo isle storage authorize --dataset %s --plan %s --revision %d --item %s --digest %s'
          % (dataset, plan_id, revision, item['id'], digest), str(a['authorize']))
    check('nothing stored: migrate and cutover blocked without a command',
          a['migrate']['status'] == 'blocked' and a['cutover']['status'] == 'blocked'
          and a['migrate']['operatorCommand'] is None and a['cutover']['operatorCommand'] is None)

    # ---- 3. placement view door ----
    body = {'device': 'isle-core', 'entries': [view()]}
    s = call(api, 'on_post_storage_placement', dict(body, device='pol-core'))
    check('placement view refused for a non-core device (403)', s.status.startswith('403') and s.media['ok'] is False)
    s = call(api, 'on_post_storage_placement', dict(body, device='nobody'))
    check('placement view refused for an unknown device (403)', s.status.startswith('403'))
    s = call(api, 'on_post_storage_placement', body, token=None)
    check('placement view refused without a Bearer (401)', s.status.startswith('401'))
    check('nothing stored by the refusals', rows(manager, 'IsleStoragePlacementView') == [])
    s = call(api, 'on_post_storage_placement', dict(body, entries=[view(state='bogus')]))
    check('bad entry state refused (400)', s.status.startswith('400'))
    s = call(api, 'on_post_storage_placement', dict(body, entries=[view(), view()]))
    check('duplicate dataset refused (400)', s.status.startswith('400'))
    s = call(api, 'on_post_storage_placement', body)
    check('placement view accepted from the core', s.status == '200 OK' and s.media == {'ok': True, 'count': 1}, str(s.media))
    pv = rows(manager, 'IsleStoragePlacementView')
    check('view row stored with the Bearer fingerprint prefix, never the token',
          len(pv) == 1 and pv[0].posted_by == 'isle-core:' + FINGERPRINT[:16] and TOKEN not in json.dumps(pv[0].__dict__, default=str))
    s = call(api, 'on_get_storage_placement', dataset=dataset)
    check('GET filtered by dataset returns the single entry', s.media['ok'] and s.media['view']['dataset'] == dataset
          and s.media['view']['plan']['digest'] == digest and s.media['view']['generation'] == 1, str(s.media))
    check('GET filtered by domain returns the entry', call(api, 'on_get_storage_placement', domain=domain).media['view']['device'] == 'pol-core')
    s = call(api, 'on_get_storage_placement', dataset='nope')
    check('GET for an unknown dataset is 404 {ok:false}', s.status.startswith('404') and s.media['ok'] is False)
    check('GET unfiltered returns the list', call(api, 'on_get_storage_placement').media['view'][0]['dataset'] == dataset)
    s = call(api, 'on_post_storage_placement', {'device': 'isle-core', 'entries': [view(dataset='other-set', domain='other.isle')]})
    check('a new view replaces the whole set', [r.dataset for r in rows(manager, 'IsleStoragePlacementView')] == ['other-set']
          and ('IsleStoragePlacementView', pv[0].id) in db.deletes)
    call(api, 'on_post_storage_placement', body)
    a = actions()
    check('view authorized: authorize succeeded, migrate planned with argv text',
          a['authorize']['status'] == 'succeeded' and a['migrate']['status'] == 'planned'
          and a['migrate']['operatorCommand'] == 'sudo isle storage migrate --dataset %s --plan %s --revision %d --item %s --digest %s'
          % (dataset, plan_id, revision, item['id'], digest) and a['migrate']['placementState'] == 'authorized'
          and a['cutover']['status'] == 'blocked', str(a['migrate']))
    check('execute stays null for every action', all(x['execute'] is None for x in a.values()))

    # ---- 3b. file-backed view (written by the core via docker exec) beats the rows; never merged ----
    from datetime import datetime, timedelta, timezone
    view_file = Path(tmp) / 'isle-storage-placement-view.json'
    def stamp(seconds_ago=0):
        return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()
    def write_view(**over):
        doc = {'schemaVersion': 1, 'writtenAt': stamp(), 'writtenBy': 'isle-core', 'datasets': {
            dataset: view(state='cutover', generation=3, addresses=addresses, sourceDevice='isle-core')}}
        doc.update(over)
        view_file.write_text(json.dumps(doc))
    addresses = {'source': '10.10.0.5', 'target': '10.10.0.9'}
    s = call(api, 'on_get_storage_placement', dataset=dataset)
    check('no file: GET serves the rows with source door', s.media['source'] == 'door'
          and s.media['view']['addresses'] is None and s.media['view']['state'] == 'authorized')
    write_view()
    s = call(api, 'on_get_storage_placement', dataset=dataset)
    check('file: GET serves the file entry with source file, sourceDevice and addresses',
          s.media['source'] == 'file' and s.media['view']['state'] == 'cutover' and s.media['view']['generation'] == 3
          and s.media['view']['sourceDevice'] == 'isle-core' and s.media['view']['addresses'] == addresses
          and s.media['view']['plan']['digest'] == digest, str(s.media))
    check('file: unfiltered list is the file only (rows not merged)',
          [v['dataset'] for v in call(api, 'on_get_storage_placement').media['view']] == [dataset])
    check('file: planned actions read the file view (cutover state)', actions()['migrate']['placementState'] == 'cutover')
    write_view(writtenAt=stamp(601))
    s = call(api, 'on_get_storage_placement', dataset=dataset)
    check('stale file (601 s) answers 503, not the rows', s.status.startswith('503')
          and s.media == {'ok': False, 'error': 'placement view unavailable'}, str(s.media))
    write_view(writtenAt=stamp(300))
    check('a 300 s old file is still served', call(api, 'on_get_storage_placement', dataset=dataset).media['source'] == 'file')
    view_file.write_text('{"schemaVersion": 1, "writtenAt"')
    s = call(api, 'on_get_storage_placement', dataset=dataset)
    check('torn JSON answers 503, not the rows', s.status.startswith('503') and s.media['ok'] is False)
    check('unavailable view: planned actions see no view (fail closed)', actions()['migrate']['status'] != 'planned')
    for label, over in (('wrong schemaVersion', {'schemaVersion': 2}), ('unparseable writtenAt', {'writtenAt': 'yesterday'}),
                        ('no writtenBy', {'writtenBy': ''}), ('datasets a list', {'datasets': []}),
                        ('bad entry state', {'datasets': {dataset: view(state='bogus')}}),
                        ('key/dataset mismatch', {'datasets': {dataset: view(dataset='other-set')}})):
        write_view(**over)
        check('invalid file (%s) answers 503' % label, call(api, 'on_get_storage_placement').status.startswith('503'))
    view_file.unlink()
    check('file removed: rows with source door', call(api, 'on_get_storage_placement', dataset=dataset).media['source'] == 'door')
    s = call(api, 'on_post_storage_placement', {'device': 'isle-core', 'entries': [view(addresses=addresses)]})
    check('POST accepts and stores addresses', s.media.get('ok') is True and
          call(api, 'on_get_storage_placement', dataset=dataset).media['view']['addresses'] == addresses)
    check('POST refuses malformed addresses', call(api, 'on_post_storage_placement',
          {'device': 'isle-core', 'entries': [view(addresses={'target': 5})]}).status.startswith('400'))
    for verb in ('recover', 'accept', 'authorize', 'mark-migrated', 'reconcile-address', 'witness', 'rollback'):
        check('receipt kind isle.storage.%s is a known kind' % verb, 'isle.storage.%s' % verb in __import__('islemesh.islemesh_api', fromlist=['x'])._STORAGE_KINDS)

    # ---- 4. receipt door ----
    s = call(api, 'on_post_storage_receipt', receipt())
    check('receipt accepted and stored unverified', s.status == '200 OK' and s.media['ok'] and s.media['verified'] is False
          and s.media['seen'] == 1 and s.media['idempotent'] is False, str(s.media))
    rr = rows(manager, 'IsleStorageReceipt')
    check('receipt row carries the digest, device, poster fingerprint and subject, verified False',
          len(rr) == 1 and rr[0].plan_digest == digest and rr[0].device == 'pol-core' and rr[0].verified is False
          and rr[0].poster_fingerprint == FINGERPRINT and rr[0].poster_subject == 'pol-core'
          and rr[0].ok is True and rr[0].epoch == 1 and rr[0].content_sha == 'c' * 64)
    check('the token is not stored anywhere on the row', TOKEN not in json.dumps(rr[0].__dict__, default=str))
    bad = receipt(plan={'id': plan_id, 'revision': revision, 'itemId': item['id'], 'digest': 'e' * 64},
                  actionId='isle.storage.migrate:%s@pol-core:%s' % (dataset, 'e' * 64))
    s = call(api, 'on_post_storage_receipt', bad)
    check('wrong digest refused 409 with the contract words', s.status.startswith('409')
          and s.media == {'ok': False, 'error': 'receipt names a plan or digest the core does not hold'}, str(s.media))
    s = call(api, 'on_post_storage_receipt', receipt(plan={'id': 'f' * 32, 'revision': 9, 'itemId': item['id'], 'digest': digest}))
    check('unheld plan id/revision refused 409', s.status.startswith('409'))
    s = call(api, 'on_post_storage_receipt', receipt(plan={'id': plan_id, 'revision': revision, 'itemId': 'no-such-item', 'digest': digest}))
    check('unknown item refused 409', s.status.startswith('409'))
    for label, over in (('bad kind', {'kind': 'isle.storage.bogus'}), ('bad actionId', {'actionId': 'migrate'}),
                        ('non-int epoch', {'epoch': '1'}), ('bool epoch', {'epoch': True}), ('bad contentSha', {'contentSha': 'xyz'}),
                        ('non-bool ok', {'ok': 'yes'}), ('actionId dataset mismatch', {'dataset': 'other'})):
        s = call(api, 'on_post_storage_receipt', receipt(**over))
        check('shape: %s refused 400' % label, s.status.startswith('400') and s.media['ok'] is False, s.status)
    check('null contentSha/manifestSha accepted', call(api, 'on_post_storage_receipt', receipt(attempt=2, ok=False, contentSha=None, manifestSha=None, stage='copying')).status == '200 OK')
    check('no extra rows from the refusals', len(rows(manager, 'IsleStorageReceipt')) == 2)
    s = call(api, 'on_post_storage_receipt', receipt(), token='ANOTHER-TOKEN')
    check('identical re-post is idempotent: 200, seen 2, same row', s.status == '200 OK' and s.media['idempotent'] is True
          and s.media['seen'] == 2 and len(rows(manager, 'IsleStorageReceipt')) == 2
          and rows(manager, 'IsleStorageReceipt')[0].poster_fingerprint == FINGERPRINT)
    s = call(api, 'on_post_storage_receipt', receipt(words='different words'))
    check('a different receipt for the same actionId and attempt is 409', s.status.startswith('409') and s.media['ok'] is False, str(s.media))
    check('the stored receipt was not rewritten', json.loads(rows(manager, 'IsleStorageReceipt')[0].receipt_json).get('words') is None)

    # ---- 5. planned-action status from stored rows ----
    a = actions()
    check('qualifying receipt: migrate succeeded', a['migrate']['status'] == 'succeeded' and a['migrate']['operatorCommand'] is None)
    check('view still authorized: cutover stays blocked', a['cutover']['status'] == 'blocked')
    call(api, 'on_post_storage_placement', {'device': 'isle-core', 'entries': [view(state='migrated', generation=3)]})
    a = actions()
    check('migrated view + receipt: cutover planned with --generation from the view',
          a['cutover']['status'] == 'planned' and a['cutover']['operatorCommand'] == 'sudo isle storage cutover --dataset %s --generation 3' % dataset
          and a['cutover']['placementState'] == 'migrated', str(a['cutover']))
    call(api, 'on_post_storage_placement', {'device': 'isle-core', 'entries': [view(state='cutover', generation=5)]})
    check('cutover view: cutover succeeded', actions()['cutover']['status'] == 'succeeded')
    call(api, 'on_post_storage_placement', {'device': 'isle-core', 'entries': [view(plan={'id': plan_id, 'revision': revision, 'digest': 'a' * 64})]})
    a = actions()
    check('a view for another digest does not authorize this plan', a['authorize']['status'] == 'planned' and a['migrate']['status'] == 'succeeded'
          and a['cutover']['status'] == 'blocked')
    # a receipt that is ok but lacks readiness does not make migrate succeed
    api2, m2 = new_api()
    call(api2, 'on_post_ingest_device', {'device': 'isle-core', 'facts': {'agent_mode': 'core'}})
    call(api2, 'on_post_storage_placement', {'device': 'isle-core', 'entries': [view()]})
    call(api2, 'on_post_storage_receipt', receipt(readinessVerified=False))
    media = {'ok': True, 'plan': PlanStore().read(plan_id, revision)}
    sp.attach_planned_actions(media, api2)
    st = {x['kind'].split('.')[-1]: x['status'] for x in media['plannedActions']}
    check('receipt without readinessVerified: migrate is failed, not planned', st['migrate'] == 'failed' and st['cutover'] == 'blocked', str(st))

    def actions2():
        media = {'ok': True, 'plan': PlanStore().read(plan_id, revision)}
        sp.attach_planned_actions(media, api2)
        return {x['kind'].split('.')[-1]: x for x in media['plannedActions']}
    call(api2, 'on_post_storage_receipt', receipt(attempt=2, ok=False, failedStage='deploying-host', operation='ab' * 16))
    mig = actions2()['migrate']
    check('a stored failed receipt: migrate is failed and says where it stopped', mig['status'] == 'failed'
          and 'attempt 2 says the migrate stopped at deploying-host' in mig['statusWords'], str(mig))
    check('its command is the resume of that operation', mig['operatorCommand'] == 'sudo isle operation retry ' + 'ab' * 16, str(mig))
    call(api2, 'on_post_storage_placement', {'device': 'isle-core', 'entries': [view(state='migrated', generation=2)]})
    a2 = actions2()
    check('placement migrated with no finished receipt stored: receipt not delivered',
          a2['migrate']['status'] == 'interrupted' and a2['migrate']['statusWords'].startswith('receipt not delivered')
          and a2['cutover']['status'] == 'blocked' and 'receipt not delivered' in a2['cutover']['statusWords'], str(a2))
    call(api2, 'on_post_storage_receipt', receipt(attempt=3))
    a2 = actions2()
    check('the finished receipt arrives under the next attempt: migrate succeeded, cutover planned',
          a2['migrate']['status'] == 'succeeded' and a2['cutover']['status'] == 'planned', str(a2))

    # ---- 6. witness door ----
    def witness(**over):
        w = {'dataset': dataset, 'device': 'econ-core', 'generation': 5, 'contentSha': 'c' * 64, 'actionId': cutover_id,
             'resolvedAddress': '10.10.0.9', 'route': ['dig @router apt.isle -> 10.10.0.9'], 'at': '2026-11-09T12:30:00+00:00',
             'sampled': [{'path': 'InRelease', 'sha256': 'a' * 64}]}
        w.update(over)
        return w
    s = call(api, 'on_post_storage_witness', witness())
    wr = rows(manager, 'IsleStorageWitness')
    check('witness accepted, stored unverified', s.status == '200 OK' and s.media['ok'] and s.media['verified'] is False and len(wr) == 1
          and wr[0].verified is False and wr[0].generation == 5 and wr[0].resolved_address == '10.10.0.9'
          and wr[0].poster_fingerprint == FINGERPRINT and wr[0].poster_subject == 'econ-core', str(s.media))
    s = call(api, 'on_post_storage_witness', witness())
    check('identical witness re-post is idempotent (seen 2, one row)', s.media['idempotent'] is True and s.media['seen'] == 2 and len(rows(manager, 'IsleStorageWitness')) == 1)
    s = call(api, 'on_post_storage_witness', witness(resolvedAddress='10.10.0.77'))
    check('a different witness for the same dataset/generation/device is 409 conflict', s.status.startswith('409')
          and s.media['error'] == 'conflicting witness for this epoch and device', str(s.media))
    check('a witness for another device or epoch is accepted', call(api, 'on_post_storage_witness', witness(device='other')).status == '200 OK'
          and call(api, 'on_post_storage_witness', witness(generation=6)).status == '200 OK' and len(rows(manager, 'IsleStorageWitness')) == 3)
    for label, over in (('bad contentSha', {'contentSha': 'zz'}), ('bad actionId', {'actionId': 'x'}), ('non-int generation', {'generation': '5'}),
                        ('bad address', {'resolvedAddress': 'apt.isle'}), ('bad time', {'at': 'yesterday'}), ('no sampled list', {'sampled': 'x'}),
                        ('epoch disagrees', {'epoch': 4})):
        s = call(api, 'on_post_storage_witness', witness(device='x' + str(len(label)), **over))
        check('shape: witness %s refused 400' % label, s.status.startswith('400'), s.status)
    check('null resolvedAddress accepted', call(api, 'on_post_storage_witness', witness(device='dev-null', resolvedAddress=None)).status == '200 OK')

    # ---- 7. read lists ----
    s = call(api, 'on_get_storage_receipts', dataset=dataset)
    docs = s.media['receipts']
    check('GET receipts returns parsed receipt_json with poster and verified', s.media['ok'] and len(docs) == 2
          and all(isinstance(d['receipt'], dict) for d in docs) and docs[0]['receipt']['plan']['digest'] == digest
          and docs[0]['posterPresented'] == {'fingerprint': FINGERPRINT, 'subject': 'pol-core'} and docs[0]['verified'] is False
          and docs[0]['seen'] == 2, str(docs[:1]))
    check('GET receipts filters by dataset', call(api, 'on_get_storage_receipts', dataset='nope').media['receipts'] == [])
    s = call(api, 'on_get_storage_witnesses', dataset=dataset)
    check('GET witnesses returns parsed witness_json', s.media['ok'] and len(s.media['witnesses']) == 4
          and isinstance(s.media['witnesses'][0]['witness'], dict) and s.media['witnesses'][0]['witness']['actionId'] == cutover_id)

    # ---- 8. persistence truth: a failing save answers 500 persisted:false ----
    failing, _ = new_api()
    failing.manager.db = SimpleNamespace(saveInstanceInDB=lambda row: False, deleteRowsWhere=lambda *a: 1)
    failing.manager.objectTables['IsleDevice'] = {}
    from islemesh.islemesh_basis import IsleDevice
    IsleDevice(name='isle-core', agent_mode='core', manager=failing.manager)
    s = call(failing, 'on_post_storage_receipt', receipt())
    check('receipt on a refusing database answers 500 persisted:false', s.status.startswith('500') and s.media.get('persisted') is False)
    s = call(failing, 'on_post_storage_placement', {'device': 'isle-core', 'entries': [view()]})
    check('placement on a refusing database answers 500 persisted:false', s.status.startswith('500') and s.media.get('persisted') is False)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
