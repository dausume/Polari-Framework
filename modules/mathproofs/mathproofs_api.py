"""
@module mathproofs.mathproofs_api

/api/mathproofs — claims, rules, obligations, runs; check a claim through a tier; (re)generate a tree's obligations;
`engines` = where the lean checker would run (the ladder's answer, pf-2).
Every number a person could act on is here: per claim the latest run's elapsed, per tree the AGGREGATE (the sum of
the latest runs' elapsed and the worst case = the sum of budgets of the claims that can run long) — D-pf-9.
"""
import json

from objectTreeDecorators import treeObject, treeObjectInit
from mathproofs.custom import checkers, rules, terms, proof_engines
from mathproofs.custom.rows import by_name, _rows


class MathProofsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/mathproofs'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/mathproofs', self)
            add('/api/mathproofs/claims/{name}', self, suffix='claim')
            add('/api/mathproofs/claims/{name}/check', self, suffix='check')
            add('/api/mathproofs/rules', self, suffix='rules')
            add('/api/mathproofs/obligations', self, suffix='obligations')
            add('/api/mathproofs/trees/{name}/obligations', self, suffix='tree_obligations')
            add('/api/mathproofs/aggregate', self, suffix='aggregate')
            add('/api/mathproofs/engines', self, suffix='engines')

    def _rows(self, cls):
        return _rows(self.manager, cls)

    def _claim_view(self, c):
        latest = self._latest_run(str(c.name))
        return {'name': str(c.name), 'kind': str(getattr(c, 'kind', '')), 'about': _j(getattr(c, 'about_refs_json', '[]'), []), 'status': checkers.status_of(self.manager, c),
                'checker': str(getattr(c, 'checker', '')), 'evidence_level': str(getattr(c, 'evidence_level', '')), 'latex': str(getattr(c, 'statement_latex', '')) or terms.to_latex(checkers.terms_of(c)),
                'statement': checkers.terms_of(c), 'counterexample': _j(getattr(c, 'counterexample_json', '{}'), {}), 'budget_s': getattr(c, 'budget_s', 25.0),
                'latest_run': latest, 'description': str(getattr(c, 'description', ''))}

    def _latest_run(self, claim_name):
        runs = [r for r in self._rows('ProofRun') if str(getattr(r, 'claim', '')) == claim_name]
        if not runs:
            return None
        r = max(runs, key=lambda x: str(getattr(x, 'ran_at', '')))
        return {'name': str(r.name), 'checker': str(getattr(r, 'checker', '')), 'verdict': str(getattr(r, 'verdict', '')), 'elapsed_s': float(getattr(r, 'elapsed_s', 0.0) or 0.0), 'ran_at': str(getattr(r, 'ran_at', ''))}

    def aggregate(self, claims):
        """The time reading (D-pf-9): what the latest runs cost, and the worst case if every long-running tier used its budget."""
        latest = [self._latest_run(str(c.name)) for c in claims]
        spent = sum((r or {}).get('elapsed_s', 0.0) for r in latest)
        long_tiers = [c for c in claims if (checkers.auto_tier(checkers.terms_of(c)) in ('z3', 'lean')) or str(getattr(c, 'checker', '')) in ('z3', 'lean')]
        return {'claims': len(claims), 'runs_recorded': sum(1 for r in latest if r), 'latest_runs_elapsed_s': round(spent, 4),
                'worst_case_s': round(sum(float(getattr(c, 'budget_s', 25.0) or 0) for c in long_tiers), 1), 'long_running_claims': len(long_tiers),
                'note': 'latest_runs_elapsed_s = what the recorded runs cost; worst_case_s = the sum of budgets of the claims a long-running tier (z3/lean) would take — the number to watch before it grows unreasonable in aggregate'}

    def on_get(self, request, response):
        claims = self._rows('MathClaim')
        by_status = {}
        for c in claims:
            st = checkers.status_of(self.manager, c).split(' ')[0]; by_status[st] = by_status.get(st, 0) + 1
        response.media = {'ok': True, 'claims': [self._claim_view(c) for c in claims], 'by_status': by_status,
                          'rules': [str(r.name) for r in self._rows('InferenceRule') if getattr(r, 'enabled', True)], 'obligations': len(self._rows('ProofObligation')),
                          'tiers': ['numeric (witness on the rows: measured)', 'interval (exact set arithmetic: decided)', 'sympy (over symbols: checked-symbolically)', 'z3 (over the continuum / machine integers within budget_s: decided)', 'lean (a committed theorem checked by the polari-proof-tools engines worker: proved; never automatic)', 'human (a signed note, labelled)'],
                          'aggregate': self.aggregate(claims), 'vocabulary': 'proofs never change a mapping\'s mapping_status or evidence_level (D-pf-8); a refuted claim keeps its counterexample'}

    def on_get_claim(self, request, response, name):
        c = by_name(self.manager, 'MathClaim', name)
        if c is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no MathClaim %r' % name}; return
        runs = sorted([r for r in self._rows('ProofRun') if str(getattr(r, 'claim', '')) == name], key=lambda r: str(getattr(r, 'ran_at', '')))
        response.media = {'ok': True, 'claim': self._claim_view(c), 'stale': checkers.stale(self.manager, c), 'valid_term': terms.validate(checkers.terms_of(c)) == [],
                          'runs': [{'name': str(r.name), 'checker': str(r.checker), 'version': str(r.checker_version), 'verdict': str(r.verdict), 'elapsed_s': r.elapsed_s, 'ran_at': str(r.ran_at), 'detail': _j(getattr(r, 'detail_json', '{}'), {})} for r in runs]}

    def on_post_check(self, request, response, name):
        """Run one tier (?tier=numeric|interval|sympy|z3|lean; default = the cheapest that can speak to the term)."""
        c = by_name(self.manager, 'MathClaim', name)
        if c is None:
            response.status = '404 Not Found'; response.media = {'ok': False, 'error': 'no MathClaim %r' % name}; return
        tier = (request.params or {}).get('tier') or None
        if tier and tier not in ('numeric', 'interval', 'sympy', 'z3', 'lean'):
            response.status = '400 Bad Request'; response.media = {'ok': False, 'error': 'tier must be numeric | interval | sympy | z3 | lean (human verdicts are written, not run)'}; return
        r = checkers.check(self.manager, c, tier=tier)
        response.status = '201 Created'
        response.media = {'ok': True, **r, 'claim_now': self._claim_view(c)}

    def on_get_rules(self, request, response):
        response.media = {'ok': True, 'rules': [{'name': str(r.name), 'pattern': str(r.pattern), 'obligation_kind': str(r.obligation_kind), 'checker_default': str(r.checker_default), 'enabled': bool(r.enabled),
                                                 'template': _j(getattr(r, 'template_json', '{}'), {}), 'rationale': str(r.rationale)} for r in self._rows('InferenceRule')]}

    def on_get_obligations(self, request, response):
        p = request.params or {}
        obs = rules.obligations_of(self.manager, tree=p.get('tree'), mapping=p.get('mapping'))
        response.media = {'ok': True, 'obligations': obs, 'count': len(obs)}

    def on_post_tree_obligations(self, request, response, name):
        """(Re)generate the obligations of one tree from every enabled rule and run the cheap tiers."""
        r = rules.generate(self.manager, name)
        if not r.get('ok'):
            response.status = '404 Not Found'; response.media = r; return
        names = {o['obligation'] for o in r['obligations']}
        claims = [c for c in self._rows('MathClaim') if str(c.name) in names]
        r['aggregate'] = self.aggregate(claims)
        response.status = '201 Created'; response.media = r

    def on_get_tree_obligations(self, request, response, name):
        obs = rules.obligations_of(self.manager, tree=name)
        claims = [by_name(self.manager, 'MathClaim', o['claim']) for o in obs]
        response.media = {'ok': True, 'tree': name, 'obligations': obs, 'aggregate': self.aggregate([c for c in claims if c is not None])}

    def on_get_aggregate(self, request, response):
        response.media = {'ok': True, **self.aggregate(self._rows('MathClaim'))}

    def on_get_engines(self, request, response):
        """Where the lean checker WOULD run (the engines ladder's answer before any dispatch) — pf-2."""
        response.media = {'ok': True, 'placement': proof_engines.placement()}


def _j(s, d):
    try:
        v = json.loads(s)
        return v if v is not None else d
    except Exception:
        return d
