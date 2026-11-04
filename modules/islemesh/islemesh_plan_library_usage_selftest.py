import copy,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from islemesh.custom.islemesh_planning import PlanStore,Conflict
from islemesh.custom.islemesh_plan_safety import violations
from islemesh.custom.islemesh_usage import UsageStore

class LibraryUsage(unittest.TestCase):
 def plan(self):return dict(title='A',revision=0,items=[],removals=[],baselineInitialized=True)
 def test_library_save_inspect_activate_conflict(self):
  with tempfile.TemporaryDirectory() as d:
   s=PlanStore(Path(d)/'plan.json');a=s.save(self.plan());b=s.save(dict(a,title='B'),as_new=True)
   self.assertEqual(s.read()['title'],'A');self.assertFalse(b['active']);self.assertEqual(s.read(b['id'])['title'],'B')
   active=s.activate(b['id'],b['generation'],b['revision']);self.assertEqual(active['title'],'B')
   with self.assertRaises(Conflict):s.activate(a['id'],b['generation'],a['revision'])
   old=copy.deepcopy(active);active['title']='B2';s.save(active)
   self.assertEqual(s.read(b['id'],1)['title'],'B')
   with self.assertRaises(Conflict):s.save(old)
 def test_old_format_migration_and_removals(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'plan.json';old=self.plan();old.update(revision=9,updatedAt='2026-11-02T00:00:00+00:00');p.write_text(json.dumps(old))
   s=PlanStore(p);a=s.read();a['removals']=[dict(app='sample',device='core',title='Sample')];s.save(a)
   self.assertEqual(s.read()['revision'],10);self.assertEqual(s.read('default',9)['removals'],[])
   self.assertEqual(s.read()['removals'][0]['app'],'sample')
 def test_critical_roles_and_moves(self):
  previous={'items':[dict(app=n,device='core',state='existing') for n in ('openwrt','apt','polari','polari-api','sample')]}
  for app in ('openwrt','apt','polari','polari-api'):
   plan=copy.deepcopy(previous);plan['items']=[i for i in plan['items'] if i['app']!=app]
   self.assertTrue(violations(plan,previous),app)
  plan=copy.deepcopy(previous);plan['items'][-1:]=[];self.assertFalse(violations(plan,previous))
  plan=copy.deepcopy(previous);plan['items'][1]['device']='remote';self.assertFalse(violations(plan,previous))
  plan['items'][0]['device']='remote';self.assertTrue(violations(plan,previous))
 def test_running_average_duplicate_and_version_isolation(self):
  with tempfile.TemporaryDirectory() as d:
   store=UsageStore(Path(d)/'usage.json');now=datetime.now(timezone.utc)
   def fact(seconds,value,version='sha256:a'):
    return dict(status='observed',observed_at=(now+timedelta(seconds=seconds)).isoformat(),value=json.dumps({'appUsage':[dict(app='sample',version=version,ramMiB=value,cpus=.2)]}))
   store.ingest('core',fact(-20,100));store.ingest('core',fact(-20,100));store.ingest('core',fact(-10,300));store.ingest('remote',fact(-10,800));store.ingest('core',fact(0,900,'sha256:b'));store.ingest('core',fact(-1000,9999))
   rows=store.for_app('sample');self.assertEqual(len(rows),3)
   m=next(r for r in rows if r['device']=='core' and r['version']=='sha256:a')['metrics']['ramMiB']
   self.assertEqual(m,dict(count=2,mean=200,peak=300))
if __name__=='__main__':unittest.main()
