"""dyn-4 proof: a module ABSENT at boot is fetched into the running
server and admitted. Simulates the fetch by staging the real gears
code in a holding area, hiding it from boot, and pointing the
'file'-kind fetch at it."""
import json, os, shutil, subprocess, sys, time, urllib.request, urllib.error

REPO = os.environ.get('PROOF_REPO', '/repo')
os.makedirs('/tmp/src', exist_ok=True)
shutil.copytree(f'{REPO}/modules/gears', '/tmp/src/gears',
                dirs_exist_ok=True)
shutil.rmtree(f'{REPO}/modules/gears')          # ABSENT at boot
print('staged gears at /tmp/src/gears; modules/gears removed')

os.environ.update(DATABASE_PATH='/tmp/dyn4.db', POLARI_LAZY_BOOT='off',
                  POLARI_MODULES='mathshapes,gears',
                  POLARI_INSTANCE_NAME='prf-test',
                  POLARI_MESH_AUTOCONFIG='false')
srv = subprocess.Popen([sys.executable, 'initLocalhostPolariServer.py'],
                       cwd=REPO, stdout=open('/tmp/boot.log','w'),
                       stderr=subprocess.STDOUT)

def req(method, path, body=None, timeout=120):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f'http://localhost:3000{path}',
                               data=data, method=method,
                               headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except Exception: return e.code, {}
    except Exception as e:
        return None, {'err': str(e)}

for i in range(240):
    code, _ = req('GET', '/api/health', timeout=5)
    if code == 200: break
    time.sleep(2)
print(f'booted (~{2*i}s) WITHOUT gears code')
print('boot log gears lines:',
      [l.strip()[:120] for l in open('/tmp/boot.log')
       if 'gears' in l.lower()][:4])
code, mb = req('GET', '/modules')
grow = [m for m in (mb.get('modules') or [])
        if m.get('id')=='gears' or m.get('name')=='gears']
print('  /modules gears row:', json.dumps(grow)[:200])

code, body = req('GET', '/api/gears/types')
print(f'1) BEFORE: /api/gears/types -> {code} (expect 404)')
code, body = req('POST', '/modules/gears/admit')
print(f'2) plain admit (code absent) -> {code}: {json.dumps(body)[:220]}')
code, body = req('POST', '/modules/gears/fetch-admit',
                 {'sourceKind': 'peer', 'sourceRef': 'x'})
print(f'3) fetch-admit peer source -> {code}: '
      f'{body.get("refusal","")[:80]}')

t0 = time.time()
code, body = req('POST', '/modules/gears/fetch-admit',
                 {'sourceKind': 'file', 'sourceRef': '/tmp/src/gears'},
                 timeout=300)
print(f'4) fetch-admit file source -> {code} in {time.time()-t0:.1f}s')
print('   ', json.dumps({k: body.get(k) for k in
      ('classes','seededOrRestoredRows','customEndpointsConstructed',
       'assignmentRow')})[:300])
print('   fetch:', json.dumps(body.get('fetch'))[:150])

code, body = req('GET', '/api/gears/types')
n = len(body.get('types', []))
print(f'5) AFTER: /api/gears/types -> {code} with {n} types')
code, body = req('GET', '/GearTypeDefinition')
print(f'   CRUDE /GearTypeDefinition -> {code}')
code, body = req('GET', '/api/modules/status')
p = body.get('placement', {})
print(f'6) placement: live={p.get("liveModules")} '
      f'declared={p.get("declared")}')
print('DYN-4 PROOF:', 'PASS' if n == 8 else f'FAIL (types={n})')
srv.terminate()
