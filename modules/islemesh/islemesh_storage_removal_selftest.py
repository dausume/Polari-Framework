"""
@module islemesh.islemesh_storage_removal_selftest

Controls for stm-2c, the receipt-gated removal-check (docs/STORAGE-MIGRATION-CONTRACT.md 1 "Auto-removals", 6):
source_removal_allowed, PlanStore.save refusals, the removal-check GET, and the byte-for-byte old-plan fixture.
Decided from stored receipts and the placement view only. Run from polari-framework/:

  PYTHONPATH=.:modules python3 -m islemesh.islemesh_storage_removal_selftest
"""
import copy
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from islemesh.islemesh_api import IsleMeshAPI
from islemesh.custom import islemesh_storage_plan as sp
from islemesh.custom.islemesh_planning import PlanStore, validate

_results = []
FIX = Path(__file__).parent / 'custom' / 'fixtures'


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra and not cond else ''))


def mk(i, app, dev):
    return dict(id=i, device=dev, title=app, app=app, kind='polari', state='existing', access='frequent')


class Rows:
    def __init__(self, views=None, receipts=None):
        self.views, self.receipts = views or {}, receipts or []

    def _storage_views(self):
        return self.views

    def _storage_receipt_documents(self):
        return self.receipts


def refused(store, plan, rows):
    try:
        store.save(plan, rows=rows)
    except ValueError as exc:
        return str(exc)
    return None


