import copy
import json
import tempfile
import unittest
from pathlib import Path
from islemesh.custom import islemesh_storage_plan as sp
from islemesh.custom.islemesh_planning import PlanStore, validate

FIX = Path(__file__).parent / 'custom' / 'fixtures'
PID = 'ce23b61c3a444592a0e9274751f76854'


def vector():
    return json.loads((FIX / 'storage-digest-vector.json').read_text())


def item(**over):
    v = vector()
    it = dict(v['item'], hostingRelease=v['hostingRelease'], title='APT to pol-core', access='frequent')
    it.update(over)
    return it


def mutate(path, value):
    it = item()
    node = it
    for k in path[:-1]:
        node = node[k]
    if value is KeyError:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return it


class Fake:
    def __init__(self, devices):
        self.devices = devices

    def _capability_devices(self):
        return self.devices


class StoragePlan(unittest.TestCase):
    def test_vector_digest(self):
        v = vector()
        self.assertEqual(sp.storage_digest(v['planId'], v['revision'], item()), v['expectedDigest'])

    def test_payload_keys(self):
        p = sp.storage_digest_payload(PID, 2, item())
        self.assertEqual(sorted(p), sorted(['planId', 'revision', 'itemId', 'device', 'originDevice', 'app',
                                            'state', 'storage', 'hostingRelease']))

    def test_digest_ignores_unknown_and_display_keys(self):
        base = sp.storage_digest(PID, 2, item())
        it = item(notes='x', title='other', ramMiB=5, protectedRoles=['aptrepo'])
        it['storage']['junk'] = 1
        it['storage']['source']['junk'] = 1
        it['hostingRelease']['junk'] = 1
        self.assertEqual(sp.storage_digest(PID, 2, it), base)

    def test_digest_changes(self):
        base = sp.storage_digest(PID, 2, item())
        self.assertNotEqual(sp.storage_digest(PID, 3, item()), base)
        self.assertNotEqual(sp.storage_digest(PID, 2, item(state='deferred')), base)
        self.assertNotEqual(sp.storage_digest(PID, 2, item(id='other')), base)
        it = item()
        it['hostingRelease']['version'] = '9'
        self.assertNotEqual(sp.storage_digest(PID, 2, it), base)
        it = item()
        it['storage']['domain'] = 'other.isle'
        self.assertNotEqual(sp.storage_digest(PID, 2, it), base)

    def test_bad_ids(self):
        for pid in ('default', PID.upper(), None):
            with self.assertRaises(ValueError):
                sp.storage_digest(pid, 2, item())
        for rev in (-1, True, '2'):
            with self.assertRaises(ValueError):
                sp.storage_digest(PID, rev, item())
        with self.assertRaises(ValueError):
            sp.storage_digest(PID, 2, item(id='bad id'))

    def test_valid_item(self):
        block = sp.validate_storage_item(item())
        self.assertEqual(block['dataset'], 'apt-public-repo')
        self.assertTrue(sp.is_storage_item(item()))
        self.assertFalse(sp.is_storage_item({'kind': 'task'}))
        self.assertFalse(sp.is_storage_item(None))

    def test_refusals(self):
        bad = {
            'kind': item(kind='task'),
            'app empty': item(app=''),
            'app not string': item(app=3),
            'state': item(state='running'),
            'device != target': item(device='other'),
            'origin != source': item(originDevice='other'),
            'no hostingRelease': mutate(['hostingRelease'], None),
            'release name != app': mutate(['hostingRelease', 'name'], 'x'),
            'release version': mutate(['hostingRelease', 'version'], ''),
            'release sha short': mutate(['hostingRelease', 'manifestSha256'], 'ab'),
            'release sha upper': mutate(['hostingRelease', 'manifestSha256'], 'A' * 64),
            'storage missing': mutate(['storage'], None),
            'schemaVersion': mutate(['storage', 'schemaVersion'], 2),
            'schemaVersion bool': mutate(['storage', 'schemaVersion'], True),
            'dataset upper': mutate(['storage', 'dataset'], 'Apt'),
            'dataset long': mutate(['storage', 'dataset'], 'a' * 65),
            'domain not isle': mutate(['storage', 'domain'], 'apt.example'),
            'domain bare': mutate(['storage', 'domain'], 'isle'),
            'domain underscore': mutate(['storage', 'domain'], 'a_b.isle'),
            'domain hyphen edge': mutate(['storage', 'domain'], '-a.isle'),
            'domain trailing': mutate(['storage', 'domain'], 'apt.isle.'),
            'domain newline': mutate(['storage', 'domain'], 'apt.isle\n'),
            'domain 9 labels': mutate(['storage', 'domain'], 'a.b.c.d.e.f.g.h.isle'),
            'abs relativePath': mutate(['storage', 'target', 'relativePath'], '/x'),
            'dotdot relativePath': mutate(['storage', 'target', 'relativePath'], 'a/../b'),
            'long relativePath': mutate(['storage', 'target', 'relativePath'], 'a' * 201),
            'empty relativePath': mutate(['storage', 'target', 'relativePath'], ''),
            'mountpoint relative': mutate(['storage', 'target', 'mountpoint'], 'mnt'),
            'mountpoint dotdot': mutate(['storage', 'target', 'mountpoint'], '/mnt/../x'),
            'snapshot short': mutate(['storage', 'source', 'snapshotSha256'], 'abc'),
            'snapshot upper': mutate(['storage', 'source', 'snapshotSha256'], 'A' * 64),
            'capacity low': mutate(['storage', 'target', 'capacityBytes'], 17179869184),
            'capacity just low': mutate(['storage', 'target', 'capacityBytes'], 18038862643),
            'totalBytes bool': mutate(['storage', 'source', 'totalBytes'], True),
            'entries negative': mutate(['storage', 'source', 'entries'], -1),
            'sourceRemoval': mutate(['storage', 'sourceRemoval'], 'immediate'),
            'sourceRemoval missing': mutate(['storage', 'sourceRemoval'], KeyError),
            'contentSha bad': mutate(['storage', 'source', 'contentSha256'], 'xyz'),
            'apps not list': mutate(['storage', 'source', 'apps'], 'apt'),
            'apps bad name': mutate(['storage', 'source', 'apps'], ['Apt']),
            'apps too many': mutate(['storage', 'source', 'apps'], ['a%d' % i for i in range(9)]),
        }
        for name, it in bad.items():
            with self.subTest(name), self.assertRaises(ValueError):
                sp.validate_storage_item(it)

    def test_capacity_boundary_exact(self):
        it = mutate(['storage', 'target', 'capacityBytes'], sp.required_capacity(17179869184))
        sp.validate_storage_item(it)
        self.assertEqual(sp.required_capacity(100), 105)
        self.assertEqual(sp.required_capacity(101), 107)

    def test_null_snapshot_accepted_but_no_actions(self):
        it = mutate(['storage', 'source', 'snapshotSha256'], None)
        sp.validate_storage_item(it)
        self.assertEqual(sp.planned_actions({'id': PID, 'revision': 2, 'items': [it]}, 'isle-core'), [])

    def test_optional_keys_whitelisted(self):
        it = item()
        it['storage']['source'].update(contentSha256='c' * 64, apps=['aptrepo'])
        src = sp.validate_storage_item(it)['source']
        self.assertEqual(src['contentSha256'], 'c' * 64)
        self.assertEqual(src['apps'], ['aptrepo'])
        self.assertNotIn('apps', sp.validate_storage_item(item())['source'])
        self.assertNotIn('contentSha256', sp.validate_storage_item(item())['source'])
        it['storage']['source']['contentSha256'] = None
        self.assertNotIn('contentSha256', sp.validate_storage_item(it)['source'])

    def plan(self, items):
        return {'revision': 0, 'title': 'T', 'items': items}

    def test_old_plan_byte_for_byte(self):
        old = json.loads((FIX / 'placement-plan-v2-oldshape.json').read_text())
        got = json.dumps(validate(old), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        self.assertEqual(got, (FIX / 'placement-plan-v2-oldshape.validated.json').read_text())

    def test_old_kinds_still_checked(self):
        old = json.loads((FIX / 'placement-plan-v2-oldshape.json').read_text())
        old['items'][0]['kind'] = 'bogus'
        with self.assertRaises(ValueError):
            validate(old)
        old['items'][0]['kind'] = 'catalog'
        old['items'][0]['app'] = ''
        with self.assertRaises(ValueError):
            validate(old)
        self.assertNotIn('storage', validate(json.loads((FIX / 'placement-plan-v2-oldshape.json').read_text()))['items'][0])

    def test_plan_with_storage_item(self):
        it = item(junk='x')
        it['storage']['junk'] = 1
        out = validate(self.plan([it]))['items'][0]
        self.assertEqual(out['kind'], 'storage')
        self.assertEqual(out['storage'], sp.validate_storage_item(item()))
        self.assertEqual(out['hostingRelease'], vector()['hostingRelease'])
        self.assertNotIn('junk', out)
        self.assertNotIn('junk', out['storage'])

    def test_plan_storage_item_refused(self):
        for it in (item(device='x'), mutate(['storage', 'domain'], 'a.com'), mutate(['hostingRelease'], None)):
            with self.assertRaises(ValueError):
                validate(self.plan([it]))
        it = item()
        del it['storage']
        with self.assertRaises(ValueError):
            validate(self.plan([it]))

    def test_planned_actions_chain(self):
        v = vector()
        plan = {'id': v['planId'], 'revision': v['revision'], 'items': [item()]}
        acts = sp.planned_actions(plan, 'isle-core')
        self.assertEqual([a['kind'] for a in acts],
                         ['isle.storage.authorize', 'isle.storage.migrate', 'isle.storage.cutover'])
        self.assertEqual([a['device'] for a in acts], ['isle-core', 'pol-core', 'isle-core'])
        d = v['expectedDigest']
        self.assertEqual(acts[0]['id'], 'isle.storage.authorize:apt-public-repo@isle-core:' + d)
        self.assertEqual(acts[1]['dependsOn'], [acts[0]['id']])
        self.assertEqual(acts[2]['dependsOn'], [acts[1]['id']])
        self.assertEqual(acts[0]['dependsOn'], [])
        # stm-2b: with nothing recorded, authorize (no dependsOn) is planned; the rest wait on it.
        self.assertEqual([a['status'] for a in acts], ['planned', 'blocked', 'blocked'])
        self.assertEqual([a['operatorCommand'] is None for a in acts], [False, True, True])
        for a in acts:
            self.assertIsNone(a['execute'])
            self.assertIsNone(a['undo'])
            self.assertEqual(a['chain'], [])
            self.assertEqual(a['digest'], d)
            self.assertEqual((a['planId'], a['revision'], a['itemId'], a['dataset']),
                             (PID, 2, 'apt-repo-to-pol-core', 'apt-public-repo'))
            self.assertIsNone(a['placementState'])
        self.assertFalse(any('retire' in a['kind'] for a in acts))

    def test_planned_actions_placement_state_and_filters(self):
        plan = {'id': PID, 'revision': 2, 'items': [item()]}
        acts = sp.planned_actions(plan, 'isle-core', {'apt-public-repo': {'state': 'authorized'}})
        self.assertEqual({a['placementState'] for a in acts}, {'authorized'})
        self.assertEqual(sp.planned_actions(dict(plan, items=[item(state='existing')]), 'isle-core'), [])
        self.assertEqual(sp.planned_actions(dict(plan, items=[item(state='deferred')]), 'isle-core'), [])
        self.assertEqual(sp.planned_actions(dict(plan, id='default'), 'isle-core'), [])
        self.assertEqual(sp.planned_actions({'id': PID, 'revision': 1, 'items': [{'kind': 'task'}]}, 'c'), [])

    def migrate_with(self, receipts, state='authorized', **view):
        """(migrate, cutover) of the vector's plan with the placement in `state` for its digest and these stored receipts."""
        v = vector()
        plan = {'id': v['planId'], 'revision': v['revision'], 'items': [item()]}
        d = v['expectedDigest']
        action = 'isle.storage.migrate:apt-public-repo@pol-core:' + d
        stored = [dict({'kind': 'isle.storage.migrate', 'actionId': action, 'plan': {'digest': d}}, **r) for r in receipts]
        views = {'apt-public-repo': dict({'state': state, 'generation': 2, 'planDigest': d}, **view)}
        acts = sp.planned_actions(plan, 'isle-core', views, stored)
        return acts[1], acts[2], d

    def test_a_stored_failure_is_shown_as_failed_with_the_resume(self):
        op = 'c0' * 16
        mig, cut, d = self.migrate_with([{'ok': False, 'attempt': 1, 'failedStage': 'receiving-content', 'operation': op}])
        self.assertEqual((mig['status'], cut['status']), ('failed', 'blocked'))
        self.assertIn('attempt 1 says the migrate stopped at receiving-content', mig['statusWords'])
        self.assertIn('resume that operation on pol-core', mig['statusWords'])
        self.assertIn('its receipt did not reach the core', mig['statusWords'])
        self.assertEqual(mig['operatorCommand'], 'sudo isle operation retry ' + op)
        again = 'sudo isle storage migrate --dataset apt-public-repo --plan %s --revision 2 --item apt-repo-to-pol-core --digest %s' % (PID, d)
        # the highest attempt is the one shown, whatever order the rows come in
        mig, _, _ = self.migrate_with([{'ok': False, 'attempt': 3, 'failedStage': 'deploying-host', 'operation': op},
                                       {'ok': False, 'attempt': 2, 'failedStage': 'receiving-content', 'operation': op}])
        self.assertIn('attempt 3 says the migrate stopped at deploying-host', mig['statusWords'])
        # an ok receipt that lacks a proof is not a finished migrate
        mig, _, _ = self.migrate_with([{'ok': True, 'attempt': 1, 'contentVerified': True, 'stagedDeploy': True, 'operation': op}])
        self.assertEqual(mig['status'], 'failed')
        self.assertIn('attempt 1 does not show readinessVerified', mig['statusWords'])
        # what a device wrote is never printed unless it has the expected shape
        for bad in ('x; rm -rf /', 'C0' * 16, 'c0' * 17, 7, None):
            mig, _, _ = self.migrate_with([{'ok': False, 'attempt': 1, 'failedStage': 'Stage one\n$(x)', 'operation': bad}])
            self.assertEqual(mig['operatorCommand'], again)
            self.assertIn('attempt 1 says the migrate did not finish', mig['statusWords'])
            self.assertIn('run the migrate again on pol-core', mig['statusWords'])
            self.assertNotIn('$(x)', json.dumps(mig))
        mig, _, _ = self.migrate_with([{'ok': False, 'attempt': 'nine', 'operation': op}])
        self.assertIn('attempt 1 says', mig['statusWords'])

    def test_a_finished_receipt_wins_over_failed_ones(self):
        good = {'ok': True, 'attempt': 2, 'contentVerified': True, 'stagedDeploy': True, 'readinessVerified': True}
        mig, cut, _ = self.migrate_with([{'ok': False, 'attempt': 1}, good, {'ok': False, 'attempt': 3}], state='migrated')
        self.assertEqual((mig['status'], mig['operatorCommand'], cut['status']), ('succeeded', None, 'planned'))

    def test_receipts_of_another_action_or_digest_do_not_count(self):
        v = vector()
        plan = {'id': v['planId'], 'revision': v['revision'], 'items': [item()]}
        d = v['expectedDigest']
        views = {'apt-public-repo': {'state': 'authorized', 'planDigest': d}}
        action = 'isle.storage.migrate:apt-public-repo@pol-core:' + d
        for other in ({'kind': 'isle.storage.migrate', 'actionId': action, 'plan': {'digest': 'a' * 64}, 'ok': False},
                      {'kind': 'isle.storage.migrate', 'actionId': action.replace('pol-core', 'other'), 'plan': {'digest': d}, 'ok': False},
                      {'kind': 'isle.storage.sync', 'actionId': action, 'plan': {'digest': d}, 'ok': False}, 'not a receipt'):
            mig = sp.planned_actions(plan, 'isle-core', views, [other])[1]
            self.assertEqual((mig['status'], mig['statusWords']), ('planned', 'authorized; ready to run on the target (no migrate receipt is stored here)'))
        # a failed receipt does not unblock a migrate that is not authorized for this digest
        failed = {'kind': 'isle.storage.migrate', 'actionId': action, 'plan': {'digest': d}, 'ok': False}
        mig = sp.planned_actions(plan, 'isle-core', {'apt-public-repo': {'state': 'authorized', 'planDigest': 'a' * 64}}, [failed])[1]
        self.assertEqual((mig['status'], mig['operatorCommand']), ('blocked', None))

    def test_receipt_not_delivered(self):
        mig, cut, d = self.migrate_with([], state='migrated')
        self.assertEqual((mig['status'], cut['status']), ('interrupted', 'blocked'))
        self.assertTrue(mig['statusWords'].startswith('receipt not delivered: the placement shows migrated'))
        self.assertTrue(mig['operatorCommand'].startswith('sudo isle storage migrate --dataset apt-public-repo '))
        self.assertIn('receipt not delivered', cut['statusWords'])
        self.assertIsNone(cut['operatorCommand'])
        # a failed receipt is not a finished one: still not delivered
        mig, _, _ = self.migrate_with([{'ok': False, 'attempt': 1}], state='migrated')
        self.assertEqual(mig['status'], 'interrupted')
        for state in ('cutover', 'hosting'):        # past cutover a migrate cannot be typed again, so no command
            mig, cut, _ = self.migrate_with([], state=state)
            self.assertEqual((mig['status'], mig['operatorCommand'], cut['status']), ('interrupted', None, 'succeeded'))
            self.assertIn('the placement shows %s' % state, mig['statusWords'])
        # every status is one the contract names
        self.assertLessEqual({mig['status'], cut['status']}, {'planned', 'blocked', 'running', 'succeeded', 'failed', 'interrupted'})

    def test_attach(self):
        plan = {'id': PID, 'revision': 2, 'items': [item()]}
        media = {'ok': True, 'plan': plan}
        before = copy.deepcopy(plan)
        sp.attach_planned_actions(media, Fake([{'name': 'a', 'agent_mode': 'remote'}, {'name': 'isle-core', 'agent_mode': 'core'}]))
        self.assertEqual(len(media['plannedActions']), 3)
        self.assertEqual(media['plan'], before)
        media = {'plan': plan}
        sp.attach_planned_actions(media, Fake([]))
        self.assertEqual(media['plannedActions'], [])
        self.assertIn('plannedActionsError', media)
        media = {'plan': plan}
        sp.attach_planned_actions(media, object())
        self.assertEqual(media['plannedActions'], [])
        self.assertIn('plannedActionsError', media)
        media = {'plan': {'items': [{'kind': 'task'}]}}
        sp.attach_planned_actions(media, object())
        self.assertEqual(media['plannedActions'], [])
        self.assertNotIn('plannedActionsError', media)

    def save_two(self, store, new_items):
        old = self.base_items()
        first = store.save({'revision': 0, 'title': 'T', 'items': old})
        return store.save({'revision': first['revision'], 'id': first['id'], 'title': 'T', 'items': new_items})

    def base_items(self):
        mk = lambda i, app, dev: dict(id=i, device=dev, title=app, app=app, kind='polari', state='existing', access='frequent')
        return [mk('aptrepo', 'aptrepo', 'isle-core'), mk('other', 'other', 'isle-core'), mk('keep', 'keep', 'isle-core')]

    def test_removal_suppression(self):
        # stm-2c: a dropped storage source is no longer auto-removed, it is refused (receipt-gated, Phase A).
        keep = self.base_items()[2]
        with tempfile.TemporaryDirectory() as d:
            store = PlanStore(Path(d) / 'p.json')
            it = item()
            it['storage']['source']['apps'] = ['aptrepo']
            with self.assertRaisesRegex(ValueError, 'removal refused: .*aptrepo on isle-core'):
                self.save_two(store, [it, keep])
        with tempfile.TemporaryDirectory() as d:
            store = PlanStore(Path(d) / 'p.json')
            old = self.base_items()
            old.append(dict(id='host', device='isle-core', title='h', app='isle-content-host', kind='polari', state='existing', access='frequent'))
            first = store.save({'revision': 0, 'title': 'T', 'items': old})
            with self.assertRaisesRegex(ValueError, 'removal refused: .*isle-content-host on isle-core'):
                store.save({'revision': first['revision'], 'id': first['id'], 'title': 'T', 'items': [item(), old[2]]})

    def test_no_suppression_cases(self):
        keep = self.base_items()[2]
        with tempfile.TemporaryDirectory() as d:  # no source.apps
            out = self.save_two(PlanStore(Path(d) / 'p.json'), [item(), keep])
            self.assertEqual(sorted(r['app'] for r in out['removals']), ['aptrepo', 'other'])
        with tempfile.TemporaryDirectory() as d:  # apps listed but origin device differs from where app lived
            it = item()
            it['storage']['source']['apps'] = ['aptrepo']
            old = self.base_items()
            old[0]['device'] = 'econ-core'
            store = PlanStore(Path(d) / 'p.json')
            first = store.save({'revision': 0, 'title': 'T', 'items': old})
            out = store.save({'revision': first['revision'], 'id': first['id'], 'title': 'T', 'items': [it, old[2]]})
            self.assertEqual(sorted(r['app'] for r in out['removals']), ['aptrepo', 'other'])
        with tempfile.TemporaryDirectory() as d:  # no storage item at all
            out = self.save_two(PlanStore(Path(d) / 'p.json'), [keep])
            self.assertEqual(sorted(r['app'] for r in out['removals']), ['aptrepo', 'other'])

    def test_suppresses_removal_function(self):
        it = validate(self.plan([dict(item(), **{})]))['items'][0]
        self.assertFalse(sp.suppresses_removal([it], 'aptrepo', 'isle-core'))
        self.assertTrue(sp.suppresses_removal([it], 'isle-content-host', 'isle-core'))
        self.assertFalse(sp.suppresses_removal([it], 'isle-content-host', 'elsewhere'))
        self.assertFalse(sp.suppresses_removal([{'kind': 'task', 'app': 'x', 'originDevice': 'isle-core'}], 'x', 'isle-core'))

    def test_category_round_trip(self):
        from islemesh.objects.islemesh.IsleCatalogEntry import IsleCatalogEntry
        self.assertEqual(IsleCatalogEntry(name='x').category, '')
        self.assertEqual(IsleCatalogEntry(name='x', category='storage').category, 'storage')


if __name__ == '__main__':
    unittest.main()
