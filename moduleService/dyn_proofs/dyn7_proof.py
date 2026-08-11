import json, os, subprocess, sys, time, urllib.request, urllib.error
REPO=os.environ.get('PROOF_REPO','/app')
os.environ.update(DATABASE_PATH='/tmp/dyn7.db', POLARI_LAZY_BOOT='off',
                  POLARI_MODULES='polariapps,appstore,islemesh,mathshapes,'
                                 'aquaponics,plant_morphology,scoring,gears',
                  POLARI_INSTANCE_NAME='prf-a',
                  POLARI_MESH_AUTOCONFIG='false')
srv=subprocess.Popen([sys.executable,'initLocalhostPolariServer.py'],cwd=REPO,
                     stdout=open('/tmp/boot.log','w'),stderr=subprocess.STDOUT)
def req(m,p,body=None,timeout=180):
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
for i in range(400):
    c,_=req('GET','/api/health',timeout=5)
    if c==200: break
    time.sleep(1)
print('booted prf-a with gears live')

c,b=req('POST','/api/topology/module-move/plan',
        {'module':'gears','to':'prf-b'})
print(f'1) PLAN (no peer yet) -> ok={b.get("ok")}')
for r in b.get('refusals',[]): print(f'   refusal: {r}')
print(f'   consent: {json.dumps(b.get("consent"))}')

# register prf-b as an addressable peer, then re-plan
c,pn=req('POST','/PeerNode',{'name':'prf-b',
                             'base_url':'https://api.prf-b.test'})
c,b=req('POST','/api/topology/module-move/plan',
        {'module':'gears','to':'prf-b'})
print(f'2) PLAN (peer registered) -> ok={b.get("ok")} '
      f'rowsOnSource={b.get("rowsOnSource")} classes={len(b.get("classes") or [])}')
for r in b.get('refusals',[]): print(f'   refusal: {r}')
for s in b.get('steps',[]):
    print(f'   step {s["step"]} [{s["performedBy"]}] {s["act"]}')
    print(f'      {s["call"][:96]}')

c,b=req('POST','/api/topology/module-move/local-half',
        {'module':'gears','to':'prf-b'})
print(f'3) local-half WITHOUT dataMoved -> {c}: {b.get("refusal","")[:90]}')

c,b=req('POST','/api/topology/module-move/local-half',
        {'module':'gears','to':'prf-b','dataMoved':True})
print(f'4) local-half WITH dataMoved -> {c} in {b.get("tookSeconds")}s; '
      f'row={json.dumps(b.get("assignmentRow"))}')
c,b=req('GET','/api/gears/types')
print(f'5) /api/gears/types on the loser -> {c} (expect 410)')
c,b=req('GET','/api/refs/directory')
g=b.get('classes',{}).get('GearTypeDefinition')
print(f'6) directory says: {json.dumps(g)}')
c,b=req('GET','/api/topology/placement')
print(f'7) placement: live has gears? {"gears" in (b.get("liveModules") or [])}; '
      f'declared gears={b.get("declared",{}).get("gears")}')
print('DYN-7 PROOF: PASS' if g and not g.get('servedHere') else 'DYN-7: check')
srv.terminate()
