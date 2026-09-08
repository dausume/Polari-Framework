"""
@module testing.check_catalog

acct-0: the registration layer — every existing test surface appears
in the capability matrix exactly once, by DISCOVERY, not by a hand
list that drifts:

  suite:<name>       tests/test_*.py unittest files (the container
                     suite run_tests.py discovers).
  selftest:<pkg>.<topic>
                     every <package>/selftest_*.py at package root.
  live:api-smoke     tests/live_api_smoke.py against a live server
                     (skip-honest when none is reachable).
  gate:normal-build-absence
                     the pinned assert that a NORMAL build carries
                     zero test machinery (testing.custom.absence_probe).

Categories follow the plan's spine: substrate | transport | format |
twin | nocode | engine | module. Criticality: substrate/transport/
twin rows are blocking (plan §4) — blocking_green gates on them —
everything else is visible, non-blocking debt. New test files
auto-appear on the matrix at the defaults below; refine a row's
category/criticality here when a phase claims it.
"""

import os

# mp-4: this module may live at the framework root OR under
# modules/ (the second import root) — the framework root is the
# directory that actually carries tests/.
FRAMEWORK_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(FRAMEWORK_ROOT) == 'modules':
    FRAMEWORK_ROOT = os.path.dirname(FRAMEWORK_ROOT)

# A package's selftests inherit its category ('module' if unlisted).
CATEGORY_BY_PACKAGE = {
    'polariDBmanagement': 'substrate',
    'polariDataTyping': 'substrate',
    'grpcbridge': 'transport',
    'polariRefs': 'twin',
    'polariPeers': 'twin',
    'simulationLocks': 'twin',
    'topology': 'twin',
    'polariNoCode': 'nocode',
    'hwdigital': 'hwdigital',
    'electrodevice': 'circuit',
    'dmvdata': 'format',
    'matrices': 'engine',
    'simulations': 'engine',
    'simSpace': 'engine',
}

# tests/test_<stem>.py -> category.
CATEGORY_BY_SUITE = {
    'object_tree': 'substrate',
    'crude_api': 'transport',
    'api_contracts': 'transport',
    'api_honesty': 'transport',
    'api_sweep': 'transport',
    'api_profiler': 'transport',
    'createclass_api': 'nocode',
    'mathshapes': 'module',
    'modules_smoke': 'module',
}

BLOCKING_CATEGORIES = frozenset({'substrate', 'transport', 'twin'})

# Name-level category overrides (win over the package rule) — for
# testing/'s own phase selftests, which pin seams in OTHER packages.
CATEGORY_OVERRIDES = {
    'selftest:testing.formats': 'format',
    'selftest:testing.stomp': 'transport',
    # ncg-2: the judicial client is the standing litmus that the
    # no-code generalization seam still serves its first domain.
    'selftest:scoring.court_case_basis': 'nocode',
    # ncg-7: the levels must keep splitting across small nodes.
    'selftest:testing.ncg_split': 'nocode',
    # ncg-7: the levels as PolariModule objects (export -> store ->
    # dynamic load into a running instance).
    'selftest:polariPeers.ncg_modules': 'nocode',
    # API-profiler schema-drift adaptation + relocation discovery
    # (Dustin 2026-07-16): deterministic in-process golden behavior
    # over an emulated external API — a format concern.
    'selftest:polariApiProfiler.profiler_drift': 'format',
}

