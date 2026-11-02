import tempfile
import unittest
from pathlib import Path
from islemesh.custom.islemesh_planning import PlanStore, Conflict, validate

class Planning(unittest.TestCase):
    def plan(self):
        return {'revision':0,'title':'Electronics','items':[dict(id='a',device='econ-core',title='Bridge',kind='polari',state='planned',access='frequent',app='',notes='',volume='/',ramMiB=None,diskMiB=0,cpus=1)]}
    def test_persistence_and_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'plan.json';store=PlanStore(p);self.assertEqual(store.read()['revision'],0)
            stored=store.save(self.plan());self.assertEqual(PlanStore(p).read(),stored)
            with self.assertRaises(Conflict):store.save(self.plan())
            self.assertIsNone(stored['items'][0]['ramMiB']);self.assertEqual(stored['items'][0]['diskMiB'],0)
            stored['items'][0]['state']='existing';self.assertEqual(store.save(stored)['revision'],2)
    def test_cost_and_device_validation(self):
        for value in (-1,True,float('nan'),float('inf'),'2048'):
            p=self.plan();p['items'][0]['ramMiB']=value
            with self.assertRaises(ValueError):validate(p)
        p=self.plan();p['items'][0]['device']='x; reboot'
        with self.assertRaises(ValueError):validate(p)
    def test_invalid_items_and_duplicates(self):
        p=self.plan();p['items']*=2
        with self.assertRaises(ValueError):validate(p)
        p=self.plan();p['items'][0]['kind']='catalog'
        with self.assertRaises(ValueError):validate(p)
    def test_missing_storage_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(OSError):PlanStore(Path(d)/'missing'/'plan.json').save(self.plan())
if __name__=='__main__':unittest.main()
