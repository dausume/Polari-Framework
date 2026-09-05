import json, os, subprocess, sys, time, urllib.request, urllib.error

os.environ.update(DATABASE_PATH='/tmp/dyn2.db', POLARI_LAZY_BOOT='off',
                  POLARI_MODULES='mathshapes',
                  POLARI_MESH_AUTOCONFIG='false')
srv = subprocess.Popen([sys.executable, 'initLocalhostPolariServer.py'],
                       cwd='/repo', stdout=open('/tmp/boot.log', 'w'),
                       stderr=subprocess.STDOUT)

def req(method, path, timeout=30):
    r = urllib.request.Request(f'http://localhost:3000{path}',
                               method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            return e.code, json.loads(body or b'{}')
        except Exception:
            return e.code, {'raw': body[:120].decode('utf-8', 'ignore')}
    except Exception as e:
        return None, {'err': str(e)}

for i in range(240):
    code, _ = req('GET', '/api/health', timeout=5)
    if code == 200:
        break
    time.sleep(2)
else:
    print(open('/tmp/boot.log').read()[-3000:]); sys.exit(1)
print(f'BOOTED after ~{2*i}s')
for line in open('/tmp/boot.log'):
    if 'Module gating' in line:
        print('GATE:', line.strip()[:200])

code, _ = req('GET', '/api/gears/types')
print(f'BEFORE admit: GET /api/gears/types -> {code} (expect 404)')

code, body = req('POST', '/modules/motors/admit')
print(f'REFUSAL motors (deps): {code} — {body.get("refusal","?")[:100]}')
code, body = req('POST', '/modules/topology/admit')
print(f'REFUSAL topology (core): {code} — {body.get("refusal","?")[:100]}')

t0 = time.time()
code, body = req('POST', '/modules/gears/admit', timeout=300)
print(f'ADMIT gears: {code} in {time.time()-t0:.1f}s')
print(json.dumps({k: body.get(k) for k in
                  ('success', 'classes', 'seededOrRestoredRows',
                   'crudeRoutes', 'customEndpointsConstructed',
                   'envUpdatedProcessLocal', 'tookSeconds')}, indent=1))

code, body = req('GET', '/api/gears/types')
n = len(body.get('types', body) if isinstance(body, (list, dict)) else [])
print(f'AFTER admit: GET /api/gears/types -> {code} with {n} entries')

code, body = req('POST', '/modules/gears/admit')
print(f'RE-ADMIT (idempotent): {code} noop={body.get("noop")}')

code, _ = req('GET', '/api/health')
print(f'health still: {code}')
code, body = req('GET', '/api/modules/status')
print('gears lifecycle row:',
      json.dumps((body.get('modules') or {}).get('gears'))[:220])
srv.terminate()