def main():
    vector = json.loads((FIX / 'storage-digest-vector.json').read_text())
    storage = dict(vector['item'], hostingRelease=vector['hostingRelease'], title='APT to pol-core', access='frequent')
    storage['storage']['source']['apps'] = ['aptrepo']
    tmp = tempfile.mkdtemp()
    store = PlanStore(Path(tmp) / 'p.json')
    src, spare, other = mk('aptrepo', 'aptrepo', 'isle-core'), mk('spare', 'aptrepo', 'econ-core'), mk('other', 'other', 'isle-core')
    saved = store.save({'revision': 0, 'title': 'T', 'items': [src, spare, other, storage]}, as_new=True)
    store.activate(saved['id'], saved['generation'], saved['revision'])
    stored = next(i for i in saved['items'] if i['kind'] == 'storage')
    digest = sp.storage_digest(saved['id'], saved['revision'], stored)
    dataset = stored['storage']['dataset']
    migrate_id = 'isle.storage.migrate:%s@pol-core:%s' % (dataset, digest)
    receipt = {'kind': 'isle.storage.migrate', 'actionId': migrate_id, 'ok': True, 'contentVerified': True,
               'stagedDeploy': True, 'readinessVerified': True, 'plan': {'digest': digest}}
    hosting = {dataset: {'dataset': dataset, 'state': 'hosting', 'plan': {'digest': digest}}}
    migrated = {dataset: {'dataset': dataset, 'state': 'migrated', 'plan': {'digest': digest}}}
    keep = [spare, other, stored]
    drop = lambda plan_items: dict(saved, items=plan_items)

    # ---- the function ----
    r = sp.source_removal_allowed(saved, drop(keep), Rows())
    check('no receipt, no view: refused', any('no verified migrate receipt' in x for x in r) and any('not hosting' in x for x in r), str(r))
    r = sp.source_removal_allowed(saved, drop(keep), Rows(migrated, [receipt]))
    check('receipt but view not hosting: refused', any('not hosting' in x for x in r) and not any('no verified' in x for x in r), str(r))
    r = sp.source_removal_allowed(saved, drop(keep), Rows(hosting, [receipt]))
    check('receipt + hosting but Phase A: refused with the Phase A words', r == [sp.PHASE_A_REASON] and 'Phase A' in r[0], str(r))
    check('Phase A flag defaults to True', sp.PHASE_A_SOURCE_RETAINED is True)
    sp.PHASE_A_SOURCE_RETAINED = False
    try:
        check('Phase A flag False + receipt + hosting + other provider: allowed',
              sp.source_removal_allowed(saved, drop(keep), Rows(hosting, [receipt])) == [])
        bad = dict(receipt, contentVerified=False)
        check('an unverified receipt is not evidence',
              sp.source_removal_allowed(saved, drop(keep), Rows(hosting, [bad])) != [])
        stale = {dataset: {'state': 'hosting', 'plan': {'digest': 'f' * 64}}}
        check('a view for another digest is not evidence',
              sp.source_removal_allowed(saved, drop(keep), Rows(stale, [receipt])) != [])
        check('receipt for another digest is not evidence',
              sp.source_removal_allowed(saved, drop(keep), Rows(hosting, [dict(receipt, plan={'digest': 'e' * 64})])) != [])
        r = sp.source_removal_allowed(saved, drop([other, stored]), Rows(hosting, [receipt]))
        check('last provider of the app is denied', len(r) == 1 and 'last provider' in r[0], str(r))
        r = sp.source_removal_allowed(saved, drop([spare, stored]), Rows(hosting, [receipt]))
        check('an item that is not a source (app not listed) is unaffected', r == [], str(r))
        protected = dict(spare, protectedRoles=['backend'])
        r = sp.source_removal_allowed(saved, drop([protected, other, stored]), Rows(hosting, [receipt]))
        check('protectedRoles is never read', r == [], str(r))
        check('keeping the source item is allowed with no rows', sp.source_removal_allowed(saved, saved, None) == [])
        check('a source moved to a deferred state counts as absent',
              sp.source_removal_allowed(saved, drop([dict(src, state='deferred'), spare, other, stored]), Rows(hosting, [receipt])) == [])
    finally:
        sp.PHASE_A_SOURCE_RETAINED = True

    # ---- PlanStore.save ----
    new = {'revision': saved['revision'], 'id': saved['id'], 'title': 'T', 'items': copy.deepcopy(keep)}
    msg = refused(store, new, Rows())
    check('save without receipt refused with removal refused: prefix', bool(msg) and msg.startswith('removal refused: '), str(msg))
    msg = refused(store, new, Rows(hosting, [receipt]))
    check('save with receipt + hosting still refused in Phase A', bool(msg) and 'Phase A' in msg, str(msg))
    check('save with no rows refused', bool(refused(store, new, None)))
    check('refused saves wrote nothing', store.read()['revision'] == saved['revision'])
    sp.PHASE_A_SOURCE_RETAINED = False
    try:
        out = store.save(new, rows=Rows(hosting, [receipt]))
        check('save accepted when evidence complete and Phase A off', out['revision'] == saved['revision'] + 1)
        check('no auto-removal is added for the suppressed source', all(x['app'] != 'aptrepo' or x['device'] != 'isle-core' for x in out['removals']))
    finally:
        sp.PHASE_A_SOURCE_RETAINED = True

    # plans without storage items save exactly as before
    plain = PlanStore(Path(tmp) / 'q.json')
    first = plain.save({'revision': 0, 'title': 'T', 'items': [src, other]})
    out = plain.save({'revision': first['revision'], 'id': first['id'], 'title': 'T', 'items': [other]})
    check('plan without storage items: a dropped item is auto-removed as before', [r['app'] for r in out['removals']] == ['aptrepo'])

    # old-plan fixture byte for byte
    old = json.loads((FIX / 'placement-plan-v2-oldshape.json').read_text())
    got = json.dumps(validate(old), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    check('old-plan fixture validates byte for byte', got == (FIX / 'placement-plan-v2-oldshape.validated.json').read_text())

    # ---- removal-check GET ----
    class Stub(IsleMeshAPI):
        def on_get_graph(self, request, response):
            response.media = {'nodes': []}

        def _storage_views(self):
            return {}

        def _storage_receipt_documents(self):
            return []

    api = Stub.__new__(Stub)
    api.manager = SimpleNamespace(objectTables={}, db=None, idList=[], objectTyping=[])
    os.environ['DATABASE_PATH'] = os.path.join(tmp, 'polari.db')
    again = PlanStore().save({'revision': 0, 'title': 'T', 'items': [src, spare, other, storage]}, as_new=True)
    PlanStore().activate(again['id'], again['generation'], again['revision'])

    def get(app, device):
        resp = SimpleNamespace(media=None, status='200 OK')
        api.on_get_removal_check(SimpleNamespace(get_param=lambda n: {'app': app, 'device': device}.get(n)), resp)
        return resp.media
    media = get('aptrepo', 'isle-core')
    check('GET reports not allowed with the storage reasons', media['allowed'] is False
          and any('migrate receipt' in x for x in media['reasons']) and any('Phase A' in x for x in media['reasons']), str(media))
    media = get('other', 'isle-core')
    check('GET for a non-source app is unaffected', media['allowed'] is True and media['reasons'] == [], str(media))

    from islemesh.custom import islemesh_storage_plan as _sp
    original = _sp.source_removal_allowed
    for exc in (OSError('plan store unreadable'), ValueError('bad view'), RuntimeError('boom')):
        def raising(*a, _e=exc, **k):
            raise _e
        _sp.source_removal_allowed = raising
        try:
            media = get('other', 'isle-core')
        finally:
            _sp.source_removal_allowed = original
        check('GET fails closed when the storage check raises %s' % type(exc).__name__, media['allowed'] is False
              and media['reasons'] == ['storage removal check unavailable: %s' % exc], str(media))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
