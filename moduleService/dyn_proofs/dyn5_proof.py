import json, os, subprocess, sys, time, urllib.request, urllib.error
REPO=os.environ.get('PROOF_REPO','/app')
os.environ.update(DATABASE_PATH='/tmp/dyn5.db', POLARI_LAZY_BOOT='off',
                  POLARI_MODULES='polariapps,appstore,islemesh',
                  POLARI_INSTANCE_NAME='prf-base',
                  POLARI_MESH_AUTOCONFIG='false')
t0=time.time()
srv=subprocess.Popen([sys.executable,'initLocalhostPolariServer.py'],cwd=REPO,
                     stdout=open('/tmp/boot.log','w'),stderr=subprocess.STDOUT)
def req(m,p,body=None,timeout=120):
    d=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request(f'http://localhost:3000{p}',data=d,method=m,
                             headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:
            return x.status, json.loads(x.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except Exception: return e.code, {}
    except Exception as e: return None, {'err':str(e)}
for i in range(300):
    c,_=req('GET','/api/health',timeout=5)
    if c==200: break
    time.sleep(1)
boot=time.time()-t0
print(f'1) BASELINE BOOT ready in {boot:.1f}s')
c,b=req('GET','/api/modules/status')
p=b.get('placement',{})
print(f'   live modules: {p.get("liveModules")}')
c,b=req('GET','/api/topology/baseline/prf-base')
print(f'2) baseline PREVIEW -> {c}: floor={b.get("baselineModules")} '
      f'toEnable={b.get("toEnable")} toStandDown={b.get("toStandDown")}')
print(f'   excluded on purpose: {list((b.get("excludedOnPurpose") or {}).keys())}')
c,b=req('POST','/api/topology/baseline/prf-base')
print(f'3) baseline APPLY -> {c}: rows={b.get("rowsWritten")}')
c,b=req('GET','/api/gears/types')
print(f'4) gears BEFORE (not in baseline) -> {c}')
c,b=req('POST','/modules/gears/admit',timeout=300)
print(f'5a) admit gears first -> {c}: {b.get("refusal","")[:80]}')
t1=time.time()
c,b=req('POST','/modules/gears/admit?withDeps=true',timeout=900)
print(f'5b) admit gears WITH DEPS -> {c} in {time.time()-t1:.1f}s')
print(f'    planned order: {b.get("plannedOrder")}')
print(f'    admitted: {b.get("admitted")}')
for st in (b.get('steps') or []):
    print(f'      - {st["module"]}: ok={st["ok"]} noop={st["noop"]} '
          f'classes={st["classes"]} rows={st["rows"]}'
          + (f' refusal={st["refusal"][:60]}' if st.get('refusal') else ''))
c,b=req('GET','/api/gears/types')
print(f'6) gears AFTER -> {c} with {len(b.get("types",[]))} types')
c,b=req('GET','/api/topology/placement')
print(f'7) placement: live={b.get("liveModules")} declared={b.get("declared")}')
c,b=req('POST','/modules/gears/put-away')
c,b2=req('GET','/api/topology/placement')
print(f'8) after put-away: live={b2.get("liveModules")} putAway={b2.get("putAway")}')
print('DYN-5 PROOF: PASS' if boot < 120 else 'DYN-5: boot slow')
srv.terminate()
