"""Framework-free evaluator and API contract tests. No runtime/network mutations."""
import ast
from datetime import datetime, timezone, timedelta
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location('capabilities', ROOT/'custom/islemesh_capabilities.py')
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
role_spec = importlib.util.spec_from_file_location('roles', ROOT/'custom/islemesh_roles.py')
roles = importlib.util.module_from_spec(role_spec)
role_spec.loader.exec_module(roles)
NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)

def device(name='a', **facts):
    return {'name': name, 'capability_evidence': {'schema_version': 1, 'facts': {
        dep: {'status': 'observed', 'source': 'fixture-probe', 'observed_at': NOW.isoformat(), 'value': value}
        for dep, value in facts.items()}}}

def requirement(dep='docker', scope='device', **kw):
    return dict(dep=dep, scope=scope, check='present', **kw)

def descriptor(*needs, **kw):
    return dict(schema_version=1, kind='mesh-app', action='host', complete=True,
                needs=list(needs) or [requirement()], **kw)

class EvaluatorTests(unittest.TestCase):
    def evaluate(self, desc, target, devices=None):
        return cap.evaluate_target(desc, target, devices or [target], NOW)

    def test_ready_requires_complete_current_evidence(self):
        self.assertEqual(self.evaluate(descriptor(), device(docker=True))['status'], 'ready')
    def test_missing_report_unknown(self):
        self.assertEqual(self.evaluate(descriptor(), {'name':'a','agent_present':True})['status'], 'unknown')
    def test_incomplete_closure_never_ready(self):
        desc=descriptor();desc['complete']=False
        self.assertEqual(self.evaluate(desc, device(docker=True))['status'],'unknown')
    def test_missing_descriptor_unknown(self):
        self.assertEqual(self.evaluate(None,device(docker=True))['status'],'unknown')
    def test_mock_never_ready(self):
        d=device(docker=True);d['is_mock']=True
        self.assertEqual(self.evaluate(descriptor(),d)['status'],'unknown')
    def test_freshness_not_device_last_seen(self):
        d=device(docker=True);d['last_seen']=NOW.isoformat()
        d['capability_evidence']['facts']['docker']['observed_at']=(NOW-timedelta(minutes=6)).isoformat()
        self.assertEqual(self.evaluate(descriptor(),d)['status'],'unknown')
        self.assertEqual(self.evaluate(descriptor(),d)['last_reported_status'],'ready')
    def test_old_failure_retains_reason_and_timestamp(self):
        d=device(docker=False)
        stamp=(NOW-timedelta(days=2)).isoformat()
        d['capability_evidence']['facts']['docker']['observed_at']=stamp
        result=self.evaluate(descriptor(requirement(failure='policy-restricted')),d)
        self.assertEqual(result['last_reported_status'],'policy-restricted')
        self.assertEqual(result['checks'][0]['observed_at'],stamp)
        self.assertTrue(result['revalidation_required'])
    def test_old_shared_provider_retains_result_without_current_readiness(self):
        d=device(docker=True)
        d['capability_evidence']['facts']['docker']['observed_at']=(NOW-timedelta(days=1)).isoformat()
        result=self.evaluate(descriptor(requirement(scope='isle')),d)
        self.assertEqual(result['status'],'unknown')
        self.assertEqual(result['last_reported_status'],'ready')
        self.assertEqual(result['providers']['docker'],[])

    def test_future_and_naive_dates_unknown(self):
        for value in [(NOW+timedelta(minutes=2)).isoformat(), '2026-10-30T00:00:00']:
            d=device(docker=True);d['capability_evidence']['facts']['docker']['observed_at']=value
            self.assertEqual(self.evaluate(descriptor(),d)['status'],'unknown')
    def test_probe_error_not_missing_capability(self):
        d=device(docker=True);d['capability_evidence']['facts']['docker']['status']='error'
        self.assertEqual(self.evaluate(descriptor(),d)['status'],'unknown')
    def test_failed_observation_returns_specific_reason(self):
        for state in cap.FAILURES:
            self.assertEqual(self.evaluate(descriptor(requirement(failure=state)),device(docker=False))['status'],state)
    def test_types_not_coerced(self):
        for value in ['true',1]:
            self.assertEqual(self.evaluate(descriptor(),device(docker=value))['status'],'unknown')
    def test_minimum_resource(self):
        desc=descriptor(dict(dep='ram',scope='device',check='min',value=512,failure='resource-limited'))
        self.assertEqual(self.evaluate(desc,device(ram=256))['status'],'resource-limited')
        self.assertEqual(self.evaluate(desc,device(ram=512))['status'],'ready')
        self.assertEqual(self.evaluate(desc,device(ram=True))['status'],'unknown')
    def test_remote_polari_satisfies_shared_use_requirement(self):
        desc=descriptor(requirement('dns'),requirement('electronics.frontend','isle'))
        desc['action']='use';desc['kind']='polari-app'
        client=device('client',dns=True);host=device('polari',**{'electronics.frontend':True})
        self.assertEqual(self.evaluate(desc,client,[client,host])['status'],'ready')
    def test_colocated_dependencies_cannot_be_split(self):
        desc=descriptor(requirement('node','isle',group='runtime'),requirement('modules','isle',group='runtime'))
        a=device('a',node=True,modules=False);b=device('b',node=False,modules=True)
        self.assertEqual(self.evaluate(desc,a,[a,b])['status'],'needs-setup')
    def test_isle_unknown_provider_prevents_unsupported_claim(self):
        desc=descriptor(requirement(failure='unsupported'))
        r=cap.evaluate_isle(desc,[device('a',docker=False),{'name':'b'}],NOW)
        self.assertEqual(r['status'],'unknown')
    def test_isle_unsupported_requires_all_targets(self):
        r=cap.evaluate_isle(descriptor(requirement(failure='unsupported')),[device('a',docker=False),device('b',docker=False)],NOW)
        self.assertEqual(r['status'],'unsupported')
    def test_mixed_blockers_do_not_invent_resource_failure(self):
        desc=descriptor(requirement('policy',failure='policy-restricted'),requirement('architecture',failure='unsupported'))
        report=cap.evaluate_isle(desc,[device('a',policy=False,architecture=True),device('b',policy=True,architecture=False)],NOW)
        self.assertEqual(report['status'],'blocked')
    def test_empty_isle_unknown(self):
        self.assertEqual(cap.evaluate_isle(descriptor(),[],NOW)['status'],'unknown')
    def test_vm_and_bridge_require_realization(self):
        desc=descriptor();desc['kind']='hardware-app'
        self.assertEqual(self.evaluate(desc,device(docker=True))['status'],'unknown')
        desc['realization']='bridge'
        self.assertEqual(self.evaluate(desc,device(docker=True))['status'],'ready')
    def test_duplicate_resource_needs_refused(self):
        desc=descriptor(requirement(),requirement())
        self.assertEqual(self.evaluate(desc,device(docker=True))['status'],'unknown')
    def test_numeric_bool_schema_and_nan_refused(self):
        for bad in [{'schema_version':True,'facts':{}}, {'schema_version':1,'facts':{'x':{'value':float('nan'),'status':'observed','source':'probe','observed_at':NOW.isoformat()}}}]:
            with self.assertRaises(ValueError):cap.validate_evidence(bad)

