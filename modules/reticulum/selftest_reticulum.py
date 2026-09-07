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
    'AppArchExposure', 'MeshAppRelay', 'MeshConsumer',
    'AppDataRule', 'QuarantinedSubmission', 'PeerSighting',
    'KitProfile',
    'MeshSimScenario', 'MeshSimNode', 'MeshSimResult',
)
RETICULUM_SEEDS = ('SEED_RNS_INTERFACES', 'SEED_DEVICE_MODELS',
                   'SEED_KIT_PROFILES')


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

    # -- wifi assignment knob (Dustin 2026-08-14) -------------------------
    check('wifi assignment vocabulary: exclusive roles + three dual '
          'flavors, defaulting unassigned',
          ob.WIFI_ASSIGNMENT_VALUES == (
              'unassigned', 'reticulum', 'onboarding-ap',
              'dual-one-network', 'dual-ap-sta', 'dual-switched')
          and inspect.signature(ob.DeviceLink.__init__)
          .parameters['wifi_assignment'].default == 'unassigned')
    check('unassigned refuses BOTH uses — assignment is deliberate',
          not ob.wifi_use_allowed('unassigned', 'reticulum')[0]
          and not ob.wifi_use_allowed('unassigned', 'onboarding-ap')[0])
    check('exclusive assignments serve their use and refuse the other '
          'by name',
          ob.wifi_use_allowed('reticulum', 'reticulum')[0]
          and not ob.wifi_use_allowed('reticulum', 'onboarding-ap')[0]
          and 'reticulum-only' in ob.wifi_use_allowed(
              'reticulum', 'onboarding-ap')[1])
    check('dual-one-network serves both with no switching (RNS rides '
          'the AP\'s own network)',
          ob.wifi_use_allowed('dual-one-network', 'reticulum')[0]
          and ob.wifi_use_allowed('dual-one-network',
                                  'onboarding-ap')[0])
    check('dual-ap-sta REFUSES until the chipset fact is measured — '
          'unmeasured concurrency is a hope',
          not ob.wifi_use_allowed('dual-ap-sta', 'reticulum')[0]
          and ob.wifi_use_allowed('dual-ap-sta', 'reticulum',
                                  ap_sta_measured=True)[0])
    check('dual-switched allows but WARNS: a switch interrupts the '
          'other use',
          ob.wifi_use_allowed('dual-switched', 'onboarding-ap')[0]
          and 'interrupts' in ob.wifi_use_allowed(
              'dual-switched', 'onboarding-ap')[1])
    check('ap_capable/ap_sta_capable are unmeasured-empty by default '
          '(facts arrive by iw ingest, never assumption)',
          inspect.signature(ob.DeviceLink.__init__)
          .parameters['ap_capable'].default == ''
          and inspect.signature(ob.DeviceLink.__init__)
          .parameters['ap_sta_capable'].default == '')
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

    # -- idle radios are SILENT (Dustin 2026-08-13, DECIDED row 19) -------
    rf_idle = {'enabled': True, 'direction': 'both',
               'regulatory_domain': 'ism', 'tx_legal_confirmed': True}
    ok, why = rb.interface_may_attach(dict(rf_idle), active_uses=0)
    check('an idle silent-policy radio is not even ATTACHED — '
          'detached is the only guaranteed dark',
          not ok and 'detached' in why)
    check('the same radio attaches while actively used',
          rb.interface_may_attach(dict(rf_idle), active_uses=1)[0])
    check('rx-hold attaches idle (listening is free) but never '
          'announces idle',
          rb.interface_may_attach(
              dict(rf_idle, idle_policy='rx-hold'), 0)[0]
          and not rb.may_announce(
              dict(rf_idle, idle_policy='rx-hold'), 0))
    check('announces are TX: refused on an idle radio, permitted '
          'with an active use, always fine on wired',
          not rb.may_announce(dict(rf_idle), 0)
          and rb.may_announce(dict(rf_idle), 1)
          and rb.may_announce({'regulatory_domain': 'none'}, 0))
    check('hold-open is the deliberate exception — may announce '
          'idle, but ONLY with the legality confirmation',
          rb.may_announce(dict(rf_idle, idle_policy='hold-open'), 0)
          and not rb.may_announce(
              dict(rf_idle, idle_policy='hold-open',
                   tx_legal_confirmed=False), 0))
    check('ReticulumInterface defaults idle_policy to silent',
          inspect.signature(rb.ReticulumInterface.__init__)
          .parameters['idle_policy'].default == 'silent'
          and rb.IDLE_POLICY_VALUES == ('silent', 'rx-hold',
                                        'hold-open'))

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

    # -- arch topology view (ret-1b, §5m) ---------------------------------
    from reticulum import arch_topology as at
    d = at.binding_demand({'max_message_bytes': 200,
                           'max_rate_per_min': 6, 'encoding': 'grpc'})
    check('binding demand = bytes x rate per minute, labelled '
          'declared',
          d['bytesPerMin'] == 1200 and d['fidelity'] == 'declared')
    iface = {'name': 'lora0', 'declared_params_json':
             json.dumps({'air_rate_bps': 62500})}
    meas = [{'interface_name': 'lora0', 'throughput_bps': 6568,
             'measured_at_ms': 100, 'fidelity': 'measured-real'}]
    cap = at.device_capacity(iface, meas, [], 200)
    check('capacity pairs declared air rate with measured effective '
          '(overhead is real)',
          cap['declaredAirRateBps'] == 62500
          and cap['measuredThroughputBps'] == 6568
          and cap['bytesPerMinUsable'] == int(6568 / 8 * 60))
    cap = at.device_capacity(iface, meas, [], 2_000_000)
    check('a stale measurement is NOT capacity — unknown, measure '
          'first',
          cap['measuredThroughputBps'] is None
          and cap['staleMeasurements'] == 1
          and cap['bytesPerMinUsable'] is None)
    check('oversubscription is a NAMED finding with the arithmetic '
          'shown',
          at._oversubscription(2000, 1000)['state'] == 'oversubscribed'
          and '200%' in at._oversubscription(2000, 1000)['evidence']
          and at._oversubscription(500, 1000)['state'] == 'fits'
          and at._oversubscription(0, 1000)['state'] == 'idle'
          and at._oversubscription(500, None)['state'] == 'unknown')
    topo = at.assemble_arch_topology({
        'interfaces': [dict(iface, bearer='rnode-lora',
                            direction='both', enabled=True)],
        'device_links': [], 'device_models': [],
        'bindings': [{'name': 'b1', 'app_name': 'collab',
                      'max_message_bytes': 200, 'max_rate_per_min': 6,
                      'enabled': True}],
        'budgets': [],
        'measurements': [dict(meas[0], destination_name='isle-b',
                              rtt_ms=222.8, hop_count=1)],
        'arch_nodes': [{'name': 'isle-b', 'arch_name': 'isle-b.arch',
                        'node_kind': 'peer-isle',
                        'last_heard_ms': 100}],
        'isle_devices': [],
    }, 'isle-a', 200)
    check('assembly: local block carries devices+apps+verdict, peer '
          'block is reachable, path edge is fresh',
          topo['isles'][0]['kind'] == 'local'
          and topo['isles'][0]['apps'][0]['name'] == 'collab'
          and topo['isles'][0]['verdict']['state'] == 'fits'
          and topo['isles'][1]['reachableNow'] is True
          and topo['paths'][0]['fresh'] is True
          and topo['paths'][0]['rttMs'] == 222.8)
    check('unattributed bindings are shown as such, never guessed '
          'into an app',
          at.assemble_arch_topology(
              {'bindings': [{'name': 'x', 'max_message_bytes': 1,
                             'max_rate_per_min': 1}]},
              'i', 0)['isles'][0]['apps'][0]['name']
          == '(unattributed)')

    # -- the app access ladder (ret-1c, DECIDED row 20) -------------------
    from reticulum import meshapp_basis as mb
    check('the ladder is the reserved suffixes + web (isle -> arch '
          '-> mesh -> web), and KC linkage has NO required mode '
          '(the option not existing keeps the promise)',
          mb.APP_SCOPE_VALUES == ('isle', 'arch', 'mesh', 'web')
          and mb.KC_LINK_MODE_VALUES == ('disabled', 'optional')
          and 'required' not in mb.KC_LINK_MODE_VALUES)
    check('an isle-scoped app refuses arch/mesh/web callers by rung',
          not mb.scope_allows('isle', 'arch')[0]
          and not mb.scope_allows('isle', 'mesh')[0]
          and not mb.scope_allows('isle', 'web')[0]
          and mb.scope_allows('isle', 'isle')[0])
    check('an arch-scoped app serves its isles and its arch, not the '
          'wider mesh or the internet',
          mb.scope_allows('arch', 'isle')[0]
          and mb.scope_allows('arch', 'arch')[0]
          and not mb.scope_allows('arch', 'mesh')[0]
          and not mb.scope_allows('arch', 'web')[0])
    check('a .mesh app serves mesh and below but not the internet; '
          'a web app serves every rung; unknown scopes refuse',
          mb.scope_allows('mesh', 'mesh')[0]
          and mb.scope_allows('mesh', 'isle')[0]
          and not mb.scope_allows('mesh', 'web')[0]
          and mb.scope_allows('web', 'web')[0]
          and mb.scope_allows('web', 'isle')[0]
          and not mb.scope_allows('lagoon', 'isle')[0]
          and not mb.scope_allows('isle', 'lagoon')[0])
    check('roles: observer/user/relay-only/server, defaulting to '
          'receive-only presence (being a server is declared, never '
          'assumed); an app may hold SEVERAL exposure rows',
          mb.MESH_APP_ROLE_VALUES == ('observer', 'user',
                                      'relay-only', 'server')
          and inspect.signature(mb.AppArchExposure.__init__)
          .parameters['role'].default == 'observer')
    check('exposure defaults are the most restrictive rung, disabled',
          inspect.signature(mb.AppArchExposure.__init__)
          .parameters['scope'].default == 'isle'
          and inspect.signature(mb.AppArchExposure.__init__)
          .parameters['enabled'].default is False
          and inspect.signature(mb.MeshAppRelay.__init__)
          .parameters['kc_link_mode'].default == 'disabled')

    new, ev = mb.adaptive_cadence(60, [10, 12, 14, 200], 10, 600)
    check('cadence paces to the MEDIAN consumer return x headroom '
          '(one slow consumer does not stall the sea)',
          new == 30.0 and ev['medianReturn'] == 14
          and ev['samples'] == 4)
    new, ev = mb.adaptive_cadence(60, [], 10, 600)
    check('no returns -> drift toward the ceiling, rate-limited '
          '(broadcast survives silence)',
          new == 120.0 and 'no consumer returns' in ev['reason'])
    check('the floor always wins (the airtime budget\'s voice) and '
          'steps are rate-limited against oscillation',
          mb.adaptive_cadence(12, [1, 1, 1], 10, 600)[0] == 10
          and mb.adaptive_cadence(600, [1, 1], 10, 600)[0] == 300.0)
    check('census: over/under/as-expected are NAMED findings; no '
          'expectation is stated, not defaulted',
          mb.user_census(10, 40)['state'] == 'over'
          and mb.user_census(10, 4)['state'] == 'under'
          and mb.user_census(10, 12)['state'] == 'as-expected'
          and mb.user_census(0, 7)['state'] == 'no-expectation')
    check('a consumer\'s NAME is its Reticulum identity; kc_subject '
          'is empty unless opted in',
          inspect.signature(mb.MeshConsumer.__init__)
          .parameters['kc_subject'].default == ''
          and inspect.signature(mb.MeshConsumer.__init__)
          .parameters['kc_signed'].default is False)

    # -- per-app data rules (ret-1c: the inbound gate) --------------------
    from reticulum import datarule_basis as dr
    schema = {'candidate': 'str', 'rank': 'int'}
    check('strict typing: right shape passes, wrong type / missing / '
          'UNMATCHED fields refuse naming the field',
          dr.payload_matches_schema({'candidate': 'a', 'rank': 1},
                                    schema)[0]
          and 'not int' in dr.payload_matches_schema(
              {'candidate': 'a', 'rank': 'first'}, schema)[1]
          and 'missing' in dr.payload_matches_schema(
              {'candidate': 'a'}, schema)[1]
          and 'unmatched' in dr.payload_matches_schema(
              {'candidate': 'a', 'rank': 1, 'x': 1}, schema)[1].lower())
    check('bool is not int (the classic stuffing trick)',
          not dr.payload_matches_schema({'candidate': 'a',
                                         'rank': True}, schema)[0])
    rule = {'enabled': True, 'max_submission_bytes': 512,
            'max_submissions_per_window': 3, 'window_seconds': 3600,
            'schema_json': json.dumps(schema),
            'dedupe_field': 'candidate'}
    ok, f = dr.evaluate_submission(rule, 'id1',
                                   {'candidate': 'a', 'rank': 1},
                                   100, 0, set(), 0)
    check('a well-formed first submission is accepted',
          ok and f is None)
    checks = [
        ('no-rule', dr.evaluate_submission(None, 'i', {}, 1, 0,
                                           set(), 0)),
        ('oversize', dr.evaluate_submission(rule, 'i', {}, 600, 0,
                                            set(), 0)),
        ('over-rate', dr.evaluate_submission(
            rule, 'i', {'candidate': 'a', 'rank': 1}, 100, 3,
            set(), 0)),
        ('duplicate', dr.evaluate_submission(
            rule, 'i', {'candidate': 'a', 'rank': 2}, 100, 0,
            {'a'}, 0)),
    ]
    check('every refusal is CAUGHT with its named reason (no-rule / '
          'oversize / over-rate / duplicate — one ballot per box)',
          all(not ok and f['reason'] == want
              for want, (ok, f) in checks)
          and all(want in dr.QUARANTINE_REASON_VALUES
                  for want, _ in checks))
    check('a broken rule schema fails CLOSED (nothing passes a '
          'broken gate)',
          not dr.evaluate_submission(
              dict(rule, schema_json='{nope'), 'i',
              {'candidate': 'a', 'rank': 1}, 100, 0, set(), 0)[0])
    check('rules default disabled; quarantine keeps a BOUNDED sample',
          inspect.signature(dr.AppDataRule.__init__)
          .parameters['enabled'].default is False
          and 'payload_sample' in inspect.signature(
              dr.QuarantinedSubmission.__init__).parameters)

    # -- the actor: isle identity by default, KC when present (2026-09-07)
    from reticulum import discovery_basis as db
    ra = db.resolve_actor
    check('KC user always wins', ra({'sub': 'u1', 'username': 'dustin'},
                                    'isle', 'abcd' * 8)[1]['actor'] == 'dustin')
    check('isle identity is the default actor',
          ra(None, 'isle', 'abcdef0123456789ff')[1] ==
          {'actor': 'isle:abcdef0123456789', 'tier': 'isle'})
    check('instance name stands in without a sidecar, stated',
          ra(None, 'isle', '', 'prf-isle')[1]['actor'] == 'isle:prf-isle'
          and 'note' in ra(None, 'isle', '', 'prf-isle')[1])
    check('keycloak mode refuses with the knob named',
          not ra(None, 'keycloak', 'ab')[0]
          and 'RETICULUM_ACTOR_MODE' in ra(None, 'keycloak', 'ab')[1]['knob'])
    check('nothing to sign with → refusal', not ra(None, 'isle')[0])
    check('bad mode → refusal', not ra(None, 'lagoon', 'ab')[0])

    # -- peer discovery + adjudication (ret-1d, row 21) -------------------
    from reticulum import discovery_basis as db
    check('sighting lifecycle: unadjudicated is neither .arch nor '
          '.mesh — a question, not a member',
          db.SIGHTING_STATUS_VALUES == ('unadjudicated',
                                        'archipelago', 'mesh',
                                        'ignored')
          and inspect.signature(db.PeerSighting.__init__)
          .parameters['status'].default == 'unadjudicated')
    s = {'status': 'unadjudicated', 'dest_hash': 'ab12',
         'last_heard_ms': 5}
    ok, changes = db.adjudicate(s, 'archipelago', 'dustin',
                                'barn-isle')
    check('admission to .arch creates the node, named, vouched, '
          'measured-real',
          ok and changes['createArchNode']['arch_name']
          == 'barn-isle.arch'
          and changes['createArchNode']['vouched_by'] == 'dustin'
          and changes['createArchNode']['fidelity'] == 'measured-real')
    ok, refusal = db.adjudicate(s, 'archipelago', 'dustin', '')
    check('admission WITHOUT a name refuses — admission IS naming',
          not ok and 'naming' in refusal['action'])
    check('mesh needs no name; anonymous deciders and unknown '
          'decisions refuse',
          db.adjudicate(s, 'mesh', 'dustin')[0]
          and not db.adjudicate(s, 'mesh', '')[0]
          and not db.adjudicate(s, 'lagoon', 'dustin')[0]
          and not db.adjudicate(dict(s, status='mesh'), 'mesh',
                                'dustin')[0])
    fresh = db.merge_heard(None, {'destHash': 'cd34',
                                  'identityHash': 'ef56',
                                  'interface': 'LoRa Serial',
                                  'lastHeardMs': 9, 'count': 3}, 9)
    check('first hearing creates an unadjudicated sighting with its '
          'evidence', fresh['status'] == 'unadjudicated'
          and fresh['announce_count'] == 3
          and fresh['heard_via'] == 'LoRa Serial')
    merged = db.merge_heard(fresh, {'interface': 'TCP Server',
                                    'lastHeardMs': 20, 'count': 2}, 20)
    check('re-hearing accumulates, and a NEW bearer for a known peer '
          'is recorded',
          merged['announce_count'] == 5
          and merged['last_heard_ms'] == 20
          and merged['heard_via'] == 'LoRa Serial,TCP Server'
          and merged['first_heard_ms'] == fresh['first_heard_ms'])

    # -- mesh simulation (ret-1e, §5p) ------------------------------------
    from reticulum import meshsim_basis as ms
    check('propagation modes are a fidelity ladder; elevation modes '
          'REFUSE with the terrain disclaimer (deliberately deferred)',
          ms.PROPAGATION_MODE_VALUES == ('flat-assumed', 'measured',
                                         'average-elevation',
                                         'ideal-elevation')
          and ms.mode_supported('flat-assumed')[0]
          and ms.mode_supported('measured')[0]
          and not ms.mode_supported('ideal-elevation')[0]
          and 'TERRAIN IS NOT ACCOUNTED FOR'
          in ms.mode_supported('ideal-elevation')[1]
          and not ms.mode_supported('lunar')[0])
    r, fid, _ = ms.flat_range_m({'declared_range_m': 1000.0,
                                 'tx_power_dbm_max': 22,
                                 'rx_sensitivity_dbm': -129,
                                 'freq_mhz_lo': 915})
    check('flat range PREFERS the vendor-declared figure',
          r == 1000.0 and fid == 'declared')
    r, fid, ev = ms.flat_range_m({'tx_power_dbm_max': 22,
                                  'rx_sensitivity_dbm': -129,
                                  'freq_mhz_lo': 915})
    check('no declared range -> link-budget derivation, labelled '
          'derived-flat with the arithmetic',
          fid == 'derived-flat' and r and r > 1000
          and 'link budget' in ev)
    check('missing radio facts -> no range, refused not guessed',
          ms.flat_range_m({})[0] is None
          and ms.flat_range_m({})[1] == 'unknown')
    plan = ms.spacing_plan(1000.0, 3_000_000)
    check('spacing = range x safety; hex cells; nodes >= 1; the '
          'disclaimer rides every plan',
          plan['spacingM'] == 700.0 and plan['nodesForArea'] >= 1
          and any('TERRAIN' in a for a in plan['assumptions']))
    relay = ms.relay_allowance(9, 200, 6568)
    check('relay allowance: 9 nodes @ 200 bps on the measured LoRa '
          'capacity FITS, with the burden arithmetic shown',
          relay['ok'] and relay['fits']
          and relay['relayAllowanceBpsPerNode'] > 0
          and relay['avgHops'] > 1)
    relay = ms.relay_allowance(100, 2000, 6568)
    check('an oversubscribed mesh is VERDICTED with the max '
          'achievable target named',
          relay['ok'] and not relay['fits']
          and 'oversubscribed' in relay['verdict']
          and relay['maxAchievablePerPeerBps'] > 0)
    check('a one-node mesh refuses (nothing to relay)',
          not ms.relay_allowance(1, 100, 1000)['ok'])
    square = {'type': 'Feature', 'geometry': {
        'type': 'Polygon', 'coordinates': [[
            [-1000, -500], [3000, -500], [3000, 500], [-1000, 500],
            [-1000, -500]]]}}
    east = ms.hops_toward(square, (0, 0), 90, 500)
    west = ms.hops_toward(square, (0, 0), 270, 500)
    north = ms.hops_toward(square, (0, 0), 0, 500)
    check('a boundary shape IS a directional hop budget: more hops '
          'toward the far edge than the near one',
          east is not None and east > west and north <= west
          and east >= 5 and north <= 1)
    check('spread limits: each form binds, the tightest wins, and NO '
          'limits refuses (unbounded cannot happen by accident)',
          not ms.spread_allows({'max_hops': 3}, 4, 0)[0]
          and not ms.spread_allows({'max_distance_m': 900}, 1,
                                   1000)[0]
          and not ms.spread_allows({'max_hops': 10,
                                    'max_distance_m': 900}, 2,
                                   1000)[0]
          and ms.spread_allows({'max_hops': 3,
                                'max_distance_m': 5000}, 2, 1000)[0]
          and not ms.spread_allows({}, 0, 0)[0])
    check('a shape policy without bearing/spacing refuses rather '
          'than guessing a direction',
          not ms.spread_allows({'boundary_geojson': square}, 1,
                               100)[0]
          and ms.spread_allows({'boundary_geojson': square}, 2, 100,
                               bearing_deg=90, origin_xy=(0, 0),
                               spacing_m=500)[0])
    samples = ([{'bearing_deg': b, 'distance_m': 900,
                 'success': True} for b in (10, 100, 190)]
               + [{'bearing_deg': 280, 'distance_m': 150,
                   'success': True}])
    sus = ms.interference_suspicions(samples, 1000)
    check('one starved sector among healthy ones IS a suspicion, '
          'with the irregularity as evidence',
          len(sus['suspicions']) == 1
          and 'IRREGULAR' in sus['suspicions'][0]['evidence']
          and sus['suspicions'][0]['fidelity'] == 'derived')
    all_short = [{'bearing_deg': b, 'distance_m': 200,
                  'success': True} for b in (10, 100, 190, 280)]
    sus = ms.interference_suspicions(all_short, 1000)
    check('ALL sectors short is NOT interference — named as a '
          'prediction (or terrain) problem instead',
          sus['suspicions'] == []
          and 'prediction problem' in sus['note'])
    check('MeshSimNode records elevation but v1 does not use it '
          '(the docstring says so)',
          'elevation_m' in inspect.signature(
              ms.MeshSimNode.__init__).parameters
          and 'UNUSED' in (ms.MeshSimNode.__doc__ or ''))


    # -- §5q: generic reference rows + kit profiles + counts-first --------
    from reticulum import meshsim_placement as mp
    check('device classes gained ham-transceiver + ham-receiver',
          'ham-transceiver' in dc.DEVICE_CLASS_VALUES
          and 'ham-receiver' in dc.DEVICE_CLASS_VALUES)
    generics = {m['name']: m for m in dc.SEED_DEVICE_MODELS
                if m['name'].startswith('generic-')}
    check('four generic REFERENCE rows exist with min<typ<max spans '
          'and sourced evidence',
          set(generics) == {'generic-lora', 'generic-ham-vhf-uhf',
                            'generic-wifi-24', 'generic-wifi-halow'}
          and all(m['declared_range_min_m'] < m['declared_range_m']
                  < m['declared_range_max_m']
                  for m in generics.values())
          and all('http' in json.dumps(m['evidence_json'])
                  for m in generics.values()))
    check('reference rows REFUSE to vouch (openness unstated) — and '
          'that being correct is the point',
          all(not dc.model_vouches(m)[0] for m in generics.values())
          and all('REFERENCE CLASS' in m['notes']
                  for m in generics.values()))
    check('unpriced reference rows refuse costing; the HaLow row '
          'carries its dated price',
          generics['generic-lora']['price_usd'] == 0.0
          and generics['generic-wifi-halow']['price_usd'] == 134.97)
    kits = {k['name']: json.loads(k['devices_json'])
            for k in mb.SEED_KIT_PROFILES}
    check("Dustin's three kit profiles seed verbatim (everyday / "
          'broadcaster / backbone)',
          kits['everyday-node'] == {'lora': 1, 'ham-rx': 1,
                                    'wifi-halow': 1}
          and kits['meshapp-broadcaster'] == {'ham-tx': 1,
                                              'wifi-halow': 3}
          and kits['bandwidth-backbone'] == {'wifi-halow': 4})
    cohorts = mp.population_cohorts_report(
        [{'profile': 'everyday-node', 'count': 12},
         {'profile': 'meshapp-broadcaster', 'count': 1},
         {'kit': {'wifi-halow': 4}, 'count': 3,
          'label': 'backbone'},
         {'profile': 'nope', 'count': 5}],
        profiles=kits)
    check('counts-first: counts are the truth, pct is DERIVED '
          'analytics, unknown profiles refuse by name',
          cohorts['countsFirst'] and cohorts['populationN'] == 16
          and cohorts['builds']['everyday-node']['count'] == 12
          and cohorts['builds']['everyday-node']['pctOfPopulation']
          == 75.0
          and 'unknown kit profile'
          in cohorts['builds']['nope']['error'])
    check('the broadcaster kit PEERS on halow with everyday+backbone '
          'cohorts, and everyday hears its ham-tx one-way',
          'wifi-halow'
          in cohorts['builds']['meshapp-broadcaster']['peersWith']
          and cohorts['builds']['everyday-node']['oneWayListensTo']
          == ['ham-tx']
          and 'capacityNote'
          in cohorts['builds']['meshapp-broadcaster'])
    legacy = mp.population_mix_report({'lora': 60, 'wifi': 40}, 10)
    check('the legacy pct form still works and is FLAGGED as legacy',
          legacy.get('legacyPctForm') is True
          and legacy['builds']['lora']['count'] == 6)

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

    # -- ret-1f (§5q): placement, population, pricing ---------------------
    from reticulum import meshsim_placement as mp
    square_m = {'type': 'Polygon', 'coordinates': [[
        [0, 0], [2000, 0], [2000, 2000], [0, 2000], [0, 0]]]}
    ring_m, area, notes = mp.to_local_meters(square_m)
    check('meter rings pass through with the note; area is right',
          ring_m is not None and area == 4_000_000.0
          and any('LOCAL METERS' in n for n in notes)
          and any('TERRAIN' in n for n in notes))
    lonlat = {'type': 'Polygon', 'coordinates': [[
        [-77.0, 39.0], [-76.99, 39.0], [-76.99, 39.01],
        [-77.0, 39.01], [-77.0, 39.0]]]}
    ring2, area2, notes2 = mp.to_local_meters(lonlat)
    check('lon/lat rings project equirectangularly, assumption '
          'STATED, ~1km cell area sane',
          ring2 is not None
          and any('equirectangular' in n for n in notes2)
          and 800_000 < area2 < 1_100_000)
    priced = {'name': 'sh', 'declared_range_m': 1000.0,
              'price_usd': 27.99, 'capacityBps': 6568}
    unpriced = {'name': 'mystery', 'declared_range_m': 1000.0,
                'capacityBps': 6568}
    plan = mp.plan_cheapest_coverage(ring_m, [priced, unpriced], 200)
    check('unpriced models are REFUSED costing by name; the priced '
          'one wins with positions and a real total',
          any(r['model'] == 'mystery' and 'unstated'
              in r['reason'] for r in plan['refused'])
          and plan['winner'] is not None
          and plan['winner']['model'] == 'sh'
          and plan['winner']['totalCostUsd'] > 0
          and len(plan['winner']['positions'])
          == plan['winner']['nodeCount'])
    cheap_weak = {'name': 'weak', 'declared_range_m': 1000.0,
                  'price_usd': 5.0, 'capacityBps': 40}
    plan2 = mp.plan_cheapest_coverage(ring_m, [cheap_weak, priced],
                                      200)
    check('cheapest FEASIBLE wins over cheaper-infeasible (the weak '
          'option cannot carry the target)',
          plan2['winner']['model'] == 'sh'
          and any(e['model'] == 'weak' for e in plan2['infeasible']))
    # -- the 8-nodes-for-2km lesson (Dustin 2026-08-13) -------------------
    check('multi-node plans NAME the binding constraint (backbone vs '
          'coverage — the constraint-stacking bug made visible)',
          'backbone-connectivity' in plan['winner']['bindingConstraint']
          and 'coverage alone' in plan['winner']['bindingConstraint'])
    spanned = {'name': 'sh-span', 'declared_range_m': 1000.0,
               'declared_range_min_m': 500.0,
               'declared_range_max_m': 1500.0,
               'price_usd': 27.99, 'capacityBps': 6568}
    plan_o = mp.plan_cheapest_coverage(ring_m, [spanned], 200,
                                       range_scenario='optimistic')
    check('OPTIMISTIC range on the 2 km square = ONE node (corners '
          'at 1414 m < 1500 m) — the single-node case the old solver '
          'never tested',
          plan_o['winner']['nodeCount'] == 1
          and len(plan_o['winner']['positions']) == 1
          and plan_o['winner']['bindingConstraint']
          .startswith('coverage')
          and plan_o['winner']['rangeFidelity'].endswith('-max'))
    plan_p = mp.plan_cheapest_coverage(ring_m, [spanned], 200,
                                       range_scenario='pessimistic')
    check('PESSIMISTIC reads the vendor minimum and costs more nodes '
          'than typical',
          plan_p['winner']['rangeM'] == 500.0
          and plan_p['winner']['nodeCount']
          > plan['winner']['nodeCount'])
    plan_ov = mp.plan_cheapest_coverage(ring_m, [priced], 200,
                                        range_override_m=2500)
    check('an operator range override wins and is LABELLED as the '
          'assertion it is',
          plan_ov['winner']['nodeCount'] == 1
          and plan_ov['winner']['rangeFidelity'] == 'operator-override'
          and 'operator-asserted'
          in plan_ov['winner']['rangeEvidence'])
    check('pessimistic without a declared span falls back 0.6x, '
          'stated in the scenario field',
          mp.plan_cheapest_coverage(
              ring_m, [priced], 200,
              range_scenario='pessimistic')['winner']['rangeM']
          == 600.0)

    hexn = len(mp.hex_positions_in_polygon(ring_m, 700))
    linn = len(mp.linear_positions(ring_m, 700))
    check('linear vs max-spread differ on the square (a chain is a '
          'row, a spread is a lattice), and the chain relay math is '
          'the stress case',
          hexn > linn and linn >= 2
          and 'n/3' in json.dumps(mp.plan_cheapest_coverage(
              ring_m, [priced], 200,
              reach_mode='linear')['assumptions']))
    short = {'name': 'short', 'declared_range_m': 600.0,
             'price_usd': 12.0, 'capacityBps': 6568}
    nodes_ok = [{'name': 'a', 'x_m': 500.0, 'y_m': 1000.0},
                {'name': 'b', 'x_m': 1000.0, 'y_m': 1000.0},
                {'name': 'c', 'x_m': 1500.0, 'y_m': 1000.0}]
    fixed = mp.assess_fixed_locations(ring_m, nodes_ok, [short], 200)
    check('fixed-locations: connected chain, BFS hops source stated, '
          'per-node types + total cost',
          fixed['ok'] and fixed['connected']
          and fixed['relay']['avgHopsSource'].startswith('BFS')
          and fixed['totalCostUsd'] == round(3 * 12.0, 2))
    check('coverage gaps are NAMED with centroids when the shape is '
          'not covered (600 m radios cannot fill a 2 km square from '
          'the center row)',
          not fixed['fullyCovered']
          and fixed['uncoveredGaps']
          and 'centroidXM' in fixed['uncoveredGaps'][0])
    nodes_far = nodes_ok + [{'name': 'lonely', 'x_m': 1900.0,
                             'y_m': 100.0}]
    fixed2 = mp.assess_fixed_locations(ring_m, nodes_far, [short],
                                       200)
    check('a disconnected node is NAMED (greedy v1 stated in '
          'assumptions)',
          'lonely' in fixed2['isolatedNodes']
          and any('greedy v1' in a for a in fixed2['assumptions']))
    res = mp.failure_resilience(ring_m, nodes_ok, [short])
    check('resilience: the MIDDLE of a 3-node chain is an '
          'articulation finding with what it takes down',
          any(f['node'] == 'b' and f['partitionsNodes']
              for f in res['articulationFindings']))
    pop = mp.population_mix_report(
        {'lora': 40, 'ham-rx': 30, 'ham-tx': 5, 'lorawan': 25}, 200)
    check('population: lorawan is isolated WITH the gateway reason '
          '(row 9), ham-rx listens one-way when ham-tx exists',
          pop['builds']['lorawan']['isolated']
          and 'gateway' in pop['builds']['lorawan']['why']
          and pop['builds']['ham-rx']['oneWayListensTo'] == ['ham-tx']
          and not pop['builds']['ham-rx']['isolated'])
    pop2 = mp.population_mix_report({'ham-rx': 100}, 50)
    check('ham-rx WITHOUT ham-tx is isolated with the §5g '
          'nobody-is-broadcasting reason',
          pop2['builds']['ham-rx']['isolated']
          and 'licensed' in pop2['builds']['ham-rx']['why'])
    # -- §5q addendum: node LOADOUTS (units + kits) -----------------------
    bandwidth_poor = {'name': 'thin', 'declared_range_m': 1000.0,
                      'price_usd': 10.0, 'capacityBps': 600,
                      'unitsMax': 4}
    plan_u = mp.plan_cheapest_coverage(ring_m, [bandwidth_poor], 200)
    check('units rescue a bandwidth-infeasible option: 2 units '
          'double capacity, the winner says so, cost scales',
          plan_u['winner'] is not None
          and plan_u['winner']['unitsPerNode'] == 2
          and plan_u['winner']['totalCostUsd'] == round(
              plan_u['winner']['nodeCount'] * 10.0 * 2, 2)
          and any('DISTINCT channels' in a
                  for a in plan_u['assumptions']))
    plan_u1 = mp.plan_cheapest_coverage(
        ring_m, [dict(bandwidth_poor, unitsMax=1)], 200)
    check('the units cap is respected (unitsMax=1 stays infeasible) '
          'and units NEVER extend range (same node count, same '
          'range, only feasibility moved)',
          plan_u1['winner'] is None
          and any(e['model'] == 'thin' and e['unitsPerNode'] == 1
                  for e in plan_u1['infeasible'])
          and plan_u1['infeasible'][0]['nodeCount']
          == plan_u['winner']['nodeCount']
          and plan_u1['infeasible'][0]['rangeM']
          == plan_u['winner']['rangeM'])
    narrow = dict(bandwidth_poor, name='narrowband',
                  freq_mhz_lo=915.0, freq_mhz_hi=915.4)
    plan_ch = mp.plan_cheapest_coverage(ring_m, [narrow], 200)
    check('the channel count CEILINGS units (one usable channel = '
          'one unit, whatever unitsMax hopes)',
          plan_ch['winner'] is None
          and plan_ch['infeasible'][0]['unitsCap'] == 1)
    multi = {'name': 'multi', 'declared_range_m': 1000.0,
             'price_usd': 10.0, 'capacityBps': 250, 'unitsMax': 4}
    single = {'name': 'single', 'declared_range_m': 1000.0,
              'price_usd': 25.0, 'capacityBps': 1200}
    plan_rank = mp.plan_cheapest_coverage(ring_m, [multi, single],
                                          200)
    check('TOTAL cost ranks: a pricier single-unit device beats the '
          'cheap one that needs three of itself',
          plan_rank['winner']['model'] == 'single'
          and any(e['model'] == 'multi' and e['unitsPerNode'] == 3
                  for e in plan_rank['rankedFeasible']))
    thin_fixed = {'name': 'thin', 'declared_range_m': 600.0,
                  'price_usd': 10.0, 'capacityBps': 200,
                  'unitsMax': 4}
    fixed_u = mp.assess_fixed_locations(ring_m, nodes_ok,
                                        [thin_fixed], 200)
    check('fixed-locations: a BANDWIDTH failure adds UNITS at the '
          'bottleneck (relay now fits, cost reflects it)',
          fixed_u['relay'] is not None and fixed_u['relay']['fits']
          and any(p['units'] > 1 for p in fixed_u['perNode'])
          and fixed_u['totalCostUsd'] == round(
              sum(p['units'] * 10.0 for p in fixed_u['perNode']), 2)
          and any('units never extend range' in a
                  for a in fixed_u['assumptions']))
    long_opt = {'name': 'long', 'declared_range_m': 1500.0,
                'price_usd': 40.0, 'capacityBps': 6568}
    fixed_t = mp.assess_fixed_locations(
        ring_m, nodes_far, [dict(short, unitsMax=4), long_opt], 200)
    lonely_row = next(p for p in fixed_t['perNode']
                      if p['name'] == 'lonely')
    check('a RANGE failure moves TYPE, not units (the far node was '
          'upgraded and keeps 1 unit — units cannot buy distance)',
          lonely_row['type'] == 'long' and lonely_row['units'] == 1)
    mixk = mp.population_mix_report(
        {'lora': 30, 'wifi': 30,
         'farm-kit': {'kit': {'lora': 1, 'wifi': 1}, 'pct': 40}}, 10)
    check('a KIT is the union of its parts: lora+wifi kit peers with '
          'both pure builds, devices echoed',
          mixk['builds']['farm-kit']['peersWith'] == ['lora', 'wifi']
          and mixk['builds']['farm-kit']['devices']
          == {'lora': 1, 'wifi': 1}
          and mixk['builds']['lora']['peersWith'] == ['lora'])
    mixh = mp.population_mix_report(
        {'ham-tx': 10, 'lora': 20,
         'scout': {'kit': {'lora': 2, 'ham-rx': 1}, 'pct': 50}}, 10)
    check('a kit with ham-rx LISTENS one-way and never becomes TX; '
          'multi-unit parts state the distinct-channels capacity '
          'note',
          mixh['builds']['scout']['oneWayListensTo'] == ['ham-tx']
          and 'ham-tx' not in mixh['builds']['scout']['peersWith']
          and 'lora' in mixh['builds']['scout']['peersWith']
          and '2x lora' in mixh['builds']['scout']['capacityNote']
          and 'DISTINCT channels'
          in mixh['builds']['scout']['capacityNote'])

    check('placement + population results all carry the disclaimer',
          all('TERRAIN' in json.dumps(x)
              for x in (plan, fixed, res, pop)))
    check('the SH-L1A seed row is PRICED with dated evidence',
          dc.SEED_DEVICE_MODELS[0]['price_usd'] == 27.99
          and any('price' in e['fact'] and '2026-08-13'
                  in json.dumps(e) for e in json.loads(
                      dc.SEED_DEVICE_MODELS[0]['evidence_json'])))
    node_conv, refusals = mp.nodes_to_local(
        [{'name': 'geo', 'lon': -76.995, 'lat': 39.005},
         {'name': 'bad'}], lonlat)
    check('lon/lat nodes project into the polygon frame; a node with '
          'neither form is refused by name',
          len(node_conv) == 1 and abs(node_conv[0]['x_m']) < 1000
          and refusals and 'bad' in refusals[0])

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

    # -- antennas (§5q addendum; drone bridges SHELVED 2026-08-13 — ------
    # -- Dustin: legal complications; revival = drone_basis.py from ------
    # -- git history at 7201c0a) -----------------------------------------
    omni = {'name': 'omni', 'declared_range_m': 1000.0,
            'price_usd': 20.0, 'capacityBps': 6568,
            'antenna': 'high-gain-omni'}
    yagi = dict(omni, name='yagi', antenna='directional')
    plan_a = mp.plan_cheapest_coverage(ring_m, [omni], 200)
    check('antenna factor extends range, is labelled in evidence, '
          'and 1.8x turns the 2 km square into a single-node job',
          plan_a['winner']['rangeM'] == 1800.0
          and 'antenna factor' in plan_a['winner']['rangeEvidence']
          and plan_a['winner']['antenna'] == 'high-gain-omni'
          and plan_a['winner']['nodeCount'] == 1)
    plan_d = mp.plan_cheapest_coverage(ring_m, [yagi], 200)
    check('directional x max-spread is REFUSED by name (point-to-'
          'point cannot serve a lattice)',
          plan_d['winner'] is None
          and any('point-to-point' in r['reason']
                  for r in plan_d['refused']))
    plan_l = mp.plan_cheapest_coverage(ring_m, [yagi], 200,
                                       reach_mode='linear')
    check('directional is allowed in linear chains at x3 range',
          plan_l['winner'] is not None
          and plan_l['winner']['rangeM'] == 3000.0)
    check('an unknown antenna refuses — factors are not guessed',
          any('unknown antenna' in r['reason']
              for r in mp.plan_cheapest_coverage(
                  ring_m, [dict(omni, antenna='mystical')],
                  200)['refused']))
    check('no drone machinery remains (shelved 2026-08-13 — revival '
          'is a git restore from 7201c0a, not a rebuild)',
          not os.path.exists(os.path.join(
              os.path.dirname(__file__), 'drone_basis.py')))
    fx2 = mp.assess_fixed_locations(
        ring_m, [{'name': n, 'x_m': x, 'y_m': y}
                 for n, x, y in (('a', 100, 100), ('b', 300, 100),
                                 ('c', 100, 300), ('d', 300, 300))],
        [yagi], 100)
    check('directional nodes holding >2 graph neighbours are '
          'FLAGGED (a chain, not a lattice) and the rule is in the '
          'assumptions',
          len(fx2['directionalViolations']) == 4
          and any('point-to-point' in a for a in fx2['assumptions']))

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

    # ---- ret-7 backend half: LXMF over the sidecar ---------------
    import io as _io
    import os as _os
    import urllib.request as _url
    from reticulum import rns_remote as _rr

    _os.environ.pop('RETICULUM_URL', None)
    report = _rr.lxmf_overview()
    check('lxmf: no sidecar configured -> honest refusal with the '
          'knob + action named',
          not report.get('ok') and 'suggestion' in report)

    _os.environ['RETICULUM_URL'] = 'http://sidecar.test:4285'
    _canned = {}

    def _fake_urlopen(req, timeout=0):
        import json as _json
        target = req if isinstance(req, str) else req.full_url
        target = target.split('4285', 1)[1]
        body = _canned.get(target, {'ok': False, 'error': 'no can'})
        return _io.BytesIO(_json.dumps(body).encode())

    _real = _url.urlopen
    _url.urlopen = _fake_urlopen
    try:
        _canned['/lxmf'] = {'ok': True, 'storedMessages': 2,
                            'destinationHash': 'aa'}
        _canned['/lxmf/messages'] = {'ok': True, 'messages': [
            {'source': '01', 'content': 'hi'}]}
        overview = _rr.lxmf_overview()
        check('lxmf: overview proxies the sidecar facts AND '
              'carries the pin-isolation note (the normal-'
              'reticulum-peers truth rides every surface)',
              overview['ok'] and overview['storedMessages'] == 2
              and 'rns 0.9.x' in overview['pinIsolationNote'])
        msgs = _rr.lxmf_messages()
        check('lxmf: stored messages list through the proxy',
              msgs['ok'] and msgs['messages'][0]['content'] == 'hi')
        _canned['/lxmf/send'] = {'ok': False,
                                 'refusal': 'destination identity '
                                            'unknown ... announce'}
        report = _rr.lxmf_send('99' * 16, 'x')
        check('lxmf: sidecar refusals pass through INTACT '
              '(announce-first recovery reaches the caller)',
              not report['ok'] and 'announce' in report['refusal'])
        _canned['/lxmf/policy'] = {'ok': True,
                                   'policy': {'mode': 'whitelist'}}
        report = _rr.lxmf_policy(whitelist=['02' * 16])
        check('lxmf: policy updates proxy through',
              report['ok'] and report['policy']['mode']
              == 'whitelist')
    finally:
        _url.urlopen = _real
        _os.environ.pop('RETICULUM_URL', None)

    failed = sum(1 for r in _results if not r)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed')
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    run()
