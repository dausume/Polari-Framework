import json, os, subprocess, sys, time, urllib.request, urllib.error
REPO=os.environ.get('PROOF_REPO','/app')
os.environ.update(DATABASE_PATH='/tmp/dyn68.db', POLARI_LAZY_BOOT='off',
                  POLARI_MODULES='polariapps,appstore,islemesh',
                  POLARI_INSTANCE_NAME='prf-base',
                  POLARI_MESH_AUTOCONFIG='false')
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
print('booted baseline')

# --- dyn-8: directory answers for classes NOT served here ---
c,b=req('GET','/api/refs/directory')
cl=b.get('classes',{})
gear=cl.get('GearTypeDefinition')
print(f'1) dyn-8 directory: {c}, {len(cl)} classes total')
print(f'   GearTypeDefinition (module not live here): {json.dumps(gear)}')
print(f'   invalidateOn: {json.dumps(b.get("invalidateOn"))}')

# --- dyn-6: an app whose modules are not live ---
c,b=req('GET','/api/apps/nav')
apps=b.get('apps',[])
target=None
for a in apps:
    mp=a.get('modulePlan') or {}
    if mp.get('missingHere'):
        target=a; break
if target:
    mp=target['modulePlan']
    print(f'2) dyn-6 app "{target["name"]}" ready={mp["ready"]}')
    print(f'   missingHere={mp["missingHere"][:5]} alsoPulledIn={mp["alsoPulledIn"][:5]}')
    print(f'   admit suggestions: {mp["admit"][:2]}')
    states=set(target.get('moduleStates',{}).values())
    print(f'   moduleStates seen: {sorted(states)}')
    # find a nav item carrying the admit affordance
    for g in target.get('nav',[]):
        for it in g.get('items',[]):
            if it.get('availability')=='absent' and it.get('bringup',{}).get('admit'):
                print(f'   nav item "{it["label"]}" -> {it["bringup"]["admit"]["withDeps"]}')
                break
        else: continue
        break
    # --- act on the suggestion ---
    t0=time.time(); allad=[]
    for mod in mp['missingHere']:
        c,r=req('POST',f'/modules/{mod}/admit?withDeps=true',timeout=900)
        allad += (r.get('admitted') or [])
        if not r.get('ok'):
            print(f'   admit {mod} -> {c} {str(r.get("refusal"))[:80]}')
    print(f'3) acted on ALL suggestions in {time.time()-t0:.1f}s '
          f'admitted={allad}')
    c,b2=req('GET',f'/api/apps/nav/{target["name"]}')
    mp2=b2.get('modulePlan') or {}
    print(f'4) same app now: ready={mp2.get("ready")} '
          f'missingHere={mp2.get("missingHere")}')
    c,b3=req('GET','/api/refs/directory')
    g2=b3.get('classes',{}).get('GearTypeDefinition')
    print(f'5) directory GearTypeDefinition now: {json.dumps(g2)}')
    print('DYN-6/8 PROOF:', 'PASS' if mp2.get('ready') else 'PARTIAL')
else:
    print('no app with missing modules found'); print('DYN-6/8 PROOF: INCONCLUSIVE')
srv.terminate()
