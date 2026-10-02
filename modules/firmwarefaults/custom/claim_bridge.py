"""
@module firmwarefaults.custom.claim_bridge

A RUN BECOMES A CLAIM (FIRMWARE_SCENARIO_PLAN.md §1): one mathproofs `MathClaim` per (scenario, firmware build) —
"firmware F under scenario S is free of fault K" — kind `safe-under-scenario`, checker `sim` (tier 0: a WITNESS, never a
proof), its about_refs naming the Scenario, the FirmwareBuild and the fault row. Each run also leaves a `ProofRun`
(checker sim) so the claim's certificate_ref points at evidence. His vocabulary, kept apart:

    failed → refuted (counterexample_json = cycle, PC, landed PC, the torn value, the frames)
    passed → witnessed · inapplicable → inapplicable · undetermined → undetermined

A refuted claim is never deleted, and never silently flipped back: a later passing run on the SAME build is recorded
as its own ProofRun but leaves `refuted` standing (a counterexample outranks a witness). A different build (the AFTER
variant) is a different claim.

The claim carries no term in statement_json (the sim tier lowers no term language; mathproofs' boot pass checks only
claims with a term, so it leaves these alone) — the statement is in words, with a LaTeX rendering for people.
"""
import json


def claim_name(scenario, build_name):
    return 'fw-safe:%s:%s' % (scenario, build_name)


def _latex(build_name, scenario, fault_class):
    esc = lambda s: str(s).replace('_', r'\_')  # noqa: E731
    return r'\mathrm{safe}_{\mathrm{sim}}\left(\texttt{%s},\ \texttt{%s},\ \mathrm{%s}\right)' % (esc(build_name), esc(scenario), esc(fault_class))


def write(sink, run, scenario, harness_version=''):
    """Upsert the claim + a ProofRun for one ScenarioRun dict. Returns (claim_name, status_after, status_before)."""
    from firmwarefaults.custom.outcome import CLAIM_STATUS
    name = claim_name(scenario['name'], run['build_name'])
    status = CLAIM_STATUS.get(run['outcome'], 'undetermined')
    prior = sink.get('MathClaim', name)
    before = (prior.get('proof_status') if isinstance(prior, dict) else getattr(prior, 'proof_status', '')) if prior is not None else ''
    if before == 'refuted' and status != 'refuted':
        after = 'refuted'   # a counterexample outranks a later witness on the same build
    else:
        after = status
    ce = {}
    if status == 'refuted':
        ce = {'cycle': run['fault_cycle'], 'pc': run['fault_pc'], 'pc_symbol': run['fault_symbol'], 'landed_pc': run['landed_pc'],
              'landed_symbol': run['landed_symbol'], 'torn_value': run['torn_value'], 'expected_value': run['expected_value'],
              'uptime_sequence': run['uptime_sequence'], 'trace_sha256': run['trace_sha256'], 'run': run['name']}
    fields = {
        'name': name,
        'description': 'Firmware build %s (variant %s) under scenario %s is free of fault %s (%s): %s' % (
            run['build_name'], run['variant'], scenario['name'], scenario['fault'], scenario['fault_class'], scenario['expected_observable']),
        'kind': 'safe-under-scenario',
        'about_refs_json': json.dumps(['Scenario:%s' % scenario['name'], 'FirmwareBuild:%s' % run['build_name'],
                                       '%s:%s' % (scenario['fault_class'], scenario['fault'])]),
        'statement_json': '{}',
        'statement_latex': _latex(run['build_name'], scenario['name'], scenario['fault_class']),
        'assumptions_json': json.dumps(['the simavr 1.6 twin models the ATmega328P at instruction granularity (one interleaving per run)']),
        'scope_json': json.dumps({'scenario': scenario['name'], 'variant': run['variant'], 'seed': run['seed'], 'side': run['side']}),
        'proof_status': after,
        'checker': 'sim',
        'certificate_ref': run['name'],
        'counterexample_json': json.dumps(ce) if after == 'refuted' and ce else (
            (prior.get('counterexample_json') if isinstance(prior, dict) else getattr(prior, 'counterexample_json', '{}')) if prior is not None and after == 'refuted' else '{}'),
        'evidence_level': 'measured' if after in ('refuted', 'witnessed') else 'none',
        'statement_hash': '',
        'budget_s': 0.0,
        'provenance': 'firmwarefaults sc-0 runner (FIRMWARE_SCENARIO_PLAN.md §1): a sim-tier witness/counterexample, never a proof',
        'notes': run['verdict_words'],
    }
    sink.upsert('MathClaim', fields)
    verdict = {'witnessed': 'holds', 'refuted': 'refuted', 'inapplicable': 'inapplicable', 'undetermined': 'undetermined'}[status]
    sink.upsert('ProofRun', {
        'name': '%s@sim@%s' % (name, run['ran_at']), 'description': 'scenario run %s' % run['name'], 'claim': name, 'checker': 'sim',
        'checker_version': harness_version or run['harness_digest'], 'verdict': verdict,
        'detail_json': json.dumps({'run': run['name'], 'outcome': run['outcome'], 'words': run['verdict_words'], 'counterexample': ce}),
        'output_tail': run['uptime_sequence'][-400:], 'elapsed_s': run['wall_s'], 'rows_state_hash': run['firmware_sha256'],
        'ran_at': run['ran_at'], 'ran_where': run['harness_digest'], 'notes': 'kept beside a refuted claim' if before == 'refuted' and status != 'refuted' else ''})
    return name, after, before
