"""Selftest for scoring.group_authority_basis — authority grants,
group↔instance bindings, the three-check admission verdict, and
term-availability signals.

Run: python3 -m scoring.group_authority_selftest
"""

import json
import os
import sys
import types

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

PASS = '\033[92m[PASS]\033[0m'
FAIL = '\033[91m[FAIL]\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL} {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    m = types.SimpleNamespace(objectTables={}, idList=[], db=None)
    m.objectTables['ScoreGroup'] = {
        'housing-justice-coalition': types.SimpleNamespace(
            name='housing-justice-coalition', group_type='civic'),
        'renters-union': types.SimpleNamespace(
            name='renters-union', group_type='political'),
    }
    m.objectTables['PeerNode'] = {
        'polari-peer-b': types.SimpleNamespace(
            name='polari-peer-b',
            base_url='http://prf-b-backend:3000', status='alive'),
    }
    return m


ALICE = 'sub-alice'
BOB = 'sub-bob'
EVE = 'sub-eve'
GROUP = 'housing-justice-coalition'
INSTANCE = 'polari-test-a'


def phase_group_grants(m):
    from scoring.group_authority_basis import (grant_group_authority,
                                         revoke_group_authority)
    r = grant_group_authority(m, 'no-such-group', ALICE,
                              granter_subject=ALICE, role='primary')
    check('grant on unknown group refused with suggestion',
          not r['ok'] and 'knownGroups' in r
          and r['suggestion']['knob'] == 'ScoreGroup')
    r = grant_group_authority(m, GROUP, ALICE, username='alice',
                              granter_subject=BOB, role='shared')
    check('bootstrap shared grant refused (primary self-claim '
          'first)', not r['ok'] and 'first grant' in r['error'])
    r = grant_group_authority(m, GROUP, ALICE, username='alice',
                              granter_subject=ALICE, role='primary',
                              identity_source='keycloak-verified')
    check('bootstrap primary self-claim admitted',
          r['ok'] and r['bootstrap']
          and r['grant']['role'] == 'primary', json.dumps(r))
    r = grant_group_authority(m, GROUP, BOB, username='bob',
                              granter_subject=EVE, role='shared')
    check('non-primary granter refused',
          not r['ok'] and 'activePrimary' in r)
    r = grant_group_authority(m, GROUP, BOB, username='bob',
                              granter_subject=ALICE, role='shared')
    check('primary grants shared authority', r['ok'])
    r = grant_group_authority(m, GROUP, EVE, granter_subject=BOB,
                              role='shared')
    check('shared holder cannot grant (not primary)', not r['ok'])
    r = grant_group_authority(m, GROUP, BOB, granter_subject=ALICE,
                              role='shared')
    check('duplicate active grant refused with knob suggestion',
          not r['ok'] and r['suggestion']['knob'].startswith('ga--'))
    r = grant_group_authority(m, GROUP, EVE, granter_subject=ALICE,
                              role='primary')
    check('second primary refused (transfer = revoke first)',
          not r['ok'] and 'at most one' in r['error'])
    r = revoke_group_authority(m, GROUP, BOB, revoker_subject=BOB)
    check('non-primary revoker refused', not r['ok'])
    r = revoke_group_authority(m, GROUP, BOB, revoker_subject=ALICE)
    check('primary revokes shared grant',
          r['ok'] and r['grant']['status'] == 'revoked')
    r = grant_group_authority(m, GROUP, BOB, username='bob',
                              granter_subject=ALICE, role='shared')
    check('re-grant after revoke admitted (new active row state)',
          r['ok'])


def phase_instance_grants(m):
    from scoring.group_authority_basis import grant_instance_authority
    r = grant_instance_authority(m, 'unknown-instance', ALICE,
                                 granter_subject=ALICE,
                                 role='primary')
    check('grant on unknown instance refused with known list',
          not r['ok'] and INSTANCE in r['knownInstances']
          and 'polari-peer-b' in r['knownInstances'])
    r = grant_instance_authority(m, '', ALICE, username='alice',
                                 granter_subject=ALICE,
                                 role='primary')
    check('instance defaults to self identity + bootstrap primary',
          r['ok'] and r['bootstrap'])
    r = grant_instance_authority(m, 'polari-peer-b', BOB,
                                 granter_subject=BOB,
                                 role='primary')
    check('peer instance claimable (PeerNode counts as known)',
          r['ok'])