# Per-check criticality overrides (win over the category rule).
CRITICALITY_OVERRIDES = {
    # ncg-0: the old no-code must PROVABLY keep working while the
    # generalization workstream (judicial + circuits) builds on it —
    # the seven engine selftests + the P5 TS parity leg + the
    # editor/engine drift sweep gate every phase (Dustin 2026-07-16).
    'selftest:polariNoCode.turing': 'blocking',
    'selftest:polariNoCode.composition': 'blocking',
    'selftest:polariNoCode.parity': 'blocking',
    'selftest:polariNoCode.display_flow': 'blocking',
    'selftest:polariNoCode.matrixop': 'blocking',
    'selftest:polariNoCode.engine_model_op': 'blocking',
    'selftest:polariNoCode.pendulum_embed': 'blocking',
    # ncg-1: the promoted builder + compiler/orchestrator seam is
    # what every domain compiler (judicial, circuits) builds through
    # — it gates like the engine gates it wraps.
    'selftest:polariNoCode.graph_builder': 'blocking',
    'selftest:scoring.court_case_basis': 'blocking',
    'selftest:testing.nocode_matrix': 'blocking',
    # ncg-3: the digital-logic client of the seam — python reference
    # + verilated bench agreement + real iCE40 synthesis (tool legs
    # skip-honest inside containers).
    'selftest:hwdigital.logic': 'blocking',
    # ncg-4: rows must keep reproducing the hand-renderer currents
    # (real ngspice leg; skip-honest without the binary).
    'selftest:electrodevice.circuit_rows': 'blocking',
    # ncg-5: placements/jumpers/board-as-component must keep
    # conducting the proven current (real ngspice leg).
    'selftest:electrodevice.breadboard': 'blocking',
    # ncg-6: the cross-level bridge + the authorable test packs.
    'selftest:electrodevice.level_bridge_basis': 'blocking',
    'selftest:polariNoCode.nocode_tests': 'blocking',
    'selftest:testing.ncg_split': 'blocking',
    'selftest:polariPeers.ncg_modules': 'blocking',
    'selftest:polariApiProfiler.profiler_drift': 'blocking',
    # col-1: the DMV vocabulary (personas, statutes-as-data, escape
    # costs) — deterministic in-process; the scorecard's data floor.
    'selftest:scoring.dmv_col': 'blocking',
    # col-2: source registrations + the Census pull slice (live leg
    # skip-honest without network/POLARI_CENSUS_API_KEY).
    'selftest:dmvdata.dmv_sources': 'blocking',
    # GovSource registry: acronym glossary, key requirements,
    # retrieval attribution, term origins (Dustin 2026-07-16).
    'selftest:dmvdata.gov_sources_basis': 'blocking',
    # Cross-validation: independent re-pull confirmations raise
    # sourcing credibility; provider groups scored on reliability.
    'selftest:dmvdata.cross_validation_basis': 'blocking',
    # Legal source types: nonprofit/company/political-group/
    # individual siblings of GovSource, one cross-type machinery.
    'selftest:dmvdata.legal_sources_basis': 'blocking',
    # Policy drafts scoreable through their lifecycle + the venue-
    # mismatch pattern analysis (policy-via-budget-rider,
    # suppression-by-defunding) — findings land as scr-6 assertions.
    'selftest:scoring.policy_drafts_basis': 'blocking',
    'selftest:scoring.venue_patterns_basis': 'blocking',
    # Legislation tracking: drafting/vote rosters/provision
    # contributors + burial patterns; Congress.gov + VA LIS
    # registered, MD manual-entry by necessity (no official API).
    'selftest:scoring.legislation_basis': 'blocking',
    # Assertion credibility votes (group + individual units),
    # drafter-set PolicyIntent, org data-gathering solutions on the
    # graph seam, and the Term Competition system (scope eligibility
    # + legitimacy elections — the PSC termcompetition draft, built).
    'selftest:scoring.assertion_credibility_basis': 'blocking',
    'selftest:scoring.policy_intent_basis': 'blocking',
    'selftest:scoring.data_gathering_basis': 'blocking',
    'selftest:scoring.term_competition_basis': 'blocking',
    # Democratic term proofs: rebuttable, re-runnable demonstrations
    # with validity + comprehension votes and the manipulation
    # catalog (neutral computable exposure checks).
    'selftest:scoring.term_proofs_basis': 'blocking',
    # Credibility bases: professional/impact/methodological standing
    # per domain, affiliations disclosed inline, kinds never
    # collapsed into one number.
    'selftest:scoring.credibility_bases_basis': 'blocking',
    'nocode:variant-sweep': 'blocking',
    'nocode:ts-parity': 'blocking',
    # Known matcher drift (prf-test-suites 2026-07-11) — visible
    # debt, not a pipeline gate, until the profiler row is repaired.
    'suite:api-profiler': 'informational',
    # The spine must be able to test itself before anything gates
    # on it, and the normal-build absence is a Dustin non-negotiable.
    'selftest:testing.testing': 'blocking',
    'selftest:testing.substrate': 'blocking',
    'selftest:testing.transports': 'blocking',
    'gate:normal-build-absence': 'blocking',
    # acct-2: format golden shapes are deterministic in-process pins
    # — drift should gate even though `format` isn't a blocking
    # category by default.
    'selftest:testing.formats': 'blocking',
    # Registered for grpc-3 (one implementation, not two): visible
    # debt, non-blocking until grpc-3 lands — flip these then.
    'transport:grpc-parity-measurement': 'informational',
    'transport:grpc-peer-watch': 'informational',
}

