import json, os, subprocess, sys, time, urllib.request, urllib.error

os.environ.update(DATABASE_PATH='/tmp/dyn3.db', POLARI_LAZY_BOOT='off',
                  POLARI_MODULES='mathshapes,gears',
                  POLARI_MESH_AUTOCONFIG='false')
srv = subprocess.Popen([sys.executable, 'initLocalhostPolariServer.py'],
                       cwd='/repo', stdout=open('/tmp/boot.log', 'w'),
                       stderr=subprocess.STDOUT)

def req(method, path, timeout=60):
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
            return e.code, {'raw': body[:200].decode('utf-8', 'ignore')}
    except Exception as e:
        return None, {'err': str(e)}

for i in range(240):
    code, _ = req('GET', '/api/health', timeout=5)
    if code == 200:
        break
    time.sleep(2)
else:
    print(open('/tmp/boot.log').read()[-3000:]); sys.exit(1)

code, body = req('GET', '/api/gears/types')
n0 = len(body.get('types', []))
print(f'1) boot with gears ON: /api/gears/types -> {code}, {n0} types')
code, body = req('GET', '/GearTypeDefinition')
rows0 = len(body if isinstance(body, list) else body.get('instances', body.get('data', [])))
print(f'   CRUDE /GearTypeDefinition -> {code}, ~{rows0} rows')

code, body = req('POST', '/modules/mathshapes/put-away')
print(f'2) put-away mathshapes (gears depends) -> {code}: '
      f'{body.get("refusal","?")[:90]}')

code, body = req('POST', '/modules/gears/put-away')
print(f'3) put-away gears -> {code}')
print(json.dumps({k: body.get(k) for k in
                  ('classesDeactivated', 'inMemoryRowsFreed',
                   'dbTablesKept', 'tookSeconds')}, indent=1))

code, body = req('GET', '/api/gears/types')
print(f'4) after put-away: /api/gears/types -> {code} (expect 410) — '
      f'{str(body)[:110]}')
code, body = req('GET', '/GearTypeDefinition')
print(f'   CRUDE /GearTypeDefinition -> {code} (expect 410)')
code, _ = req('GET', '/api/health')
print(f'   health -> {code}; ', end='')
code, body = req('GET', '/api/modules/status')
print('gears status:',
      json.dumps((body.get('modules') or {}).get('gears', {}).get('status')))

code, body = req('POST', '/modules/gears/admit', timeout=300)
print(f'5) re-admit gears -> {code}, restored '
      f'{body.get("seededOrRestoredRows")} rows in '
      f'{body.get("tookSeconds")}s, ctor re-run='
      f'{body.get("customEndpointsConstructed")} (expect False — '
      f'falcon routes persisted)')

code, body = req('GET', '/api/gears/types')
n1 = len(body.get('types', []))
print(f'6) after re-admit: /api/gears/types -> {code}, {n1} types '
      f'(boot had {n0})')
print('LIFECYCLE PROOF:', 'PASS' if n1 == n0 and n0 > 0 else 'FAIL')
srv.terminate()
