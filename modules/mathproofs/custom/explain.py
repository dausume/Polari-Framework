"""
@module mathproofs.custom.explain

EACH PROOF ROW, EXPLAINED (bp-3): what the claim says in words, which checker looked at it, what it concluded and
what that word means, and the exact way to run it again. Read by GET /api/explain; shown on /object/:class/:name.
"""
import json

from mathproofs.custom import checkers
from mathproofs.custom.rows import by_name

STATUS_WORDS = {
    'conjectured': 'stated, not yet checked by anything',
    'witnessed': 'true on every row we have (a numeric check) — evidence, NOT a proof: a new row could break it',
    'checked-symbolically': 'true over free symbols at a fixed dimension (a computer-algebra check) — strong, but not a theorem for every dimension',
    'decided': 'decided exactly over the whole stated domain (interval arithmetic or an SMT solver) — a proof for that domain',
    'proved': 'a machine-checked theorem (Lean accepted a proof term for exactly this statement)',
    'refuted': 'FALSE: a concrete counterexample was found and is kept on the row',
    'undetermined': 'not defined here: a premise fails or a value is unrecorded — neither true nor false',
    'unprovable-here': 'no checker on this instance can speak to it (a named gap), so it stays open',
    'undecided': 'the checker ran out of its time budget without an answer',
}
TIER_WORDS = {'numeric': 'the numeric tier (walks the rows)', 'interval': 'the interval tier (exact set arithmetic)', 'sympy': 'the SymPy tier (computer algebra over symbols)',
              'z3': 'the z3 tier (an SMT solver over the continuum / machine integers)', 'lean': 'the Lean tier (a committed theorem, kernel-checked)', 'human': 'a person (a signed note)'}


def _refs(row, field='about_refs_json'):
    try:
        v = json.loads(getattr(row, field, '[]') or '[]')
    except Exception:
        v = []
    out = []
    for e in v if isinstance(v, list) else []:
        if isinstance(e, str) and ':' in e:
            c, _, n = e.partition(':'); out.append({'class': c, 'name': n})
    return out


def _check_steps(name, tier):
    return ['# on the live instance (any signed-in person):', 'POST /api/mathproofs/claims/%s/check%s' % (name, ('?tier=' + tier) if tier else ''),
            '# by hand, from the framework dir (same code path, in-process):', 'cd polari-rf-node/polari-framework',
            "PYTHONPATH=.:modules python3 -c \"from tests.tensor_liveboot_probe import *\"  # or: the mathproofs selftest runs every seeded claim: python3 modules/mathproofs/mathproofs_selftest.py",
            '# the lean tier needs the polari-proof-tools worker (docker compose -p proof-engines -f docker-compose.proof-engines.yml up -d; PROOF_ENGINES_URL=http://localhost:9810)']


def explain_claim(manager, row):
    status = checkers.status_of(manager, row)
    head = status.split(' ')[0]
    tier = str(getattr(row, 'checker', '') or '')
    latex = str(getattr(row, 'statement_latex', '') or '')
    about = _refs(row)
    try:
        scope = json.loads(getattr(row, 'scope_json', '{}') or '{}')
    except Exception:
        scope = {}
    ce = str(getattr(row, 'counterexample_json', '') or '')
    return {'in one sentence': '%s — a %s claim about %s; right now it is %s.' % (str(getattr(row, 'description', '') or row.name), str(getattr(row, 'kind', '')),
                                                                              ', '.join(r['name'] for r in about) or 'no particular row', status),
            'what was done': ('%s looked at it and set the status %r: %s.' % (TIER_WORDS.get(tier, tier or 'nothing yet').capitalize(), head, STATUS_WORDS.get(head, head)))
                             + ((' Counterexample: %s.' % ce) if head == 'refuted' and ce not in ('', '{}') else '')
                             + (' (stale: a row it speaks of moved since; the next generation re-checks it)' if '(stale)' in status else ''),
            'inputs': {'the statement (LaTeX)': latex, 'the statement (term)': str(getattr(row, 'statement_json', '')), 'speaks of': ', '.join('%s %s' % (r['class'], r['name']) for r in about) or '—',
                       'claimed over (scope)': json.dumps(scope) if scope else 'the rows\' own domains', 'time budget (s)': str(getattr(row, 'budget_s', ''))},
            'result': status, 'how to reproduce': _check_steps(str(row.name), tier if tier not in ('', 'human') else ''),
            'evidence': 'certificate: %s · evidence level: %s' % (str(getattr(row, 'certificate_ref', '') or 'none'), str(getattr(row, 'evidence_level', ''))),
            'how far to trust it': STATUS_WORDS.get(head, head), 'related': about}


