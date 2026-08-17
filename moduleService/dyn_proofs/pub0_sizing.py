import json, os, subprocess, sys, time, urllib.request, urllib.error
REPO = os.environ.get('PROOF_REPO', '/app')
DEMO = ('topology,islemesh,appstore,polariapps,simulations,techtree,'
        'climate,motors,mathshapes,'
        'matrices,polariNoCode,simSpace,simSpace3D,materialsScience')
os.environ.update(DATABASE_PATH='/tmp/pub0.db', POLARI_LAZY_BOOT='on',
                  POLARI_MODULES=DEMO,
                  POLARI_INSTANCE_NAME='pub-demo',
                  POLARI_MESH_AUTOCONFIG='false')
t0 = time.time()
srv = subprocess.Popen([sys.executable, 'initLocalhostPolariServer.py'], cwd=REPO,
                       stdout=open('/tmp/boot.log', 'w'), stderr=subprocess.STDOUT)

def req(m, p, timeout=60):
    r = urllib.request.Request(f'http://localhost:3000{p}', method=m)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as x:
            body = json.loads(x.read() or b'{}')
            if isinstance(body, list):
                body = body[0] if body and isinstance(body[0], dict) else {}
            return x.status, body
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except Exception: return e.code, {}
    except Exception as e:
        return None, {'err': str(e)}

for i in range(600):
    c, _ = req('GET', '/api/health', timeout=5)
    if c == 200: break
    time.sleep(1)
print(f'CORE ready (health 200) in {time.time()-t0:.1f}s', flush=True)

# wait for lazy phase-2 to finish
for i in range(600):
    c, b = req('GET', '/api/modules/status')
    if c == 200 and b.get('finishedAt'): break
    time.sleep(2)
print(f'secondsToCore={b.get("secondsToCore")} secondsToFull={b.get("secondsToFull")} '
      f'modules={b.get("moduleCount")} online={b.get("onlineCount")} ({b.get("percentOnline")}%)', flush=True)
for name, m in sorted((b.get('modules') or {}).items()):
    dur = (m.get('finished_at') or 0) - (m.get('started_at') or 0)
    print(f'   {name:18} {m.get("status","?"):8} {dur:6.1f}s seeded={m.get("seeded_rows")} '
          f'{("ERR:"+m["error"][:60]) if m.get("error") else ""}', flush=True)

c, si = req('GET', '/system-info')
proc = si.get('process', {}); bp = si.get('bootProfile', {})
print(f'RAM: residentMb={proc.get("residentMb")} peakMb={proc.get("peakMb")}', flush=True)
print(f'bootProfile: {json.dumps(bp)[:400]}', flush=True)

# Q6 gate (a): cheap read-only endpoint costs on THIS constrained box
for ep in ('/modules', '/classInstanceCounts', '/api/apps', '/api/techtree/summary',
           '/api/modules/status', '/system-info'):
    ts = []
    for _ in range(5):
        t1 = time.time(); c, _b = req('GET', ep); ts.append(time.time()-t1)
    print(f'ENDPOINT {ep:24} -> {c} median={sorted(ts)[2]*1000:.0f}ms max={max(ts)*1000:.0f}ms', flush=True)

with open(f'/proc/{srv.pid}/status') as f:
    for line in f:
        if line.split(':')[0] in ('VmRSS', 'VmHWM'):
            print('SERVER ' + line.strip(), flush=True)
with open('/sys/fs/cgroup/memory.current') as f:
    print(f'CGROUP memory.current = {int(f.read())/1048576:.0f} MiB', flush=True)
try:
    with open('/sys/fs/cgroup/memory.peak') as f:
        print(f'CGROUP memory.peak = {int(f.read())/1048576:.0f} MiB', flush=True)
except Exception:
    pass
import os as _os
print(f'sqlite DB size = {_os.path.getsize("/tmp/pub0.db")/1048576:.1f} MiB', flush=True)
srv.terminate()
print('PUB0 MEASURE: DONE', flush=True)