# Exercise the actual route methods with in-memory tables instead of booting DB,
# server, plugins or agents. Persistence/migration is a separate integration gate.
methods={'_planning_requirements','_base_requirements_for','on_get_graph','_bridge_catalog_entries','_capability_devices','_requirements_for','on_get_devices','on_get_catalog_targets','on_get_gaps','on_post_ingest_device'}
tree=ast.parse((ROOT/'islemesh_api.py').read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='IsleMeshAPI')
cls.bases=[];cls.decorator_list=[];cls.body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in methods]
ns=dict(component_roles=roles.component_roles,is_agent_health=roles.is_agent_health,polari_inventory=roles.polari_inventory,__file__=str(ROOT/'islemesh_api.py'),json=json,datetime=datetime,timezone=timezone,ACTIONS=cap.ACTIONS,MAX_AGE_SECONDS=cap.MAX_AGE_SECONDS,
        validate_evidence=cap.validate_evidence,evaluate_isle=cap.evaluate_isle,
        test_requirement=lambda entry,action:None,
        _now_iso=lambda:NOW.isoformat(),CONNECTIVITY_MODES=[],AGENT_MODES=[],_DEVICE_CLASSES=())
exec(compile(ast.Module(body=[cls],type_ignores=[]),'islemesh_api.py','exec'),ns)

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.api=ns['IsleMeshAPI']();self.response=SimpleNamespace()
        self.tables={'IsleDevice':{},'IsleCatalogEntry':{}}
        self.api._table=lambda name:self.tables.get(name,{})
        self.api.manager=SimpleNamespace(objectTables=self.tables)
        self.api._any_mock=lambda:False
        self.api._refuse=lambda response,error,status='400 Bad Request':setattr(response,'media',{'ok':False,'error':error})
        self.request=SimpleNamespace(get_param=lambda name:None)
    def test_app_profiles_extend_existing_host_requirements(self):
        self.api._base_requirements_for=lambda entry,action: descriptor()
        self.tables['ModuleResourceProfile']={'x':SimpleNamespace(subject_kind='isle-app',subject_name='isle-app:x',min_ram_mb=256,min_disk_mb=20,image_mb=100,deps_mb=10,min_threads=1)}
        result=self.api._requirements_for({'name':'x'},'host')
        needs={n['dep']:n for n in result['needs']}
        self.assertEqual(needs['resources.memory_available_mib']['value'],256)
        self.assertEqual(needs['resources.root_disk_free_mib']['value'],130)
        self.assertEqual(needs['resources.memory_available_mib']['failure'],'resource-limited')
        self.tables['ModuleResourceProfile']['x'].min_ram_mb=-1
        self.assertIsNone(self.api._requirements_for({'name':'x'},'host'))

    def test_planning_profile_minima_and_missing_values(self):
        e={'name':'x','service':'worker'}
        self.assertFalse(self.api._planning_requirements(e)['complete'])
        self.tables['ModuleResourceProfile']={'x':SimpleNamespace(name='worker-profile',subject_kind='engine',subject_name='worker',min_ram_mb=100,min_disk_mb=20,image_mb=50,deps_mb=10,min_threads=1)}
        result=self.api._planning_requirements(e)
        self.assertEqual(result['minimum'],dict(ramMiB=100,diskMiB=80,cpus=1))
        self.assertTrue(result['complete'])
        self.assertEqual(result['source'],'ModuleResourceProfile:worker-profile')
        self.tables['ModuleResourceProfile']['x'].min_ram_mb=float('nan')
        self.assertIsNone(self.api._planning_requirements(e)['minimum']['ramMiB'])
        self.assertFalse(self.api._planning_requirements(e)['complete'])

    def test_graph_preserves_app_kinds_and_polari_runtime_role(self):
        self.tables['IsleDevice']={'core':SimpleNamespace(name='core',agent_present=True,router_running=True)}
        self.tables['IsleApp']={
            'p':SimpleNamespace(name='polari',device_name='core',modes_json='["modules:islemesh"]'),
            'w':SimpleNamespace(name='whoami',device_name='core'),
            'b':SimpleNamespace(name='bridge',device_name='core'),
            'real-bridge':SimpleNamespace(name='uno_core_demo',device_name='core'),
        }
        self.tables['IsleCatalogEntry']={
            'p':SimpleNamespace(name='polari',kind='polari-app'),
            'w':SimpleNamespace(name='whoami',kind='mesh-app'),
            'b':SimpleNamespace(name='bridge',kind='hardware-app',realization='bridge'),
        }
        self.api.on_get_graph(self.request,self.response)
        nodes={n['id']:n for n in self.response.media['nodes']}
        self.assertEqual(nodes['app:polari']['app_kind'],'polari-instance')
        self.assertEqual(nodes['app:whoami']['app_kind'],'mesh-app')
        self.assertEqual(nodes['app:bridge']['realization'],'bridge')
        self.assertEqual(nodes['app:uno_core_demo']['realization'],'bridge')
        self.assertEqual(nodes['app:uno_core_demo']['classification_source'],'Polari app manifest')
        self.assertEqual(nodes['router:core']['app_kind'],'hardware-app')
        self.assertEqual(len([n for n in nodes.values() if n['kind']=='device']),1)

    def test_graph_component_roles_and_agent_diagnostics(self):
        self.tables['IsleDevice']={'core':SimpleNamespace(name='core',agent_present=True)}
        self.tables['IsleApp']={n:SimpleNamespace(name=n,device_name='core',domain=d) for n,d in [('polari','polari.isle'),('polari-api','api.polari.isle'),('health','health.local'),('sample','sample.isle')]}
        self.tables['IsleAppService']={n:SimpleNamespace(app_name=n,device_name='core',container=c) for n,c in [('polari','prf-isle-frontend'),('polari-api','prf-isle-backend'),('sample','isle-sample-app')]}
        self.api.on_get_graph(self.request,self.response)
        data=self.response.media;nodes={n['id']:n for n in data['nodes']}
        self.assertNotIn('app:health',nodes)
        self.assertEqual(nodes['proxy:core']['diagnostics'][0]['path'],'/health')
        self.assertEqual(nodes['app:polari']['component_roles'],['frontend'])
        self.assertEqual(nodes['app:polari-api']['component_roles'],['backend'])
        self.assertEqual(nodes['app:sample']['app_kind'],'mesh-app')
        self.assertTrue(data['polari']['minimum_deployment_present'])
        self.assertNotIn('health',[w['name'] for d in data['resources']['devices'] for w in d['appWorkloads']])

    def test_graph_distinguishes_reported_interfaces_from_inferred_paths(self):
        self.tables['IsleDevice'] = {
            'core': SimpleNamespace(name='core',agent_present=True,router_running=True,last_seen=NOW.isoformat()),
            'remote': SimpleNamespace(name='remote',agent_present=True,router_running=False,last_seen=NOW.isoformat()),
        }
        self.tables['IsleUplink'] = {
            'eth': SimpleNamespace(device_name='remote',interface='eth0',kind='ethernet',link_up=True,measured_at=NOW.isoformat()),
            'wifi': SimpleNamespace(device_name='remote',interface='wlan0',kind='wifi',link_up=True,measured_at=NOW.isoformat()),
        }
        self.api.on_get_graph(self.request,self.response)
        graph=self.response.media
        segment=next(n for n in graph['nodes'] if n['kind']=='segment')
        self.assertEqual(segment['detection'],'inferred')
        self.assertNotIn('(switch)',segment['label'])
        remote=next(n for n in graph['nodes'] if n['id']=='device:remote')
        self.assertEqual(len(remote['uplinks']),2)
        physical=[l for l in graph['links'] if l['kind']=='l2']
        self.assertEqual(len(physical),1) # unrelated Wi-Fi is not an Isle link
        self.assertEqual(physical[0]['medium'],'ethernet')
        self.assertEqual(physical[0]['reported_at'],NOW.isoformat())
        dns=[l for l in graph['links'] if l['kind']=='dns']
        self.assertEqual(len(dns),2)
        self.assertTrue(all(l['source']=='router:core' and l['detection']=='inferred' for l in dns))
        self.tables['IsleDevice']['remote'].router_running=True
        self.api.on_get_graph(self.request,self.response)
        self.assertFalse(any(l['kind']=='dns' for l in self.response.media['links']))

    def test_bridge_catalog_uses_manifest_and_never_offers_vm_commands(self):
        self.api._instances_of=lambda name:[]
        entries=self.api._bridge_catalog_entries()
        demo=next(e for e in entries if e['name']=='uno_core_demo')
        self.assertEqual(demo['realization'],'bridge')
        self.assertEqual(demo['requires_tier'],'member')
        self.assertFalse(demo['install_plan']['ok'])
        self.assertEqual(demo['install_plan']['steps'],[])
        self.assertFalse(any(e['name']=='bridge-engines' for e in entries))
    def test_devices_does_not_promote_legacy_agent_flag(self):
        self.tables['IsleDevice']['a']=SimpleNamespace(name='a',agent_present=True,last_seen=NOW.isoformat())
        self.api.on_get_devices(self.request,self.response)
        self.assertIsNone(self.response.media['devices'][0]['capability_evidence'])
    def test_descriptor_action_and_kind_must_match(self):
        self.tables['IsleCatalogEntry']['x']=SimpleNamespace(name='x',requirements_json=json.dumps({'host':descriptor()}))
        self.assertIsNotNone(self.api._requirements_for({'name':'x','kind':'mesh-app'},'host'))
        self.assertIsNone(self.api._requirements_for({'name':'x','kind':'polari-app'},'host'))
        self.assertIsNone(self.api._requirements_for({'name':'x','kind':'mesh-app'},'use'))
    def test_targets_and_gaps_use_same_evaluator(self):
        entry={'name':'x','kind':'mesh-app'}
        self.api.on_get_catalog_entry=lambda req,res,name:setattr(res,'media',{'ok':True,'entry':entry})
        self.api.on_get_catalog=lambda req,res:setattr(res,'media',{'entries':[entry]})
        self.tables['IsleDevice']['a']=SimpleNamespace(name='a',agent_present=True)
        self.api.on_get_catalog_targets(self.request,self.response,'x');target=self.response.media
        self.api.on_get_gaps(self.request,self.response)
        self.assertEqual(target['status'],self.response.media['entries'][0]['status'])
        self.assertEqual(target['status'],'unknown')
    def test_unknown_action_rejected(self):
        self.request.get_param=lambda name:'destroy'
        self.api.on_get_catalog_targets(self.request,self.response,'x')
        self.assertFalse(self.response.media['ok'])
    def test_invalid_report_rejected_before_device_mutation(self):
        self.api._payload=lambda req:({'capability_evidence':{'schema_version':1,'facts':[]}},None)
        self.api._ingest_header=lambda payload,res:('a',False)
        self.api._upsert_device=lambda *a,**kw:self.fail('invalid evidence mutated device')
        self.api.on_post_ingest_device(self.request,self.response)
        self.assertFalse(self.response.media['ok'])
    def test_capability_only_report_preserves_uplinks(self):
        self.api._payload=lambda req:({'capability_evidence':device(docker=True)['capability_evidence']},None)
        self.api._ingest_header=lambda payload,res:('a',False)
        self.api._upsert_device=lambda *a,**kw:None
        self.api._replace_device_rows=lambda *a:self.fail('capability report erased topology')
        self.api._receipt=lambda *a:SimpleNamespace(name='receipt')
        self.api.on_post_ingest_device(self.request,self.response)
        self.assertTrue(self.response.media['ok'])
    def test_explicit_empty_uplinks_clear_topology(self):
        self.api._payload=lambda req:({'uplinks':[]},None)
        self.api._ingest_header=lambda payload,res:('a',False)
        self.api._upsert_device=lambda *a,**kw:None
        cleared=[]
        self.api._replace_device_rows=lambda *a:cleared.append(a)
        self.api._receipt=lambda *a:SimpleNamespace(name='receipt')
        self.api.on_post_ingest_device(self.request,self.response)
        self.assertEqual(len(cleared),1)
    def test_invalid_uplinks_refused_before_device_mutation(self):
        for value in (None,{},'invalid'):
            self.api._payload=lambda req:({'uplinks':value},None)
            self.api._ingest_header=lambda payload,res:('a',False)
            self.api._upsert_device=lambda *a,**kw:self.fail('invalid topology mutated device')
            self.api.on_post_ingest_device(self.request,self.response)
            self.assertFalse(self.response.media['ok'])

    def test_legacy_ingest_does_not_refresh_capability_timestamp(self):
        self.api._payload=lambda req:({'facts':{}},None)
        self.api._ingest_header=lambda payload,res:('a',False)
        saved={}
        self.api._upsert_device=lambda *a,**kw:saved.update(kw)
        self.api._replace_device_rows=lambda *a:None
        self.api._receipt=lambda *a:SimpleNamespace(name='receipt')
        self.api.on_post_ingest_device(self.request,self.response)
        self.assertIsNone(saved['capability_received_at'])
        self.assertIsNone(saved['capability_evidence_json'])

class BuiltinRequirementsTests(unittest.TestCase):
    def test_bounded_descriptors_validate_and_do_not_guess_other_apps(self):
        spec=importlib.util.spec_from_file_location('test_requirements', ROOT/'custom/islemesh_test_requirements.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for name,kind,action in [('whoami','mesh-app','use'),('polari','polari-instance','use'),('board-engines','mesh-app','host')]:
            value=module.test_requirement({'name':name,'kind':kind},action)
            cap.validate_requirements(value)
            if name=='board-engines':self.assertFalse(value['complete'])
        self.assertIsNone(module.test_requirement({'name':'other','kind':'mesh-app'},'host'))
        self.assertIsNone(module.test_requirement({'name':'whoami','kind':'hardware-app'},'use'))

if __name__=='__main__':unittest.main()
