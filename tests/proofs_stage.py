"""The PIPELINE's `proofs` stage (plan §I.9, ADVISORY): boot the real server in the image the build stage made, run
EVERY MathClaim through its cheapest tier (numeric / interval / sympy / z3 within each claim's budget), then the Lean
claims — but only where the engines ladder resolves a checker (PROOF_ENGINES_URL from the pipeline device, or the
proof-tools image on that device) and only the certificates that CHANGED since their last proof (the run's recorded
file sha256 vs the worker's), so a pin bump or an edited .lean is re-checked and an untouched one is not re-paid.

A red verdict (refuted, error, undecided, unprovable-here) is RECORDED, never a build failure — the same rule as the
scans: exit 0 always, results on stdout as JSON (or --out <file>), a human summary on stderr.

    docker run --rm -e PROOF_ENGINES_URL --entrypoint python3 prf-backend:staging tests/proofs_stage.py
"""
import argparse
import json
import os
import sys
import time

os.environ.setdefault('POLARI_MODULES', 'simulations,simSpace,materialsScience,pspp,magnetics,scoring,techtree,microchip,cntfet,electrodevice,sifet,hwfpga,mathshapes,tensormath,tensortree,computelod,mathproofs,cicd')
os.environ.setdefault('POLARI_DB_BACKEND', 'sqlite')
FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))

RED = ('refuted', 'error', 'undecided', 'unprovable-here')


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='-')
    ap.add_argument('--no-lean', action='store_true', help='skip the lean tier even when an engine resolves')
    args = ap.parse_args(argv)
    say = lambda s: print('[proofs] ' + s, file=sys.stderr, flush=True)
    t0 = time.time()
    from objectTreeManagerDecorators import managerObject
    manager = managerObject(hasServer=True, hasDB=True)   # the boot pass already generated obligations + checked never-run claims
    from mathproofs.custom import checkers, proof_engines, rules
    from mathproofs.custom.rows import _rows
    claims = sorted(_rows(manager, 'MathClaim'), key=lambda c: str(c.name))
    out = {'ran': True, 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'claims': {}, 'counts': {}, 'red': [], 'lean': {}, 'aggregate': {}}
    # 1. every claim, cheapest tier (a re-check: rows may have moved since the seed's last verdict)
    for c in claims:
        term = checkers.terms_of(c)
        if not term:
            out['claims'][str(c.name)] = {'status': str(c.proof_status), 'verdict': None, 'tier': None, 'note': 'no term (a template-less rule)'}
            continue
        tier = checkers.auto_tier(term)
        if tier == 'lean':
            out['claims'][str(c.name)] = {'status': checkers.status_of(manager, c), 'verdict': None, 'tier': 'lean', 'note': 'lean: see the lean section'}
            continue
        r = checkers.check(manager, c)
        out['claims'][str(c.name)] = {'status': str(c.proof_status), 'verdict': r['verdict'], 'tier': r['tier'], 'elapsed_s': r['run']['elapsed_s']}
        if r['verdict'] in RED or str(c.proof_status) in RED:
            out['red'].append({'claim': str(c.name), 'verdict': r['verdict'], 'status': str(c.proof_status), 'why': (r.get('detail') or {}).get('why', ''), 'counterexample': r.get('counterexample')})
    # 2. the lean claims, only where an engine resolves, only the certificates that changed
    place = proof_engines.resolve()
    out['lean'] = {'placement': place, 'checked': [], 'skipped_unchanged': [], 'not_run': None}
    if args.no_lean or place['how'] == 'refused':
        out['lean']['not_run'] = 'asked to skip' if args.no_lean else place['why']
    else:
        cap = proof_engines.remote_capability(place['where']) if place['how'] == 'remote' else None
        shas = {t['file']: t.get('sha256') for t in (cap or {}).get('theorems', [])} if cap else {}
        from mathproofs.custom import lean_tier
        runs = _rows(manager, 'ProofRun')
        for c in claims:
            term = checkers.terms_of(c)
            f = lean_tier.theorem_for(term)
            if not f:
                continue
            last = max([r for r in runs if str(r.claim) == str(c.name) and str(r.checker) == 'lean' and str(r.verdict) == 'holds'], key=lambda r: str(r.ran_at), default=None)
            last_sha = (json.loads(getattr(last, 'detail_json', '{}') or '{}').get('file_sha256') if last is not None else None)
            if last is not None and shas.get(f) and last_sha == shas.get(f) and not checkers.stale(manager, c):
                out['lean']['skipped_unchanged'].append({'claim': str(c.name), 'file': f, 'sha256': last_sha}); continue
            r = checkers.check(manager, c, tier='lean')
            d = r.get('detail') or {}
            out['lean']['checked'].append({'claim': str(c.name), 'file': f, 'verdict': r['verdict'], 'status': str(c.proof_status), 'elapsed_s': d.get('elapsed_s'), 'pins': d.get('pins'), 'hash_matches': d.get('hash_matches'), 'how': d.get('how'), 'why': d.get('why', '')})
            out['claims'][str(c.name)] = {'status': str(c.proof_status), 'verdict': r['verdict'], 'tier': 'lean', 'elapsed_s': d.get('elapsed_s')}
            if r['verdict'] != 'holds':
                out['red'].append({'claim': str(c.name), 'verdict': r['verdict'], 'status': str(c.proof_status), 'why': d.get('why', '')})
    for name, row in out['claims'].items():
        k = (row.get('status') or '?').split(' ')[0]
        out['counts'][k] = out['counts'].get(k, 0) + 1
    out['aggregate'] = checkers.aggregate(manager, claims)
    out['elapsed_s'] = round(time.time() - t0, 1)
    out['advisory'] = 'a red verdict is recorded, never a build failure (plan §I.9) — until he says otherwise'
    say('%d claims; by status %s; red %d; lean %s; %.1f s' % (len(out['claims']), out['counts'], len(out['red']),
        ('checked %d, unchanged %d' % (len(out['lean']['checked']), len(out['lean']['skipped_unchanged']))) if not out['lean']['not_run'] else 'not run (%s)' % out['lean']['not_run'][:80], out['elapsed_s']))
    for r in out['red']:
        say('  RED %s: %s %s — %s' % (r['claim'], r['verdict'], r['status'], (r.get('why') or '')[:100]))
    text = json.dumps(out, indent=1, default=str)
    if args.out == '-':
        print(text)
    else:
        open(args.out, 'w').write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
