"""ret-1 selftest: pure invariants over the reticulum module — the
vocabulary, the rules (admission, routing lawfulness, freshness,
replication algebra, licence ladder), the ret-8 seam, and the FIVE
registrations a manifest-first module needs (miss one and seeds
silently vanish — the standing gotcha).

Run in-container: pol modules selftest reticulum
(python3 -m reticulum.selftest_reticulum)
No server, no network, no RNS import — the stack lives in the sidecar.
"""

import inspect
import json
import os

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    suffix = f' [{extra}]' if extra and not cond else ''
    print(f'  [{PASS if cond else FAIL}] {label}{suffix}')


RETICULUM_CLASSES = (
    'ReticulumIdentity', 'ReticulumDestination', 'ReticulumInterface',
    'TransportBinding', 'LinkMeasurement', 'AirtimeBudget',
    'ArchipelagoNode', 'ArchipelagoTrust',
    'WatchedObject', 'ObjectStateVersion', 'StateConflict',
    'OperatorLicense', 'DeviceLink', 'DeviceModel',
)
RETICULUM_SEEDS = ('SEED_RNS_INTERFACES', 'SEED_DEVICE_MODELS')


def run():
    from reticulum import arch_basis as ab
    from reticulum import operator_basis as ob
    from reticulum import replication_basis as pb
    from reticulum import reticulum_basis as rb

    # -- vocabulary is pinned (rows declare against these) ---------------
    check('two mesh encodings + the middle option (DECIDED row 4: '
          'STOMP is OUT)',
          rb.ENCODING_VALUES == ('grpc', 'json', 'cbor')
          and 'stomp' not in rb.ENCODING_VALUES)
    check('regulatory domains include amateur + ism, and none for '
          'wired links',
          set(('none', 'ism', 'amateur')) <= set(
              rb.REGULATORY_DOMAIN_VALUES))
    check('rx/tx is a device fact vocabulary (§5i)',
          rb.INTERFACE_DIRECTION_VALUES == ('rx', 'tx', 'both'))
    check('LoRa is ONE bearer among many (§5d) — nothing above the '
          'interface may assume it',
          'rnode-lora' in rb.BEARER_VALUES
          and 'wifi-halow' in rb.BEARER_VALUES
          and 'tcp' in rb.BEARER_VALUES)
    check('fidelity separates declared from measured, and VM numbers '
          'are labelled (§5h)',
          rb.FIDELITY_VALUES == ('declared', 'measured-vm',
                                 'measured-real'))
    check('publication classes default-most-restrictive vocabulary '
          '(§5g item 3)',
          pb.PUBLICATION_CLASS_VALUES == ('local-only', 'mesh-only',
                                          'public'))
    check('conflict policy includes propose (the one that fits this '
          'suite) and it is the class default',
          'propose' in pb.CONFLICT_POLICY_VALUES
          and inspect.signature(pb.WatchedObject.__init__)
          .parameters['conflict_policy'].default == 'propose')
    check('WatchedObject defaults publication_class to local-only '
          '(most restrictive)',
          inspect.signature(pb.WatchedObject.__init__)
          .parameters['publication_class'].default == 'local-only')
    check('identity binds at INSTANCE level by default (§6 assumption) '
          'with kc_subject nullable',
          inspect.signature(rb.ReticulumIdentity.__init__)
          .parameters['kind'].default == 'instance'
          and inspect.signature(rb.ReticulumIdentity.__init__)
          .parameters['kc_subject'].default == '')
    check('no private-key field exists on ReticulumIdentity — only a '
          'location label',
          'key_location' in inspect.signature(
              rb.ReticulumIdentity.__init__).parameters
          and not any('private' in p or p.endswith('_key')
                      for p in inspect.signature(
                          rb.ReticulumIdentity.__init__).parameters))

    # -- names travel into configs/DNS: one safe segment -----------------
    check('safe_mesh_name accepts ordinary names',
          rb.safe_mesh_name('isle-b.arch') and rb.safe_mesh_name('m2'))
    check('safe_mesh_name refuses traversal, blanks and separators',
          not rb.safe_mesh_name('') and not rb.safe_mesh_name('a/b')
          and not rb.safe_mesh_name('a..b')
          and not rb.safe_mesh_name('.hidden'))

    # -- §5e: freshness, derived timeouts, per-path capability -----------
    check('a fact inside the horizon is fresh; outside is not',
          rb.measurement_fresh(1_000_000, 1_800_000)
          and not rb.measurement_fresh(1_000_000, 2_000_001))
    check('no timestamp is never fresh (absence of a fact is not a '
          'fact)', not rb.measurement_fresh(0, 500))
    check('timeouts DERIVE from measured RTT with margin + floor',
          rb.derive_timeout_ms(2000) == 8000
          and rb.derive_timeout_ms(10) == 2000)
    check('no measurement -> no timeout (refuse, never a constant)',
          rb.derive_timeout_ms(0) is None
          and rb.derive_timeout_ms(None) is None)
    cap = rb.capability_for_path(None, 0)
    check('capability with no path fact answers unknown-measure-first',
          cap['known'] is False and 'measure first' in cap['reason'])
    lora_path = {'measured_at_ms': 100, 'throughput_bps': 1200,
                 'rtt_ms': 4000, 'hop_count': 4,
                 'worst_hop_bearer': 'rnode-lora', 'fidelity':
                 'measured-real'}
    cap = rb.capability_for_path(lora_path, 200)
    check('a 1.2 kbps 4-hop path: gRPC unary yes, streaming refused '
          'WITH the numbers',
          cap['known'] and cap['grpc_unary']
          and not cap['grpc_streaming']
          and '1200 bps' in cap['grpc_streaming_reason'])
    check('capability carries its evidence (worst hop named)',
          cap['evidence']['worst_hop_bearer'] == 'rnode-lora')

    # -- airtime is LEDGERED, never assumed ------------------------------
    check('airtime cost computes from bitrate',
          rb.airtime_ms(100, 1000) == ((100 + 40) * 8 * 1000) // 1000)
    check('unknown bitrate -> no cost -> refusal, not a guess',
          rb.airtime_ms(100, 0) is None
          and not rb.budget_admits(0, 1000, None))
    check('a budget admits until it is spent',
          rb.budget_admits(0, 1000, 999)
          and not rb.budget_admits(500, 1000, 501))
    check('no declared budget on a bearer = refusal, not a free pass',
          not rb.budget_admits(0, 0, 10))

    # -- the two lawfulness refusals (§5f/§5g), by name -------------------
    ok, _ = rb.may_route('public', 'ism', True)
    check('encrypted + ISM routes fine', ok)
    ok, why = rb.may_route('public', 'amateur', True)
    check('encrypted on amateur is REFUSED with the rule cited',
          not ok and 'encrypted' in why and 'amateur' in why)
    ok, why = rb.may_route('mesh-only', 'amateur', False)
    check('non-public state on amateur is REFUSED by name (a HAM '
          'broadcast is public and permanent)',
          not ok and 'mesh-only' in why and 'public' in why.lower())
    ok, _ = rb.may_route('public', 'amateur', False)
    check('public + cleartext on amateur is the lawful ham shape',
          ok)

    # -- admission is a pure rule with three-key refusals -----------------
    policy = {'max_message_bytes': 256}
    ok, refusal = rb.admit_binding(policy, None, 100, 0)
    check('no path fact -> refused with evidence+knob+action',
          not ok and set(refusal) == {'evidence', 'knob', 'action'})
    ok, refusal = rb.admit_binding(policy, lora_path, 300, 200)
    check('oversize payload refused naming both numbers',
          not ok and '300' in refusal['evidence']
          and '256' in refusal['evidence'])
    stale_path = dict(lora_path, measured_at_ms=1)
    ok, refusal = rb.admit_binding(policy, stale_path, 100,
                                   2_000_000)
    check('stale path fact refused: re-measure, then retry',
          not ok and 'stale' in refusal['evidence'])
    budget_path = dict(lora_path, budget_ms=100, consumed_ms=99)
    ok, refusal = rb.admit_binding(policy, budget_path, 100, 200)
    check('blown airtime budget refused, store-and-forward named as '
          'the action',
          not ok and 'budget' in refusal['evidence']
          and 'ret-7' in refusal['action'])
    ok, refusal = rb.admit_binding(policy, dict(lora_path,
                                                budget_ms=100_000), 100,
                                   200)
    check('a healthy fresh path under budget ADMITS', ok
          and refusal is None)

    # -- .arch: graded trust, never boolean; measured reachability --------
    check('trust grades are a ladder, not a boolean',
          ab.TRUST_GRADE_VALUES == ('observe', 'gossip', 'telemetry',
                                    'propose', 'propose-low-preapproved'))
    check('no grade auto-approves above level 3 (authority never rides '
          'trust to network-service)',
          max(ab.effective_auto_level(g)
              for g in ab.TRUST_GRADE_VALUES) == 3)
    check('an unknown grade gets level 0, never guessed into authority',
          ab.effective_auto_level('best-friend') == 0)
    check('reachable_now is a timestamped measurement, not a hope',
          ab.reachable_now({'last_heard_ms': 100}, 200)
          and not ab.reachable_now({'last_heard_ms': 0}, 200)
          and not ab.reachable_now({'last_heard_ms': 100}, 2_000_000))

    # -- replication algebra (§5f) ----------------------------------------
    check('conflict detected exactly when both sides moved',
          pb.detect_conflict(5, 7) and not pb.detect_conflict(5, 5))
    check('no baseline -> not a conflict (a late joiner needs a '
          'keyframe)', not pb.detect_conflict(0, 7))
    check('a delta is only usable against the exact parent',
          pb.delta_usable(5, 5) and not pb.delta_usable(5, 4)
          and not pb.delta_usable(0, 5))
    check('hash+version make a repeat a no-op (lossy links retry '
          'safely)',
          pb.repeat_is_noop(5, 'h', 5, 'h')
          and not pb.repeat_is_noop(5, 'h', 5, 'g')
          and not pb.repeat_is_noop(0, '', 0, ''))
    check('keyframe cadence: every Nth, and N<=1 means every send '
          '(the receive-only default)',
          pb.keyframe_due(10, 10) and not pb.keyframe_due(11, 10)
          and pb.keyframe_due(3, 1) and pb.keyframe_due(3, 0))

    # -- operator licence: recorded assertion, tracked expiry -------------
    check('licence ladder: valid / approaching / expired / undated',
          ob.license_state('2027-01-01', '2026-08-13') == 'valid'
          and ob.license_state('2026-09-01', '2026-08-13')
          == 'approaching-expiry'
          and ob.license_state('2026-08-01', '2026-08-13') == 'expired'
          and ob.license_state('', '2026-08-13') == 'undated'
          and ob.license_state('not-a-date', '2026-08-13') == 'undated')
    check('warnings NAME what is missing and never claim law',
          'no operator licence on file' in ob.license_warning('none')
          and 'never validated online' in ob.license_warning('none')
          and ob.license_warning('valid') == '')
    check('rx-only devices never offer transmit (§5i)',
          not ob.offers_transmit('rx') and ob.offers_transmit('both'))
    check('an unknown device is reported unknown WITH its ids, never '
          'guessed',
          ob.describe_device('0403', '6001', 'unknown')
          == 'unknown (usb 0403:6001)'
          and ob.describe_device('', '', 'lora-board') == 'lora-board')

    # -- the TX legality gate (Dustin 2026-08-13) -------------------------
    base_iface = {'enabled': True, 'direction': 'both',
                  'regulatory_domain': 'ism'}
    ok, refusal = rb.tx_permitted(dict(base_iface))
    check('an RF interface with NO operator confirmation refuses TX '
          'naming the knob',
          not ok and 'tx_legal_confirmed' in refusal['knob']
          and set(refusal) == {'evidence', 'knob', 'action'})
    ok, _ = rb.tx_permitted(dict(base_iface, tx_legal_confirmed=True))
    check('a confirmed RF interface may transmit', ok)
    ok, _ = rb.tx_permitted({'enabled': True, 'direction': 'both',
                             'regulatory_domain': 'none'})
    check('wired links (regulatory none) are not legality-gated', ok)
    ok, refusal = rb.tx_permitted({'enabled': True, 'direction': 'rx',
                                   'regulatory_domain': 'ism',
                                   'tx_legal_confirmed': True})
    check('an rx-only device never transmits, confirmation or not',
          not ok and 'direction' in refusal['knob'])
    ok, refusal = rb.tx_permitted({'enabled': False})
    check('a disabled interface refuses before anything else',
          not ok and 'enabled' in refusal['knob'])

    # -- device catalog (Dustin 2026-08-13) -------------------------------
    from reticulum import device_catalog_basis as dc
    check('catalog vocabularies carry the SH-L1A lessons: rebadge-'
          'aware openness + closed-same-model interop',
          'documented-via-oem' in dc.PROTOCOL_OPENNESS_VALUES
          and 'closed-same-model' in dc.INTEROP_VALUES
          and 'flashable-open' in dc.FIRMWARE_OPENNESS_VALUES)
    ok, why = dc.model_vouches({'status': 'usable',
                                'firmware_openness': 'unstated',
                                'protocol_openness': 'documented',
                                'interop': 'open-standard'})
    check('a catalog row with an UNSTATED openness field refuses to '
          'vouch', not ok and 'firmware_openness' in why)
    check('blocked/unevaluated rows never vouch',
          not dc.model_vouches({'status': 'unevaluated'})[0])
    sh = dict(dc.SEED_DEVICE_MODELS[0])
    check('the SH-L1A seed row vouches (all facts stated)',
          dc.model_vouches(sh)[0])
    ok, why = dc.interop_possible(sh, {'name': 'rnode-generic',
                                       'interop': 'open-standard'})
    check('closed-same-model refuses cross-model links BY NAME',
          not ok and 'dsd-tech-sh-l1a' in why)
    check('same-model pairs interop; unknown refuses',
          dc.interop_possible(sh, dict(sh))[0]
          and not dc.interop_possible(sh, {'name': 'x'})[0])
    restrictions = json.loads(sh['restrictions_json'])
    check('SH-L1A restrictions carry the regulatory trap (ships '
          'out-of-US-band) + buffering + interop + identity',
          {r['kind'] for r in restrictions}
          == {'regulatory', 'buffering', 'interop', 'identity'}
          and any('873.125' in r['detail'] for r in restrictions))
    check('SH-L1A records its OEM lineage (rebadged EByte E220)',
          sh['oem_vendor'] == 'EByte' and 'E220' in sh['oem_model'])
    steps = json.loads(sh['setup_steps_json'])
    check('setup steps record the unplug-flip-replug config-mode '
          'entry (Dustin verified 2026-08-13)',
          any('UNPLUG' in s['detail'] and 'Config' in s['detail']
              for s in steps)
          and any('antenna' in s['step'] for s in steps))
    check('every load-bearing catalog fact carries evidence with a '
          'source',
          all('source' in e and e['source']
              for e in json.loads(sh['evidence_json'])))

    # -- the seed is the ret-0 shape, disabled ----------------------------
    check('exactly one seeded interface: the ret-0-proven local TCP, '
          'DISABLED (declaring is not enabling)',
          len(rb.SEED_RNS_INTERFACES) == 1
          and rb.SEED_RNS_INTERFACES[0]['name'] == 'local-tcp'
          and rb.SEED_RNS_INTERFACES[0]['enabled'] is False
          and rb.SEED_RNS_INTERFACES[0]['regulatory_domain'] == 'none')
    check('no radio is seeded — hardware rows come from udev facts',
          all(row['bearer'] == 'tcp' for row in rb.SEED_RNS_INTERFACES))

    # -- the licence pins are surfaced facts ------------------------------
    from reticulum import rns_remote as rr
    check('stack pins are the gate\'s MIT pair (pins are LICENCE pins)',
          rr.STACK_PINS['rns'] == '0.9.4'
          and rr.STACK_PINS['lxmf'] == '0.6.3'
          and 'GATE' in rr.STACK_PINS['gate'].upper())
    check('the module itself never imports RNS (the licence boundary '
          'is the process boundary)',
          all('import RNS' not in open(os.path.join(
              os.path.dirname(__file__), f)).read()
              for f in ('reticulum_basis.py', 'arch_basis.py',
                        'replication_basis.py', 'operator_basis.py',
                        'rns_remote.py', 'reticulum_api.py')))
    check('refusal ladder carries the three keys',
          set(rr.unavailable_suggestion('x'))
          == {'evidence', 'knob', 'action'})

    # -- ret-8 seam: inbound mesh data proposes at level 4 ----------------
    from polariApiServer.ai_actions import _OP_LEVEL, classify, kernel
    check('rns_inbound is a KNOWN operation at network-service level 4',
          'rns_inbound' in _OP_LEVEL
          and classify('rns_inbound') == (4, 'network-service'))
    check('level 4 sits ABOVE the auto-approve ceiling (remote data '
          'never applies itself)',
          classify('rns_inbound')[0] > 3
          or int(os.environ.get('POLARI_AUTO_MAX_LEVEL', '3')) < 4)
    proposal = kernel.propose(
        'rns_inbound', 'selftest inbound gossip',
        {'archName': 'isle-b.arch', 'kind': 'gossip',
         'payload': {'modules': []}})
    check('propose returns a DRY RUN carrying level 4',
          proposal['dry_run'] is True
          and proposal['authority_level'] == 4)
    check('nothing is applied without an explicit confirm',
          not kernel.execute(proposal['proposal_id'], False).get('ok'))

    # -- registration 1: the feature-import manifest ---------------------
    from polariApiServer.feature_imports import FEATURE_IMPORT_BLOCKS
    blocks = [entries for mod, entries in FEATURE_IMPORT_BLOCKS
              if mod == 'reticulum']
    check('feature_imports has exactly one reticulum block',
          len(blocks) == 1)
    declared = tuple(sorted(sym for _m, syms in (blocks[0] if blocks
                            else ()) for sym in syms))
    check('manifest declares exactly the reticulum classes + seed '
          'lists',
          declared == tuple(sorted(RETICULUM_CLASSES
                                   + RETICULUM_SEEDS)),
          f'declared={declared}')

    # -- registration 2: the endpoint constructor ------------------------
    from polariApiServer.module_endpoints import (
        MODULE_ENDPOINT_CONSTRUCTORS)
    check('module_endpoints carries a reticulum constructor',
          'reticulum' in MODULE_ENDPOINT_CONSTRUCTORS)

    # -- registration 3: the module registry JSON ------------------------
    registry_path = os.path.join(os.path.dirname(__file__), '..',
                                 'polari-modules.json')
    with open(registry_path) as f:
        registry = json.load(f)
    row = registry.get('modules', {}).get('reticulum')
    check('polari-modules.json knows reticulum', row is not None)
    check('registry row: official, downloaded, right path, wave 9',
          row and row.get('kind') == 'official' and row.get('downloaded')
          and row.get('path') == 'modules/reticulum'
          and row.get('wave') == 9)

    # -- registration 4: FEATURE_MODULES ---------------------------------
    from moduleService.module_loading import FEATURE_MODULES
    check('FEATURE_MODULES contains reticulum',
          'reticulum' in FEATURE_MODULES)

    # -- registration 5: defClassList (the silent-vanish gotcha) ---------
    server_src = open(os.path.join(
        os.path.dirname(__file__), '..', '..', 'polariApiServer',
        'polariServer.py')).read()
    missing = [c for c in RETICULUM_CLASSES if c not in server_src]
    check('every reticulum class appears in polariServer (defClassList '
          '+ seed_pairs — miss one and seeds silently never land)',
          not missing, f'missing={missing}')

    failed = sum(1 for r in _results if not r)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    run()
