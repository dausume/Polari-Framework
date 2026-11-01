import json
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace as Row
import unittest
from topology.device_resources import resource_ledger,device_inventory

class Reports(unittest.TestCase):
    def manager(self, old=False):
        stamp=(datetime.now(timezone.utc)-timedelta(hours=1 if old else 0)).isoformat()
        facts={k:dict(value=v,status='observed',observed_at=stamp,source='test')
               for k,v in [('resources.memory_available_mib',0),('resources.memory_total_mib',8000),
                           ('resources.logical_cpus',4),('resources.root_disk_free_mib',12000)]}
        return Row(objectTables={
            'IsleDevice':{'d':Row(name='d',router_running=True,capability_evidence_json=json.dumps({'facts':facts}))},
            'InstanceDefinition':{'p':Row(name='p',machine_name='d')},
            'ModuleAssignment':{'m':Row(state='enabled',instance_name='p',module_name='m')},
            'ModuleResourceProfile':{'m':Row(subject_name='m',min_ram_mb=100,min_disk_mb=20,image_mb=400,deps_mb=50,min_threads=1)},
            'IsleApp':{'x':Row(name='x',device_name='d')},
            'IsleCatalogEntry':{'x':Row(name='x',kind='mesh-app')},
        })
    def test_agent_capacity_and_zero_available_are_preserved(self):
        d=device_inventory(self.manager())[0]
        self.assertTrue(d['grants']['known'])
        self.assertEqual(d['reportedAvailability']['availableRamMb']['value'],0)
        self.assertTrue(d['reportedAvailability']['availableRamMb']['fresh'])
    def test_image_storage_not_counted_as_runtime_ram(self):
        d=resource_ledger(self.manager())['devices'][0]
        self.assertEqual(d['consumed']['ramMbTotal'],100)
        self.assertEqual(d['consumed']['diskMbTotal'],470)
        self.assertFalse(d['reservationsEnforced'])
        self.assertEqual({a['kind'] for a in d['appWorkloads']},{'mesh-app','hardware-app'})
    def test_stale_reports_remain_dated_not_fresh(self):
        d=device_inventory(self.manager(old=True))[0]
        self.assertFalse(d['reportedAvailability']['availableRamMb']['fresh'])
    def test_unreported_device_not_fabricated(self):
        d=device_inventory(Row(objectTables={'IsleDevice':{'x':Row(name='x')}}))[0]
        self.assertFalse(d['grants']['known'])
        self.assertEqual(d['reportedAvailability'],{})
if __name__=='__main__':unittest.main()
