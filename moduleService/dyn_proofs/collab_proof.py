"""mtg-2 proof: the collab module is born manifest-first on the dyn
machinery (the second walk — scanning was first). Boot with it gated
OUT, admit it live, exercise the surface (401 without KC, 503 ladder
refusals with knobs cleared), put it away (410), re-admit.
Run per dyn_proofs/README.md (repo mounted AT /app):

  docker run --rm -u 1000:1000 -e HOME=/tmp -e PROOF_REPO=/app \\
    -v $PWD:/app -v $PWD/moduleService/dyn_proofs/collab_proof.py:/p.py:ro \\
    -w /app --entrypoint python3 prf-backend:staging /p.py
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error

REPO = os.environ.get('PROOF_REPO', '/app')
os.environ.update(DATABASE_PATH='/tmp/collab.db', POLARI_LAZY_BOOT='off',
                  POLARI_MODULES='video',  # collab NOT active at boot
                  POLARI_MESH_AUTOCONFIG='false')
for knob in ('LIVEKIT_KEYS', 'LIVEKIT_KEYS_FILE', 'LIVEKIT_URL',
             'LIVEKIT_CLIENT_URL'):
    os.environ.pop(knob, None)   # the refusal half must be honest
srv = subprocess.Popen([sys.executable, 'initLocalhostPolariServer.py'],
                       cwd=REPO, stdout=open('/tmp/boot.log', 'w'),
                       stderr=subprocess.STDOUT)


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


for i in range(240):
    code, _ = req('GET', '/api/health', timeout=5)
    if code == 200:
        break
    time.sleep(2)
else:
    print(open('/tmp/boot.log').read()[-3000:]); sys.exit(1)

checks = []
code, body = req('GET', '/api/collab/capability')
print(f'1) boot WITHOUT collab: /api/collab/capability -> {code} '
      f'(expect 404/410 — not served here)')
checks.append(code in (404, 410))

code, body = req('GET', '/api/refs/directory')
entries = body.get('classes', body if isinstance(body, dict) else {})
entry = (entries.get('CollaborationSession')
         if isinstance(entries, dict) else None)
print(f'   /api/refs/directory knows CollaborationSession pre-admit: '
      f'{json.dumps(entry)[:140] if entry else None}')
checks.append(entry is not None)

t0 = time.time()
code, body = req('POST', '/modules/collab/admit', timeout=300)
print(f'2) live admit collab -> {code}, took '
      f'{body.get("tookSeconds")}s, classes='
      f'{body.get("classesActivated", body.get("classesAdmitted"))}')
checks.append(code == 200)

code, body = req('GET', '/api/collab/capability')
print(f'3) capability (all knobs unset) -> {code}: keysConfigured='
      f'{body.get("keysConfigured")}, suggestion carries knob: '
      f'{"LIVEKIT_KEYS" in json.dumps(body.get("suggestion", {}))}')
checks.append(code == 200 and body.get('keysConfigured') is False
              and 'LIVEKIT_KEYS' in json.dumps(body.get('suggestion', {})))

code, body = req('GET', '/CollaborationSession')
print(f'4) CRUDE /CollaborationSession -> {code} (expect 200, empty)')
checks.append(code == 200)

code, body = req('POST', '/api/collab/sessions/nope/token', {})
print(f'5) token for a missing session, unauthenticated -> {code} '
      f'(expect 401, NOT 404 — an unauthenticated caller must not '
      f'learn which sessions exist)')
checks.append(code == 401)

# create a session by CRUDE, then prove the auth wall + the ladder
code, body = crude_post('CollaborationSession',
                        {'name': 'proof-room', 'title': 'proof'})
print(f'6) CRUDE create proof-room -> {code}')
checks.append(code in (200, 201))

code, body = req('POST', '/api/collab/sessions/proof-room/token', {})
print(f'7) token WITHOUT a verified KC caller -> {code} (expect 401 — '
      f'payload identities are evidence, not authorization)')
checks.append(code == 401)

code, body = req('GET', '/api/collab/sessions/proof-room/join-info')
print(f'8) join-info without LIVEKIT_CLIENT_URL -> {code} (expect 503 '
      f'+ suggestion): {json.dumps(body.get("suggestion", {}))[:100]}')
checks.append(code == 503 and 'suggestion' in body)

code, body = req('POST', '/modules/collab/put-away')
print(f'9) put-away collab -> {code}: ' + json.dumps(
    {k: body.get(k) for k in ('classesDeactivated', 'dbTablesKept',
                              'tookSeconds')}))
checks.append(code == 200)

code, body = req('GET', '/api/collab/capability')
print(f'10) after put-away: capability -> {code} (expect 410)')
checks.append(code == 410)

code, body = req('POST', '/modules/collab/admit', timeout=300)
print(f'11) re-admit -> {code}, took {body.get("tookSeconds")}s')
checks.append(code == 200)

code, body = req('GET', '/CollaborationSession')
rows = body if isinstance(body, list) else body.get('data', [])
print(f'12) proof-room SURVIVED put-away (tables kept): '
      f'{any("proof-room" in json.dumps(r) for r in (rows or []))}')
checks.append(code == 200
              and any('proof-room' in json.dumps(r) for r in (rows or [])))

srv.terminate()
passed = sum(checks)
print(f'\n{passed}/{len(checks)} PASS')
sys.exit(0 if passed == len(checks) else 1)