DEFAULT_LIVE_BASE_URL = 'https://api.prf.192.168.0.210.nip.io'


def _criticality(name, category):
    if name in CRITICALITY_OVERRIDES:
        return CRITICALITY_OVERRIDES[name]
    return ('blocking' if category in BLOCKING_CATEGORIES
            else 'informational')


def _entry(name, category, kind, runner_kind, runner_ref, description):
    return {'name': name, 'category': category, 'kind': kind,
            'criticality': _criticality(name, category),
            'runner_kind': runner_kind, 'runner_ref': runner_ref,
            'description': description}


def _suite_entries():
    tests_dir = os.path.join(FRAMEWORK_ROOT, 'tests')
    entries = []
    for fname in sorted(os.listdir(tests_dir)):
        if not (fname.startswith('test_') and fname.endswith('.py')):
            continue
        stem = fname[len('test_'):-len('.py')]
        entries.append(_entry(
            name='suite:' + stem.replace('_', '-'),
            category=CATEGORY_BY_SUITE.get(stem, 'module'),
            kind='in-process', runner_kind='unittest',
            runner_ref=f'python3 -m unittest tests.test_{stem}',
            description=f'Container-suite unittest file tests/{fname}.'))
    return entries


def _selftest_entries():
    # mp-4: packages live at the framework root AND under modules/
    # (the second import root) — scan both, plain import names.
    roots = [FRAMEWORK_ROOT]
    modules_root = os.path.join(FRAMEWORK_ROOT, 'modules')
    if os.path.isdir(modules_root):
        roots.append(modules_root)
    entries = []
    for root in roots:
      for pkg in sorted(os.listdir(root)):
        pkg_dir = os.path.join(root, pkg)
        if (pkg.startswith('.') or pkg in ('tests', 'modules')
                or not os.path.isdir(pkg_dir)
                or not os.path.isfile(
                    os.path.join(pkg_dir, '__init__.py'))):
            continue
        for fname in sorted(os.listdir(pkg_dir)):
            if not ((fname.startswith('selftest_') or fname.endswith('_selftest.py'))
                    and fname.endswith('.py')):
                continue
            topic = (fname[len('selftest_'):-len('.py')] if fname.startswith('selftest_')
                     else fname[:-len('_selftest.py')])  # sap-2: <topic>_selftest.py is the standard
            module = f'{pkg}.selftest_{topic}'
            entries.append(_entry(
                name=f'selftest:{pkg}.{topic}',
                category=CATEGORY_BY_PACKAGE.get(pkg, 'module'),
                kind='in-process', runner_kind='selftest',
                runner_ref=f'python3 -m {module}',
                description=f'Module selftest {pkg}/{fname}.'))
    return entries


def _substrate_entries():
    """acct-1: live databases + cache. runner_ref is
    'module:function' for runner_kind 'callable'."""
    prefix = 'testing.custom.substrate_checks:'
    rows = [
        ('substrate:mariadb-reachability', 'live',
         'check_mariadb_reachability',
         'Connect + SELECT VERSION() on the live MariaDB.'),
        ('substrate:mariadb-credential-honesty', 'live',
         'check_mariadb_credential_honesty',
         'A wrong password must be refused (and the right one '
         'accepted) — the wrong-password-boots-healthy gotcha, '
         'pinned.'),
        ('substrate:mariadb-auto-tables', 'live',
         'check_mariadb_auto_tables',
         'The object-tree schema was auto-generated on the live '
         'server (>=150 tables).'),
        ('substrate:keydb-roundtrip', 'live',
         'check_keydb_roundtrip',
         "The framework's PolariCache setTable/getTable/"
         'invalidateTable round-trip against live KeyDB.'),
        ('substrate:dialect-parity', 'live',
         'check_dialect_parity',
         'The dbcombo proof, repeatable: the same unittest file '
         'must behave identically on sqlite and mariadb '
         '(throwaway schema).'),
        ('substrate:restart-persistence', 'compose',
         'check_restart_persistence',
         'Volume-backed data survives a real container restart — '
         'DISRUPTIVE, opt-in via POLARI_ALLOW_DISRUPTIVE=true.'),
    ]
    return [_entry(name=name, category='substrate', kind=kind,
                   runner_kind='callable', runner_ref=prefix + fn,
                   description=description)
            for name, kind, fn, description in rows]


