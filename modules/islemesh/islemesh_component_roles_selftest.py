import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('roles', Path(__file__).parent/'custom/islemesh_roles.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class RolesTests(unittest.TestCase):
    def test_split_devices_and_arbitrary_names(self):
        apps=[dict(name='ui',device_name='a',modes=['polari-role:frontend']),dict(name='compute',device_name='b',modes=['polari-role:backend','modules:islemesh,electronics'])]
        result=r.polari_inventory(apps,[])
        self.assertTrue(result['minimum_deployment_present'])
        self.assertFalse(result['health_verified'])
        self.assertEqual(result['instances'][1]['modules'],['islemesh','electronics'])
    def test_frontend_alone_is_incomplete(self):
        result=r.polari_inventory([dict(name='polari',modes=['polari-role:frontend'])],[])
        self.assertEqual(result['missing_roles'],['backend'])
    def test_backend_alone_is_incomplete(self):
        result=r.polari_inventory([dict(name='polari-api',modes=['polari-role:backend'])],[])
        self.assertEqual(result['missing_roles'],['frontend'])
    def test_no_name_only_or_module_only_role_inference(self):
        for app in [dict(name='polari'),dict(name='polari-api'),dict(name='x',modes=['modules:islemesh'])]:
            self.assertEqual(r.component_roles(app,[]),[])
    def test_legacy_service_containers_classify_both_roles(self):
        apps=[dict(name='polari',device_name='a'),dict(name='polari-api',device_name='a')]
        services=[dict(app_name=a['name'],device_name='a',container='prf-isle-'+role) for a,role in zip(apps,['frontend','backend'])]
        self.assertTrue(r.polari_inventory(apps,services)['minimum_deployment_present'])
    def test_multiple_frontends_allowed_and_mocks_excluded(self):
        apps=[dict(name='ui1',modes=['polari-role:frontend']),dict(name='ui2',modes=['polari-role:frontend']),dict(name='api',modes=['polari-role:backend'],is_mock=True)]
        result=r.polari_inventory(apps,[])
        self.assertEqual(result['frontend_count'],2)
        self.assertEqual(result['missing_roles'],['backend'])
    def test_health_is_reserved_diagnostic_only_without_hosted_container(self):
        app=dict(name='health',domain='health.local',device_name='a')
        self.assertTrue(r.is_agent_health(app,[]))
        self.assertFalse(r.is_agent_health(app,[dict(app_name='health',device_name='a',container='custom-health')]))
        self.assertFalse(r.is_agent_health(dict(name='health',domain='health.isle'),[]))

if __name__=='__main__':unittest.main()
