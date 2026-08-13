"""ret-1 proof: the reticulum module is born manifest-first on the dyn
machinery (the third walk — scanning, collab first). Boot with it
gated OUT, admit it live, exercise the surface (capability with the
licence pins + honest ladder refusal, .arch honesty, 401 on the
inbound seam, seeded interface row), put it away (410), re-admit and
prove tables survived. Run per dyn_proofs/README.md (repo mounted AT
/app):

  docker run --rm -u 1000:1000 -e HOME=/tmp -e PROOF_REPO=/app \\
    -v $PWD:/app -v $PWD/moduleService/dyn_proofs/reticulum_proof.py:/p.py:ro \\
    -w /app --entrypoint python3 prf-backend:staging /p.py
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error

REPO = os.environ.get('PROOF_REPO', '/app')
os.environ.update(DATABASE_PATH='/tmp/reticulum.db',
                  POLARI_LAZY_BOOT='off',
                  POLARI_MODULES='video',  # reticulum NOT active at boot
                  POLARI_MESH_AUTOCONFIG='false')
os.environ.pop('RETICULUM_URL', None)  # the refusal half must be honest
srv = subprocess.Popen([sys.executable, 'initLocalhostPolariServer.py'],
                       cwd=REPO, stdout=open('/tmp/boot.log', 'w'),
                       stderr=subprocess.STDOUT)


def crude_post(class_name, params, timeout=60):
    # CRUDE speaks multipart form (initParamSets), not JSON — the
    # scanning proof's helper, verbatim.
    import uuid
    boundary = uuid.uuid4().hex
    body = (f'--{boundary}\r\nContent-Disposition: form-data; '
            f'name="initParamSets"\r\n\r\n{json.dumps([params])}\r\n'
            f'--{boundary}--\r\n').encode()
    r = urllib.request.Request(f'http://localhost:3000/{class_name}',
                               data=body, method='POST', headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}'})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as e:
        return e.code, {'raw': e.read()[:300].decode('utf-8', 'ignore')}
    except Exception as e:
        return None, {'err': str(e)}


def req(method, path, payload=None, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(f'http://localhost:3000{path}',
                               data=data, method=method,
                               headers={'Content-Type': 'application/json'}
                               if data else {})
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

checks = []
code, body = req('GET', '/api/reticulum/capability')
print(f'1) boot WITHOUT reticulum: /api/reticulum/capability -> {code} '
      f'(expect 404/410 — not served here)')
checks.append(code in (404, 410))

code, body = req('GET', '/api/refs/directory')
entries = body.get('classes', body if isinstance(body, dict) else {})
entry = (entries.get('ReticulumInterface')
         if isinstance(entries, dict) else None)
print(f'   /api/refs/directory knows ReticulumInterface pre-admit: '
      f'{json.dumps(entry)[:140] if entry else None}')
checks.append(entry is not None)

code, body = req('POST', '/modules/reticulum/admit', timeout=300)
print(f'2) live admit reticulum -> {code}, took '
      f'{body.get("tookSeconds")}s, classes='
      f'{body.get("classesActivated", body.get("classesAdmitted"))}')
checks.append(code == 200)

code, body = req('GET', '/api/reticulum/capability')
pins = body.get('stackPins', {})
print(f'3) capability (RETICULUM_URL unset) -> {code}: pins={pins}, '
      f'suggestion carries knob: '
      f'{"RETICULUM_URL" in json.dumps(body.get("suggestion", {}))}')
checks.append(code == 200 and pins.get('rns') == '0.9.4'
              and pins.get('lxmf') == '0.6.3'
              and 'RETICULUM_URL' in json.dumps(body.get('suggestion', {})))

code, body = req('GET', '/ReticulumInterface')
rows = body if isinstance(body, list) else body.get('data', [])
seeded = 'local-tcp' in json.dumps(rows or body)
print(f'4) CRUDE /ReticulumInterface -> {code}; local-tcp seed landed: '
      f'{seeded} (the five-registration gotcha would show here)')
checks.append(code == 200 and seeded)

code, body = req('GET', '/api/reticulum/arch')
print(f'5) .arch honesty on an empty mesh -> {code}: reachable='
      f'{body.get("reachable")}, staleBucket exists='
      f'{"unmeasuredOrStale" in body}')
checks.append(code == 200 and body.get('reachable') == []
              and 'unmeasuredOrStale' in body)

code, body = req('POST', '/api/reticulum/inbound',
                 {'archName': 'isle-x.arch', 'kind': 'gossip',
                  'payload': {'modules': []}})
print(f'6) inbound seam WITHOUT a verified KC caller -> {code} '
      f'(expect 401 — arrival on the mesh is not authorization)')
checks.append(code == 401)

code, body = req('GET', '/api/reticulum/arch-topology')
local = (body.get('isles') or [{}])[0]
print(f'6a) arch-topology -> {code}: local isle '
      f'{local.get("name")!r}, devices='
      f'{[d.get("name") for d in local.get("devices", [])]}, '
      f'verdict={local.get("verdict", {}).get("state")}')
checks.append(code == 200 and local.get('kind') == 'local'
              and any(d.get('name') == 'local-tcp'
                      for d in local.get('devices', []))
              and local.get('verdict', {}).get('state')
              in ('idle', 'unknown'))

code, body = req('GET', '/api/reticulum/resolve/nope.arch')
print(f'6b) resolve an UNMAPPED name -> {code} (expect 404, refused '
      f'by name with knob): '
      f'{json.dumps(body.get("suggestion", {}))[:80]}')
checks.append(code == 404 and 'knob' in body.get('suggestion', {}))

code, body = crude_post('ReticulumDestination',
                        {'name': 'isle-x-gossip',
                         'dest_hash': 'ab12cd34', 'dest_type': 'single',
                         'scope': 'mesh'})
print(f'6c) CRUDE create destination isle-x-gossip -> {code}')
checks.append(code in (200, 201))

code, body = req('GET', '/api/reticulum/resolve/isle-x-gossip')
print(f'6d) resolve the mapped name -> {code}: destHash='
      f'{body.get("destHash")}, scope={body.get("scope")}')
checks.append(code == 200 and body.get('destHash') == 'ab12cd34'
              and body.get('scope') == 'mesh')

code, body = req('GET', '/api/reticulum/peers')
print(f'6e) peers (no sidecar, no sightings) -> {code}: buckets='
      f'{sorted(body.get("peers", {}).keys())}, sidecarLive='
      f'{body.get("sidecarLive")}')
checks.append(code == 200 and body.get('sidecarLive') is False
              and set(body.get('peers', {}))
              == {'unadjudicated', 'archipelago', 'mesh', 'ignored'})

code, body = req('POST', '/api/reticulum/peers/xx/adjudicate',
                 {'decision': 'mesh'})
print(f'6f) adjudicate WITHOUT a verified KC caller -> {code} '
      f'(expect 401 — admission is a human act with a name on it)')
checks.append(code == 401)

code, body = req('POST', '/modules/reticulum/put-away')
print(f'7) put-away reticulum -> {code}: ' + json.dumps(
    {k: body.get(k) for k in ('classesDeactivated', 'dbTablesKept',
                              'tookSeconds')}))
checks.append(code == 200)

code, body = req('GET', '/api/reticulum/capability')
print(f'8) after put-away: capability -> {code} (expect 410)')
checks.append(code == 410)

code, body = req('POST', '/modules/reticulum/admit', timeout=300)
print(f'9) re-admit -> {code}, took {body.get("tookSeconds")}s')
checks.append(code == 200)

code, body = req('GET', '/ReticulumInterface')
rows = body if isinstance(body, list) else body.get('data', [])
print(f'10) local-tcp SURVIVED put-away (tables kept): '
      f'{"local-tcp" in json.dumps(rows or body)}')
checks.append(code == 200 and 'local-tcp' in json.dumps(rows or body))

srv.terminate()
passed = sum(checks)
print(f'\n{passed}/{len(checks)} PASS')
sys.exit(0 if passed == len(checks) else 1)