def phase_bindings(m):
    from scoring.group_authority_basis import (confirm_binding_remote,
                                         propose_binding,
                                         revoke_binding)
    r = propose_binding(m, GROUP, INSTANCE,
                        proposed_by_subject=BOB)
    check('proposal by group-only authority refused, names the '
          'missing side',
          not r['ok'] and r['missingAuthority']
          == [f"instance '{INSTANCE}'"])
    r = propose_binding(m, GROUP, INSTANCE,
                        proposed_by_subject=ALICE,
                        proposed_by_username='alice')
    check('proposal with both authorities → confirmed-local',
          r['ok'] and r['binding']['status'] == 'confirmed-local'
          and r['evidence']['groupAuthority']
          and r['evidence']['instanceAuthority'], json.dumps(r))
    binding_name = r['binding']['name']
    r = propose_binding(m, GROUP, INSTANCE,
                        proposed_by_subject=ALICE)
    check('duplicate proposal refused', not r['ok'])
    r = confirm_binding_remote(m, 'binding--nope--nope')
    check('confirm-remote on unknown binding refused', not r['ok'])
    r = confirm_binding_remote(m, binding_name,
                               confirmed_by='psc-backend')
    check('confirm-remote flips binding active',
          r['ok'] and r['binding']['status'] == 'active'
          and r['binding']['confirmedRemoteBy'] == 'psc-backend')
    r = confirm_binding_remote(m, binding_name)
    check('re-confirm is idempotent (alreadyActive)',
          r['ok'] and r.get('alreadyActive'))
    r = revoke_binding(m, binding_name, EVE)
    check('binding revoke by non-primary refused', not r['ok'])
    r = revoke_binding(m, binding_name, ALICE)
    check('binding revoke by a primary works',
          r['ok'] and r['binding']['status'] == 'revoked')
    r = propose_binding(m, GROUP, INSTANCE,
                        proposed_by_subject=ALICE)
    check('re-propose after revoke reuses the row → '
          'confirmed-local',
          r['ok'] and r['binding']['status'] == 'confirmed-local')
    r = confirm_binding_remote(m, binding_name)
    check('re-activated for the check/signal phases', r['ok'])


def phase_authority_check(m):
    from scoring.group_authority_basis import authority_check
    r = authority_check(m, ALICE, GROUP, INSTANCE)
    check('full check authorizes with 3/3 named checks',
          r['authorized'] and len(r['checks']) == 3
          and not r['failedChecks'], json.dumps(r))
    check('checks carry grant evidence rows',
          isinstance(r['checks'][0]['evidence'], list)
          and r['checks'][0]['evidence'][0]['subject'] == ALICE)
    r = authority_check(m, EVE, GROUP, INSTANCE)
    check('unauthorized subject fails, failing checks named',
          not r['authorized']
          and 'group-authority' in r['failedChecks']
          and 'instance-authority' in r['failedChecks'])
    r = authority_check(m, BOB, GROUP, INSTANCE)
    check('group-only authority fails ONLY instance check',
          not r['authorized']
          and r['failedChecks'] == ['instance-authority'])
    r = authority_check(m, ALICE, GROUP, 'polari-peer-b')
    check('unbound pair fails binding-active with evidence string',
          not r['authorized']
          and r['failedChecks'] == ['instance-authority',
                                    'binding-active'])


def phase_signals(m):
    from scoring.group_authority_basis import (
        list_signals, signal_report,
        submit_term_availability_signal,
    )
    r = submit_term_availability_signal(m, '', 'ctx', GROUP,
                                        requested_by_subject=ALICE)
    check('signal missing term refused',
          not r['ok'] and 'term_name' in r['error'])
    r = submit_term_availability_signal(
        m, 'median-rent-burden', 'dmv-region', GROUP,
        instance_name=INSTANCE, concept_name='housing-price-tenants',
        requested_by_subject=ALICE, requested_by_username='alice',
        identity_source='keycloak-verified')
    check('authorized signal admitted with provenance',
          r['ok'] and r['admitted']
          and r['provenance']['assertedByGroup'] == GROUP
          and r['provenance']['viaInstance'] == INSTANCE,
          json.dumps(r))
    check('admitted signal persisted with full verdict',
          r['signal']['status'] == 'admitted'
          and len(r['signal']['verdict']['checks']) == 3)
    r = submit_term_availability_signal(
        m, 'median-rent-burden', 'dmv-region', GROUP,
        requested_by_subject=ALICE)
    check('duplicate signal refused, points at existing row',
          not r['ok'] and r['suggestion']['knob'].startswith('tas--'))
    r = submit_term_availability_signal(
        m, 'sketchy-metric', 'dmv-region', GROUP,
        instance_name=INSTANCE, requested_by_subject=EVE,
        requested_by_username='eve')
    check('unauthorized signal REFUSED but persisted with verdict',
          r['ok'] and not r['admitted']
          and r['signal']['status'] == 'refused'
          and r['signal']['verdict']['failedChecks'])
    check('refusal carries no provenance', r['provenance'] is None)
    r = signal_report(m, 'tas--sketchy-metric--dmv-region--'
                         + GROUP)
    check('signal report reads back the refusal trail',
          r['ok'] and r['signal']['status'] == 'refused')
    r = list_signals(m, group_name=GROUP, status='admitted')
    check('signal list filters by group + status',
          len(r['signals']) == 1
          and r['signals'][0]['termName'] == 'median-rent-burden')
    r = list_signals(m)
    check('unfiltered list returns both signals',
          len(r['signals']) == 2)


def main():
    os.environ['POLARI_INSTANCE_NAME'] = INSTANCE
    m = _mgr()
    phase_group_grants(m)
    phase_instance_grants(m)
    phase_bindings(m)
    phase_authority_check(m)
    phase_signals(m)
    passed, total = sum(_results), len(_results)
    print(f'{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
