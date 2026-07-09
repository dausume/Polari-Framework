#!/usr/bin/env python3
"""Live-API smoke suite for PRF staging — cross-module endpoint contracts.
Stdlib only. Usage: python3 live_smoke.py [BASE_URL]
Runs anywhere that can resolve the nip.io host (any swarm node)."""
import json, ssl, sys, urllib.request, socket

BASE = (sys.argv[1] if len(sys.argv) > 1
        else "https://api.prf.192.168.0.210.nip.io").rstrip("/")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# (method, path, jsonBody or None, predicate(status, obj)->(ok, note))
def has_ok(s, o):        return (s == 200 and isinstance(o, dict) and o.get("ok") is True, "")
def is_200(s, o):        return (s == 200, "")
def count_ge(n):
    def p(s, o):
        c = (o.get("count") if isinstance(o, dict) else None)
        if c is None and isinstance(o, dict):
            for k in ("shapes","items","results","towers","materials","foods"):
                if isinstance(o.get(k), list): c = len(o[k]); break
        return (s == 200 and (c or 0) >= n, f"count={c}")
    return p

CHECKS = [
    ("GET", "/api/shapes", None, count_ge(7)),
    ("GET", "/api/shapes/unit-sphere/properties", None, has_ok),
    ("GET", "/api/shapes/unit-sphere/classify", None,
     lambda s,o:(s==200 and o.get("type")=="sphere", o.get("type"))),
    ("GET", "/api/shapes/cad-capability", None, has_ok),
    ("GET", "/api/aquaponics/towers", None, is_200),
    ("GET", "/api/aquaponics/towers/demo-herb-tower/geometry", None, has_ok),
    ("GET", "/api/aquaponics/towers/demo-herb-tower/growth-forecast?plant=sweet-basil&days=90",
     None, has_ok),
    ("GET", "/api/aquaponics/pots", None, is_200),
    ("GET", "/api/aquaponics/plants", None, is_200),
    ("GET", "/api/aquaponics/systems", None, is_200),
    ("GET", "/api/aquaponics/hydraulics/capability", None, is_200),
    ("GET", "/api/nutrition/foods", None, is_200),
    ("GET", "/api/nutrition/nutrients", None, is_200),
    ("GET", "/api/microalgae/reactors", None, is_200),
    ("GET", "/api/microalgae/strains", None, is_200),
    ("GET", "/api/biomining/systems", None, is_200),
    ("GET", "/api/scoring/assertions", None, is_200),
    ("GET", "/api/msci/materials/ferrite/detail", None, has_ok),
    ("GET", "/api/msci/scale-presence", None, is_200),
    ("GET", "/api/supplychain/chains", None, is_200),
    ("GET", "/api/modules", None, is_200),
    ("POST", "/api/shapes/unit-sphere/evaluate", {"x":0,"y":0,"z":0},
     lambda s,o:(s==200 and o.get("inside") is True, f"inside={o.get('inside')}")),
]

def call(method, path, body):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Content-Type":"application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            raw = r.read()
            try: return r.status, json.loads(raw)
            except Exception: return r.status, raw.decode(errors="replace")[:80]
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, None
    except Exception as e:
        return 0, str(e)[:80]

def main():
    host = socket.gethostname()
    print(f"== PRF live smoke @ {BASE}  (runner host: {host}) ==")
    passed = 0
    for method, path, body, pred in CHECKS:
        status, obj = call(method, path, body)
        ok, note = pred(status, obj if isinstance(obj, dict) else {})
        passed += ok
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {method:4} {path[:58]:58} http={status} {note}")
    total = len(CHECKS)
    print(f"\n{passed}/{total} passed on {host}")
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