def explain_run(manager, row):
    claim = by_name(manager, 'MathClaim', str(getattr(row, 'claim', '')))
    verdict = str(getattr(row, 'verdict', ''))
    tier = str(getattr(row, 'checker', ''))
    return {'in one sentence': 'One run of %s on the claim %s at %s: it said %r in %s s.' % (TIER_WORDS.get(tier, tier), getattr(row, 'claim', ''), getattr(row, 'ran_at', ''), verdict, getattr(row, 'elapsed_s', '')),
            'what was done': 'The claim\'s statement was lowered to %s (version %s) and evaluated; the verdict is what the checker returned, and the rows-state hash fingerprints every row the statement read — if any of them changes, this run is stale and the claim is re-checked.'
                             % (tier, getattr(row, 'checker_version', '')),
            'inputs': {'claim': str(getattr(row, 'claim', '')), 'checker': tier, 'checker version': str(getattr(row, 'checker_version', '')), 'rows-state hash': str(getattr(row, 'rows_state_hash', ''))},
            'result': '%s (%s s)' % (verdict, getattr(row, 'elapsed_s', '')), 'how to reproduce': _check_steps(str(getattr(row, 'claim', '')), tier),
            'evidence': 'this row IS the record; the claim\'s certificate_ref points at the latest one',
            'how far to trust it': STATUS_WORDS.get({'holds': 'decided' if tier in ('interval', 'z3') else ('checked-symbolically' if tier == 'sympy' else ('proved' if tier == 'lean' else 'witnessed'))}.get(verdict, verdict), verdict),
            'related': [{'class': 'MathClaim', 'name': str(getattr(row, 'claim', ''))}] + (_refs(claim) if claim is not None else [])}


def explain_obligation(manager, row):
    return {'in one sentence': 'The rule %s demanded this of the tree %s; it is discharged by the claim %s, which stands at %s.' % (getattr(row, 'rule', ''), getattr(row, 'tree', ''), getattr(row, 'discharged_by', ''), getattr(row, 'status', '')),
            'what was done': str(getattr(row, 'description', '') or 'the rule matched a structure in the tree and generated the claim to check') + '. Structure matched: %s.' % str(getattr(row, 'structure_json', '')),
            'inputs': {'tree': str(getattr(row, 'tree', '')), 'rule': str(getattr(row, 'rule', '')), 'matched': str(getattr(row, 'structure_json', '')), 'generated at': str(getattr(row, 'generated_at', ''))},
            'result': str(getattr(row, 'status', '')),
            'how to reproduce': ['POST /api/mathproofs/trees/%s/obligations      # regenerates every obligation of the tree from the rules and re-checks the never-run ones' % getattr(row, 'tree', '')],
            'how far to trust it': STATUS_WORDS.get(str(getattr(row, 'status', '')).split(' ')[0], str(getattr(row, 'status', ''))),
            'related': [{'class': 'MathClaim', 'name': str(getattr(row, 'discharged_by', ''))}, {'class': 'InferenceRule', 'name': str(getattr(row, 'rule', ''))}, {'class': 'TensorTreeDefinition', 'name': str(getattr(row, 'tree', ''))}] + _refs(row)}


def explain_source(manager, row):
    return {'in one sentence': '%s (%s, %s) — cited for %s.' % (getattr(row, 'title', ''), getattr(row, 'parties', ''), getattr(row, 'date', ''), getattr(row, 'proves', '')),
            'what was done': str(getattr(row, 'proves_detail', '')),
            'inputs': {'where': str(getattr(row, 'ref', '')), 'link': str(getattr(row, 'url', '') or 'no DOI / URL')},
            'result': 'verified' if getattr(row, 'verified', False) else 'not verified online',
            'how to reproduce': ['open %s and compare title, authors and venue with this row' % (getattr(row, 'url', '') or 'the printed reference'), '# or: curl -s https://api.crossref.org/works/<doi> | jq .message.title'],
            'evidence': str(getattr(row, 'verified_via', '')), 'how far to trust it': 'a published source; it backs the METHOD, not any particular claim here'}


EXPLAINERS = {'MathClaim': explain_claim, 'ProofRun': explain_run, 'ProofObligation': explain_obligation, 'ProofMethodReference': explain_source}
