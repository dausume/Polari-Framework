"""
@cross-cutting
@module scoring.group_authority_basis
@tags @xc:bindings @xc:accessControl

Group / Instance authority — how groups assert to the scorecard
(Dustin 2026-07-16):

  GroupAuthorityGrant    — a user (Keycloak subject) holds PRIMARY or
                           SHARED authority for a ScoreGroup (a group
                           of any kind). A group with zero active
                           grants is claimed first-come as PRIMARY
                           (self-claim only); afterward only the
                           active primary grants/revokes.
  InstanceAuthorityGrant — the same authority shape over a Polari
                           instance (this instance by env identity,
                           or a known PeerNode).
  GroupInstanceBinding   — designates a Polari instance as THE
                           authoritative source for a group. Proposing
                           requires authority on BOTH sides of the
                           binding; the row is then 'confirmed-local'
                           and only the counterparty (the PSC) flips
                           it 'active' via confirm-remote. This is the
                           Polari half of "defined on both sides".
  authority_check        — the admission verdict: three named checks
                           (group-authority, instance-authority,
                           binding-active), each carrying its evidence
                           rows. Never a bare boolean.
  TermAvailabilitySignal — "we want to make this term available for
                           this context on the PSC", adjudicated
                           through authority_check and persisted with
                           the full verdict either way (refusals are
                           part of the accountability trail).

Identity is evidence too: callers verified by the Keycloak middleware
are stamped identity_source='keycloak-verified'; payload-supplied
subjects are accepted but stamped 'payload-unverified' so downstream
readers can weigh the claim honestly.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.authority_api (HTTP surface)
  - PSC backend PolariAuthorityService (server-to-server, forwarded
    bearer tokens)
@see /GROUP_AUTHORITY_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/group_authority/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import os
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.worldview_elections_basis import _by_name, _rows

from scoring.objects.group_authority._shared import AUTHORITY_CHECKS, AUTHORITY_ROLES, BINDING_STATUSES, GRANT_STATUSES, SIGNAL_STATUSES, _active_grants, _grant_summary, _insert, _known_instances, _now, _persist, _revoke_authority, _self_instance_name, authority_check, authority_report, binding_summary, confirm_binding_remote, list_signals, revoke_binding, revoke_group_authority, revoke_instance_authority, signal_report, signal_summary  # noqa: F401
from scoring.objects.group_authority.GroupAuthorityGrant import GroupAuthorityGrant  # noqa: F401
from scoring.objects.group_authority.InstanceAuthorityGrant import InstanceAuthorityGrant  # noqa: F401
from scoring.objects.group_authority.GroupInstanceBinding import GroupInstanceBinding  # noqa: F401
from scoring.objects.group_authority.TermAvailabilitySignal import TermAvailabilitySignal  # noqa: F401

from scoring.worldview_elections_basis import _by_name, _rows
import json

def _grant_authority(manager, class_name, key_field, key_value,
                     subject, username, role, granter_subject,
                     granter_username, identity_source, prefix,
                     notes=''):
    """Shared grant logic. Bootstrap: zero active grants → the FIRST
    claim must be a PRIMARY self-claim. Afterward only the active
    primary grants; a second active primary is refused (transfer =
    revoke first, an explicit act)."""
    if role not in AUTHORITY_ROLES:
        return {'ok': False,
                'error': f"role must be one of {AUTHORITY_ROLES}, "
                         f"got '{role}'"}
    if not subject:
        return {'ok': False, 'error': 'subject is required (the '
                'Keycloak sub of the authority holder)'}
    active = _active_grants(manager, class_name, key_field, key_value)
    already = [g for g in active if g.subject == subject]
    if already:
        return {'ok': False,
                'error': f"subject '{subject}' already holds an "
                         f"active '{already[0].role}' grant on "
                         f"'{key_value}'",
                'suggestion': {
                    'knob': already[0].name,
                    'action': 'revoke the existing grant first — '
                              'role changes are explicit acts'}}
    primaries = [g for g in active if g.role == 'primary']
    if not active:
        if role != 'primary' or granter_subject != subject:
            return {'ok': False,
                    'error': f"'{key_value}' has no authority yet — "
                             'the first grant must be a PRIMARY '
                             'self-claim (first-claim-wins, like '
                             'mesh naming)',
                    'suggestion': {
                        'knob': 'role',
                        'action': 'claim primary authority for '
                                  'yourself, then grant shared '
                                  'authority to others'}}
    else:
        granter = [g for g in primaries
                   if g.subject == granter_subject]
        if not granter:
            return {'ok': False,
                    'error': f"granter '{granter_subject}' does not "
                             f"hold the active primary grant on "
                             f"'{key_value}'",
                    'activePrimary': [_grant_summary(g)
                                      for g in primaries]}
        if role == 'primary':
            return {'ok': False,
                    'error': f"'{key_value}' already has an active "
                             'primary authority — at most one',
                    'activePrimary': [_grant_summary(g)
                                      for g in primaries],
                    'suggestion': {
                        'knob': primaries[0].name,
                        'action': 'revoke the current primary first '
                                  'to transfer it'}}
    cls = (GroupAuthorityGrant if class_name == 'GroupAuthorityGrant'
           else InstanceAuthorityGrant)
    row = cls(
        name=f'{prefix}--{key_value}--{subject}',
        subject=subject, username=username, role=role,
        status='active', granted_by_subject=granter_subject,
        granted_by_username=granter_username,
        identity_source=identity_source, granted_at=_now(),
        notes=notes, manager=manager,
        **{key_field: key_value})
    _insert(manager, class_name, row)
    return {'ok': True, 'grant': _grant_summary(row),
            'bootstrap': not active}
def grant_group_authority(manager, group_name, subject, username='',
                          role='shared', granter_subject='',
                          granter_username='',
                          identity_source='payload-unverified',
                          notes=''):
    """A user becomes primary/shared authority for a group of any
    kind (any ScoreGroup group_type)."""
    if _by_name(manager, 'ScoreGroup').get(group_name) is None:
        return {'ok': False,
                'error': f"no ScoreGroup named '{group_name}'",
                'knownGroups': sorted(_by_name(manager,
                                               'ScoreGroup')),
                'suggestion': {
                    'knob': 'ScoreGroup',
                    'action': 'create the ScoreGroup row first — '
                              'authority attaches to a real group '
                              'object'}}
    return _grant_authority(
        manager, 'GroupAuthorityGrant', 'group_name', group_name,
        subject, username, role, granter_subject, granter_username,
        identity_source, 'ga', notes)
def grant_instance_authority(manager, instance_name='', subject='',
                             username='', role='shared',
                             granter_subject='', granter_username='',
                             identity_source='payload-unverified',
                             notes=''):
    """A user becomes primary/shared authority for a Polari instance
    (this one by default, or a known peer)."""
    instance_name = instance_name or _self_instance_name()
    known = _known_instances(manager)
    if instance_name not in known:
        return {'ok': False,
                'error': f"'{instance_name}' is not this instance "
                         'or a known PeerNode',
                'knownInstances': sorted(known)}
    return _grant_authority(
        manager, 'InstanceAuthorityGrant', 'instance_name',
        instance_name, subject, username, role, granter_subject,
        granter_username, identity_source, 'ia', notes)
def propose_binding(manager, group_name, instance_name='',
                    proposed_by_subject='', proposed_by_username='',
                    identity_source='payload-unverified',
                    counterparty='psc', notes=''):
    """Designate an instance as a group's authoritative source. The
    proposer must hold authority (primary or shared) on BOTH the
    group and the instance; an authorized proposal IS the local
    definition ('confirmed-local'), and only the counterparty's
    confirm-remote makes it 'active'."""
    instance_name = instance_name or _self_instance_name()
    name = f'binding--{group_name}--{instance_name}'
    existing = _by_name(manager, 'GroupInstanceBinding').get(name)
    if existing is not None and existing.status != 'revoked':
        return {'ok': False,
                'error': f"binding '{name}' already exists "
                         f"(status '{existing.status}')"}
    group_grants = [g for g in _active_grants(
        manager, 'GroupAuthorityGrant', 'group_name', group_name)
        if g.subject == proposed_by_subject]
    instance_grants = [g for g in _active_grants(
        manager, 'InstanceAuthorityGrant', 'instance_name',
        instance_name) if g.subject == proposed_by_subject]
    if not group_grants or not instance_grants:
        missing = []
        if not group_grants:
            missing.append(f"group '{group_name}'")
        if not instance_grants:
            missing.append(f"instance '{instance_name}'")
        return {'ok': False,
                'error': f"proposer '{proposed_by_subject}' holds no "
                         f"active authority on {' or '.join(missing)}"
                         ' — a binding is proposed only by someone '
                         'authoritative on BOTH sides',
                'missingAuthority': missing}
    if existing is not None:  # revoked row: re-propose in place
        row = existing
        row.status = 'confirmed-local'
        row.proposed_by_subject = proposed_by_subject
        row.proposed_by_username = proposed_by_username
        row.identity_source = identity_source
        row.confirmed_local_at = _now()
        row.confirmed_remote_at = ''
        row.confirmed_remote_by = ''
        row.revoked_at = ''
        _persist(manager, row)
    else:
        row = GroupInstanceBinding(
            name=name, group_name=group_name,
            instance_name=instance_name, counterparty=counterparty,
            status='confirmed-local',
            proposed_by_subject=proposed_by_subject,
            proposed_by_username=proposed_by_username,
            identity_source=identity_source,
            confirmed_local_at=_now(), notes=notes, manager=manager)
        _insert(manager, 'GroupInstanceBinding', row)
    return {'ok': True, 'binding': binding_summary(row),
            'evidence': {
                'groupAuthority': [_grant_summary(g)
                                   for g in group_grants],
                'instanceAuthority': [_grant_summary(g)
                                      for g in instance_grants]}}
def submit_term_availability_signal(
        manager, term_name, context_name, group_name,
        instance_name='', concept_name='',
        requested_by_subject='', requested_by_username='',
        identity_source='payload-unverified', notes=''):
    """Adjudicate + persist a term-availability signal. The verdict
    (pass or fail) is stored on the row — refusals are part of the
    trail, not discarded errors."""
    missing = [f for f, v in (('term_name', term_name),
                              ('context_name', context_name),
                              ('group_name', group_name),
                              ('requested_by_subject',
                               requested_by_subject)) if not v]
    if missing:
        return {'ok': False,
                'error': f"missing required fields: {missing}"}
    instance_name = instance_name or _self_instance_name()
    name = f'tas--{term_name}--{context_name}--{group_name}'
    if _by_name(manager, 'TermAvailabilitySignal').get(name) \
            is not None:
        return {'ok': False,
                'error': f"a TermAvailabilitySignal named '{name}' "
                         'already exists',
                'suggestion': {
                    'knob': name,
                    'action': 'read the existing signal — the same '
                              'term/context/group request is already '
                              'decided'}}
    verdict = authority_check(manager, requested_by_subject,
                              group_name, instance_name)
    verdict['identitySource'] = identity_source
    status = 'admitted' if verdict['authorized'] else 'refused'
    row = TermAvailabilitySignal(
        name=name, term_name=term_name, context_name=context_name,
        concept_name=concept_name, group_name=group_name,
        instance_name=instance_name,
        requested_by_subject=requested_by_subject,
        requested_by_username=requested_by_username,
        identity_source=identity_source, status=status,
        verdict_json=json.dumps(verdict), created_at=_now(),
        decided_at=_now(), notes=notes, manager=manager)
    _insert(manager, 'TermAvailabilitySignal', row)
    return {'ok': True, 'admitted': status == 'admitted',
            'signal': signal_summary(row), 'verdict': verdict,
            'provenance': {
                'assertedByGroup': group_name,
                'viaInstance': instance_name,
                'requestedBy': requested_by_username
                or requested_by_subject} if status == 'admitted'
            else None}