def _transport_entries():
    """acct-2: live sidecar probes + the grpc-3 placeholders."""
    prefix = 'testing.custom.transport_checks:'
    rows = [
        ('transport:stomp-live-connect', 'live',
         'check_stomp_live_connect',
         'Real websocket CONNECT -> CONNECTED against the live '
         'STOMP sidecar (:3001 in prf-backend).'),
        ('transport:grpc-sidecar-reachability', 'live',
         'check_grpc_sidecar_reachability',
         'gRPC reflection list_services on the live sidecar '
         '(:3002); polari.sync.* count reported as evidence.'),
        ('transport:grpc-parity-measurement', 'live',
         'check_grpc_parity_measurement',
         'STOMP<->gRPC parity + measured efficiency — lands with '
         'grpc-3; registered so the debt is visible.'),
        ('transport:grpc-peer-watch', 'live',
         'check_grpc_peer_watch',
         'Peer-to-peer Watch via the class-directory grpcTarget — '
         'lands with grpc-3; registered so the debt is visible.'),
    ]
    return [_entry(name=name, category='transport', kind=kind,
                   runner_kind='callable', runner_ref=prefix + fn,
                   description=description)
            for name, kind, fn, description in rows]


def _nocode_entries():
    """ncg-0: per-node-type variant rows (container-stable set:
    backend registry ∪ python dispatch), the drift-sweep summary,
    and the TS-side parity leg. Import kept local — the enumeration
    touches polariNoCode, and the catalog module itself must stay
    import-light."""
    from testing.custom.nocode_checks import variant_class_names
    prefix = 'testing.custom.nocode_checks:'
    entries = [
        _entry(name=f'nocode:variant-{cls}', category='nocode',
               kind='in-process', runner_kind='callable',
               runner_ref=prefix + 'check_variant_' + cls,
               description=f'Editor/engine/palette drift check for '
                           f'node type {cls} — truthful stub labels '
                           f'pass, lying about capability fails.')
        for cls in variant_class_names()]
    entries.append(_entry(
        name='nocode:variant-sweep', category='nocode',
        kind='in-process', runner_kind='callable',
        runner_ref=prefix + 'check_variant_sweep',
        description='Set-level drift summary across every node-type '
                    'source (registry, engine dispatch, palette, '
                    'capability partition); palette-only classes '
                    'surface here.'))
    entries.append(_entry(
        name='nocode:ts-parity', category='nocode', kind='host',
        runner_kind='callable',
        runner_ref=prefix + 'check_ts_parity',
        description='P5 TS engine over the shared parity vectors '
                    '(`npm run parity`) — skip-honest without the '
                    'Angular checkout or npm.'))
    return entries


def _twin_entries():
    """acct-3: the compose-driven coherence rehearsal."""
    return [_entry(
        name='twin:rehearsal', category='twin', kind='compose',
        runner_kind='callable',
        runner_ref='testing.custom.twin_checks:check_twin_rehearsal',
        description='Throwaway core+m+n containers: module-gating '
                    'separation, directory routing (addressable '
                    'tie-break), rung-4 traversal, un-leased write '
                    'refusal, leased dual-journal remote write, '
                    'zombie fencing, clean teardown — the xsim-6/'
                    'modsplit rehearsal as one repeatable command.')]


def catalog_checks():
    """The full check catalog, deterministically ordered
    (category, name). Pure data — no manager, no side effects."""
    entries = (_suite_entries() + _selftest_entries()
               + _substrate_entries() + _transport_entries()
               + _nocode_entries() + _twin_entries())
    for entry in entries:
        override = CATEGORY_OVERRIDES.get(entry['name'])
        if override:
            entry['category'] = override
            entry['criticality'] = _criticality(entry['name'],
                                                override)
    entries.append(_entry(
        name='live:api-smoke', category='transport', kind='live',
        runner_kind='live-smoke',
        runner_ref='python3 tests/live_api_smoke.py <base-url>',
        description='22-endpoint smoke against a LIVE server. '
                    'skip-honest when no server is reachable.'))
    entries.append(_entry(
        name='gate:normal-build-absence', category='module',
        kind='in-process', runner_kind='absence',
        runner_ref='python3 -m testing.custom.absence_probe',
        description='Pinned: a NORMAL build (no POLARI_TEST_BUILD, '
                    'testing absent from POLARI_MODULES) registers '
                    'zero test machinery — no classes, tables, '
                    'CRUDE surface, or /api/accountability route.'))
    entries.sort(key=lambda e: (e['category'], e['name']))
    return entries


def catalog_by_name():
    return {e['name']: e for e in catalog_checks()}
