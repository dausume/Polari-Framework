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

sc-2 — EVIDENCE TIERS side by side (MathClaim.evidence_tiers_json; plan §5): each tier that speaks to the claim leaves one
entry {tier, status, ref, measure, at} (the newest per (tier, ref) kept), and proof_status is the strongest HONEST status
among them:
    sim         a run: refuted | witnessed | inapplicable | undetermined (above)
    statistics  a campaign: the claim's status is UNCHANGED; the likelihood + its Wilson interval go into measure_json
    formal      a FormalCheck (CBMC): holds → `decided` (bounded, k on the entry — never `proved`); a counterexample → refuted
                sc-2c: or Frama-C/Mthread (checker frama-c-mthread): no race → `decided`, measure "decided (unbounded)" on the
                entry; a race → refuted with the two racing source lines (the negative control writes no claim)
A refutation outranks every other tier; `decided` outranks `witnessed`; a later sim witness never lowers `decided`.
"""
import datetime
import json

RANK = {'': 0, 'conjectured': 0, 'undetermined': 0, 'inapplicable': 0, 'witnessed': 1, 'decided': 2, 'proved': 3, 'refuted': 9}


def _get(row, field, default=''):
    if row is None:
        return default
    return row.get(field, default) if isinstance(row, dict) else getattr(row, field, default)


def _tiers(row):
    try:
        t = json.loads(_get(row, 'evidence_tiers_json', '[]') or '[]')
        return t if isinstance(t, list) else []
    except ValueError:
        return []


def merge_tier(tiers, entry):
    """Keep one entry per (tier, ref): the newest replaces the older; the list stays in tier order sim → statistics → formal."""
    order = {'sim': 0, 'statistics': 1, 'formal': 2, 'static': 3}
    out = [t for t in tiers if not (t.get('tier') == entry.get('tier') and t.get('ref') == entry.get('ref'))] + [entry]
    return sorted(out, key=lambda t: (order.get(t.get('tier'), 9), str(t.get('ref'))))


def strongest(current, incoming):
    """The honest status after a tier spoke: a refutation stays; a stronger status replaces a weaker; an equal or weaker one
    leaves the claim as it was (an inapplicable / undetermined tier never erases a witness or a decision)."""
    if current == 'refuted':
        return 'refuted'
    if incoming == 'refuted':
        return 'refuted'
    if RANK.get(incoming, 0) > RANK.get(current, 0):
        return incoming
    if RANK.get(current, 0) == 0 and incoming in ('inapplicable', 'undetermined'):
        return incoming
    return current or incoming


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
    before = _get(prior, 'proof_status', '')
    if before == 'refuted' and status != 'refuted':
        after = 'refuted'   # a counterexample outranks a later witness on the same build
    elif before in ('decided', 'proved') and status != 'refuted':
        after = before      # sc-2: a formal decision is not lowered by a later witness (one more interleaving)
    else:
        after = status
    ce = {}
    if status == 'refuted':
        ce = {'cycle': run['fault_cycle'], 'pc': run['fault_pc'], 'pc_symbol': run['fault_symbol'], 'landed_pc': run['landed_pc'],
              'landed_symbol': run['landed_symbol'], 'torn_value': run['torn_value'], 'expected_value': run['expected_value'],
              'uptime_sequence': run['uptime_sequence'], 'trace_sha256': run['trace_sha256'], 'run': run['name'],
              'observed': run.get('observable_value', ''), 'words': run['verdict_words'][:400]}
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
        'provenance': 'firmwarefaults runner (FIRMWARE_SCENARIO_PLAN.md §1, sc-0/sc-1): a sim-tier witness/counterexample, never a proof',
        'notes': run['verdict_words'],
        'evidence_tiers_json': json.dumps(merge_tier(_tiers(prior), {'tier': 'sim', 'status': status, 'ref': run['name'], 'at': run['ran_at'],
                                                                     'measure': run.get('observable_value', '') or run['verdict_words'][:160]})),
        'measure_json': _get(prior, 'measure_json', '{}') or '{}',
    }
    if after in ('decided', 'proved') and prior is not None:   # keep the formal tier's checker / certificate on the claim
        fields.update(checker=_get(prior, 'checker', 'cbmc'), certificate_ref=_get(prior, 'certificate_ref', ''),
                      evidence_level=_get(prior, 'evidence_level', 'analytical'))
    sink.upsert('MathClaim', fields)
    verdict = {'witnessed': 'holds', 'refuted': 'refuted', 'inapplicable': 'inapplicable', 'undetermined': 'undetermined'}[status]
    sink.upsert('ProofRun', {
        'name': '%s@sim@%s' % (name, run['ran_at']), 'description': 'scenario run %s' % run['name'], 'claim': name, 'checker': 'sim',
        'checker_version': harness_version or run['harness_digest'], 'verdict': verdict,
        'detail_json': json.dumps({'run': run['name'], 'outcome': run['outcome'], 'words': run['verdict_words'], 'counterexample': ce}),
        'output_tail': run['uptime_sequence'][-400:], 'elapsed_s': run['wall_s'], 'rows_state_hash': run['firmware_sha256'],
        'ran_at': run['ran_at'], 'ran_where': run['harness_digest'], 'notes': 'kept beside a refuted claim' if before == 'refuted' and status != 'refuted' else ''})
    return name, after, before


def add_evidence(sink, name, entry, base=None, counterexample=None, measure=None, checker=None, certificate=None):
    """sc-2: one tier speaks to claim `name` (created with `base` fields when absent — a CLI run has no server's claims).
    entry = {tier, status, ref, measure, …}. A formal `decided` / `refuted` sets proof_status (checker cbmc, evidence
    analytical); a statistics entry leaves the status and writes `measure` into measure_json. Returns (before, after)."""
    prior = sink.get('MathClaim', name)
    before = _get(prior, 'proof_status', '') or 'conjectured'
    entry = dict(entry, at=entry.get('at') or datetime.datetime.now().isoformat(timespec='seconds'))
    tiers = merge_tier(_tiers(prior), entry)
    fields = dict(base or {}) if prior is None else {}
    fields.update(name=name, evidence_tiers_json=json.dumps(tiers, default=str))
    if prior is None:
        fields.setdefault('kind', 'safe-under-scenario')
        fields.setdefault('statement_json', '{}')
        fields.setdefault('checker', '')
    after = before
    if entry['tier'] == 'formal':
        after = strongest(before, entry['status'])
        if after != before or entry['status'] == 'refuted':
            fields.update(proof_status=after)
            if entry['status'] in ('decided', 'refuted') and after == entry['status'] and before != after:   # the first refuter keeps its name
                fields.update(checker=checker or 'cbmc', certificate_ref=certificate or entry.get('ref', ''), evidence_level='analytical')
            if entry['status'] == 'refuted' and before != 'refuted' and counterexample is not None:
                fields.update(counterexample_json=json.dumps(counterexample, default=str))
        elif prior is None:
            fields.update(proof_status=after)
    elif prior is None:
        fields.update(proof_status=before)
    if measure is not None:
        m = {}
        try:
            m = json.loads(_get(prior, 'measure_json', '{}') or '{}')
        except ValueError:
            m = {}
        m[entry['tier']] = measure
        fields.update(measure_json=json.dumps(m, default=str))
    if isinstance(prior, dict):     # the local sink replaces a row whole — carry the rest of the claim over
        fields = dict(prior, **fields)
    sink.upsert('MathClaim', fields)
    return before, after
