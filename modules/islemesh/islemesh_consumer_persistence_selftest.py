"""
@module islemesh.islemesh_consumer_persistence_selftest

Production DB return conventions and repeat-sync recovery for the fix-11 registry consumer, isolated in
memory (Codex follow-up 0006, 2026-11-06): managedDB.saveInstanceInDB returns False on a refused save;
deleteRowsWhere returns -1 when unavailable, 0 when already absent; a retirement whose durable receipt
failed is retried by the next sync and then becomes a no-op.

  PYTHONPATH=.:modules python3 -m islemesh.islemesh_consumer_persistence_selftest
"""
import unittest
from types import SimpleNamespace
from islemesh.custom.islemesh_engines import sync_from_registry, _default_save, _default_delete, _TrackedSave
class Persistence(unittest.TestCase):
 def test_default_save_propagates_database_false(self):
  m=SimpleNamespace(db=SimpleNamespace(saveInstanceInDB=lambda row:False))
  save=_TrackedSave(_default_save(m),'save')
  self.assertFalse(save(SimpleNamespace(name='worker')));self.assertTrue(save.failures)
 def test_default_delete_propagates_unavailable_but_accepts_idempotent_absence(self):
  for count,expected in [(-1,False),(False,False),(0,True),(1,True)]:
   m=SimpleNamespace(db=SimpleNamespace(deleteRowsWhere=lambda *args:count))
   self.assertIs(_default_delete(m)(SimpleNamespace(id='row-id')),expected)
 def test_failed_retirement_record_is_retried(self):
  m=SimpleNamespace(objectTables={},idList=[],objectTyping=[SimpleNamespace(className='EngineProviderBinding')])
  def save(row):m.objectTables.setdefault(type(row).__name__,{})[row.name]=row;return True
  env={'ISLE_CORE_API':'https://api.polari.isle'}
  row={'app':'worker','provides':'board','url':'https://worker.isle'}
  result=sync_from_registry(m,save=save,env=env,fetch=lambda origin:([row],''))
  self.assertTrue(result['bound'])
  def fail_receipt(row):
   if type(row).__name__=='IsleEngine':raise RuntimeError('receipt unavailable')
   return save(row)
  failed=sync_from_registry(m,save=fail_receipt,delete=lambda row:True,env=env,fetch=lambda origin:([],''))
  self.assertFalse(failed['ok']);self.assertFalse(failed['retired']);self.assertTrue(failed['failed'])
  retried=sync_from_registry(m,save=save,delete=lambda row:True,env=env,fetch=lambda origin:([],''))
  self.assertTrue(retried['ok']);self.assertIn('worker@board',retried['retired']);self.assertFalse(retried['failed'])
  again=sync_from_registry(m,save=save,delete=lambda row:True,env=env,fetch=lambda origin:([],''))
  self.assertTrue(again['ok']);self.assertFalse(again['retired'])
if __name__=='__main__':unittest.main()
