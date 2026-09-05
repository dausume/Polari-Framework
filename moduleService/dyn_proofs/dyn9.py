import os,sys,json
os.environ.update(DATABASE_PATH='/tmp/d9.db',POLARI_LAZY_BOOT='off',
  POLARI_MODULES='polariapps,islemesh,mathshapes,aquaponics,plant_morphology,scoring,gears',
  POLARI_INSTANCE_NAME='prf-a',POLARI_MESH_AUTOCONFIG='false')
sys.path.insert(0,'/app'); sys.path.insert(0,'/app/modules')
from objectTreeManagerDecorators import managerObject
mgr=managerObject(hasServer=True,hasDB=True)
import falcon.testing as ft
c=ft.TestClient(mgr.polServer.falconServer)
r=c.simulate_get('/api/topology/devices')
d=r.json
print('DEVICES status',r.status_code,'counts',json.dumps(d.get('counts')))
for dev in (d.get('devices') or [])[:6]:
    g=dev['grants']
    print(f"  {dev['device']:<14} machine={dev['machine']:<12} agent={dev['agentPresent']} "
          f"known={g['known']} threads={g.get('threads')} ramMb={g.get('ramMb')} "
          f"fid={g.get('fidelity')}")
    if dev.get('note'): print(f"      note: {dev['note'][:78]}")
r=c.simulate_get('/api/topology/resource-ledger')
L=r.json
print('LEDGER status',r.status_code)
print('  totals:',json.dumps(L.get('totals')))
for e in (L.get('devices') or [])[:4]:
    print(f"  {e['device']:<14} consumed(threads={e['consumed']['threadsTotal']}, "
          f"ramMb={e['consumed']['ramMbTotal']}, fid={e['consumed']['fidelity']}) "
          f"available={json.dumps(e['available'])}")
    mf=e['consumed']['moduleFootprint']; cf=e['consumed']['containerFootprint']
    print(f"      modules={mf['modules'][:4]} instances={cf['instances'][:3]} "
          f"imageMb={cf['imageAndDepsMb']} unprofiled={e['consumed']['unprofiledModules'][:4]}")
    print(f"      verdict={json.dumps(e['verdict'])[:110]}")
