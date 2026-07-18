"""
@cross-cutting
@module scoring.group_authority
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

import json
import os
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit
from scoring.worldview_elections import _by_name, _rows

#: Authority roles. One active PRIMARY per group/instance; any number
#: of active SHARED grants.
AUTHORITY_ROLES = ('primary', 'shared')

#: Grant lifecycle. Revocation is an explicit act by the primary.
GRANT_STATUSES = ('active', 'revoked')

#: Binding lifecycle. 'confirmed-local' = the Polari side is defined
#: (an authorized proposal IS the local definition); 'active' only
#: through confirm-remote (the counterparty's side exists too).
BINDING_STATUSES = ('confirmed-local', 'active', 'revoked')

#: Signal lifecycle. Refused signals persist — the refusal verdict is
#: accountability data, not an error to discard.
SIGNAL_STATUSES = ('pending', 'admitted', 'refused')

#: The three admission checks, in the order they are reported.
AUTHORITY_CHECKS = ('group-authority', 'instance-authority',
                    'binding-active')


def _self_instance_name():
    """This instance's identity (same env contract as
    polariPeers.peers_api.instance_identity — kept local to avoid a
    scoring→peers import)."""
    iid = (os.environ.get('POLARI_INSTANCE_ID') or 'a').strip()
    return (os.environ.get('POLARI_INSTANCE_NAME')
            or f'polari-{iid}').strip()


def _now():
    return datetime.now(timezone.utc).isoformat()


class GroupAuthorityGrant(treeObject):
    """One user's authority (primary|shared) over one ScoreGroup."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('ga--<group>--<subject>').
        name: str = '',
        group_name: str = '',
        # Keycloak subject (sub claim) of the authority holder.
        subject: str = '',
        username: str = '',
        # AUTHORITY_ROLES entry.
        role: str = 'shared',
        # GRANT_STATUSES entry.
        status: str = 'active',
        granted_by_subject: str = '',
        granted_by_username: str = '',
        # 'keycloak-verified' | 'payload-unverified' at grant time.
        identity_source: str = 'payload-unverified',
        granted_at: str = '',
        revoked_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.group_name = group_name
        self.subject = subject
        self.username = username
        self.role = role
        self.status = status
        self.granted_by_subject = granted_by_subject
        self.granted_by_username = granted_by_username
        self.identity_source = identity_source
        self.granted_at = granted_at
        self.revoked_at = revoked_at
        self.notes = notes


class InstanceAuthorityGrant(treeObject):
    """One user's authority (primary|shared) over one Polari
    instance."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('ia--<instance>--<subject>').
        name: str = '',
        instance_name: str = '',
        subject: str = '',
        username: str = '',
        role: str = 'shared',
        status: str = 'active',
        granted_by_subject: str = '',
        granted_by_username: str = '',
        identity_source: str = 'payload-unverified',
        granted_at: str = '',
        revoked_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.instance_name = instance_name
        self.subject = subject
        self.username = username
        self.role = role
        self.status = status
        self.granted_by_subject = granted_by_subject
        self.granted_by_username = granted_by_username
        self.identity_source = identity_source
        self.granted_at = granted_at
        self.revoked_at = revoked_at
        self.notes = notes


class GroupInstanceBinding(treeObject):
    """One group's designation of one Polari instance as its
    authoritative source, defined on both sides."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('binding--<group>--<instance>').
        name: str = '',
        group_name: str = '',
        instance_name: str = '',
        # Who the remote side is (only 'psc' today).
        counterparty: str = 'psc',
        # BINDING_STATUSES entry.
        status: str = 'confirmed-local',
        proposed_by_subject: str = '',
        proposed_by_username: str = '',
        identity_source: str = 'payload-unverified',
        confirmed_local_at: str = '',
        confirmed_remote_at: str = '',
        confirmed_remote_by: str = '',
        revoked_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.group_name = group_name
        self.instance_name = instance_name
        self.counterparty = counterparty
        self.status = status
        self.proposed_by_subject = proposed_by_subject
        self.proposed_by_username = proposed_by_username
        self.identity_source = identity_source
        self.confirmed_local_at = confirmed_local_at
        self.confirmed_remote_at = confirmed_remote_at
        self.confirmed_remote_by = confirmed_remote_by
        self.revoked_at = revoked_at
        self.notes = notes


class TermAvailabilitySignal(treeObject):
    """One group's request that a term become available for a context
    on the PSC, adjudicated through authority_check."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('tas--<term>--<context>--<group>').
        name: str = '',
        term_name: str = '',
        context_name: str = '',
        # Optional: the Score the term is meant for.
        concept_name: str = '',
        group_name: str = '',
        instance_name: str = '',
        requested_by_subject: str = '',
        requested_by_username: str = '',
        identity_source: str = 'payload-unverified',
        # SIGNAL_STATUSES entry.
        status: str = 'pending',
        # The full authority_check verdict at decision time.
        verdict_json: str = '{}',
        created_at: str = '',
        decided_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.term_name = term_name
        self.context_name = context_name
        self.concept_name = concept_name
        self.group_name = group_name
        self.instance_name = instance_name
        self.requested_by_subject = requested_by_subject
        self.requested_by_username = requested_by_username
        self.identity_source = identity_source
        self.status = status
        self.verdict_json = verdict_json
        self.created_at = created_at
        self.decided_at = decided_at
        self.notes = notes


def _persist(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:
        pass  # in-memory managers (selftests) have no db


def _insert(manager, class_name, row):
    table = manager.objectTables.setdefault(class_name, {})
    if not any(existing is row for existing in table.values()):
        table[row.name] = row
    _persist(manager, row)
    return row


def _active_grants(manager, class_name, key_field, key_value):
    return [g for g in _rows(manager, class_name)
            if getattr(g, key_field, '') == key_value
            and getattr(g, 'status', '') == 'active']


def _grant_summary(grant):
    return {'name': grant.name, 'subject': grant.subject,
            'username': getattr(grant, 'username', ''),
            'role': grant.role, 'status': grant.status,
            'identitySource': getattr(grant, 'identity_source', ''),
            'grantedAt': getattr(grant, 'granted_at', '')}


def _known_instances(manager):
    """Instances a grant may target: this instance + known peers."""
    known = {_self_instance_name()}
    known.update(getattr(p, 'name', '')
                 for p in _rows(manager, 'PeerNode'))
    known.discard('')
    return known


# --------------------------------------------------------------- #
# 1. Authority grants (group + instance, same rules)
# --------------------------------------------------------------- #

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


def _revoke_authority(manager, class_name, key_field, key_value,
                      subject, revoker_subject):
    active = _active_grants(manager, class_name, key_field, key_value)
    primaries = [g for g in active if g.role == 'primary']
    if not any(g.subject == revoker_subject for g in primaries):
        return {'ok': False,
                'error': f"revoker '{revoker_subject}' does not hold "
                         f"the active primary grant on '{key_value}'",
                'activePrimary': [_grant_summary(g)
                                  for g in primaries]}
    target = [g for g in active if g.subject == subject]
    if not target:
        return {'ok': False,
                'error': f"subject '{subject}' holds no active grant "
                         f"on '{key_value}'",
                'activeGrants': [_grant_summary(g) for g in active]}
    row = target[0]
    row.status = 'revoked'
    row.revoked_at = _now()
    _persist(manager, row)
    result = {'ok': True, 'grant': _grant_summary(row)}
    if row.role == 'primary':
        result['warning'] = (f"'{key_value}' now has no primary "
                             'authority — the next primary claim is '
                             'first-come (bootstrap rule)')
    return result


def revoke_group_authority(manager, group_name, subject,
                           revoker_subject):
    return _revoke_authority(manager, 'GroupAuthorityGrant',
                             'group_name', group_name, subject,
                             revoker_subject)


def revoke_instance_authority(manager, instance_name, subject,
                              revoker_subject):
    instance_name = instance_name or _self_instance_name()
    return _revoke_authority(manager, 'InstanceAuthorityGrant',
                             'instance_name', instance_name, subject,
                             revoker_subject)


# --------------------------------------------------------------- #
# 2. Group ↔ instance bindings (both-sides definition)
# --------------------------------------------------------------- #

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


def confirm_binding_remote(manager, binding_name,
                           confirmed_by='psc-backend',
                           identity_source='payload-unverified'):
    """The counterparty (PSC backend) confirms its side exists —
    the both-sides moment that activates the binding."""
    row = _by_name(manager, 'GroupInstanceBinding').get(binding_name)
    if row is None:
        return {'ok': False,
                'error': f"no GroupInstanceBinding named "
                         f"'{binding_name}'",
                'knownBindings': sorted(
                    _by_name(manager, 'GroupInstanceBinding'))}
    if row.status == 'active':
        return {'ok': True, 'binding': binding_summary(row),
                'alreadyActive': True}
    if row.status != 'confirmed-local':
        return {'ok': False,
                'error': f"binding '{binding_name}' is "
                         f"'{row.status}' — only a confirmed-local "
                         'binding can be remote-confirmed'}
    row.status = 'active'
    row.confirmed_remote_at = _now()
    row.confirmed_remote_by = confirmed_by
    _persist(manager, row)
    return {'ok': True, 'binding': binding_summary(row),
            'identitySource': identity_source}


def revoke_binding(manager, binding_name, revoked_by_subject):
    """Either side's primary (group or instance) can revoke."""
    row = _by_name(manager, 'GroupInstanceBinding').get(binding_name)
    if row is None:
        return {'ok': False,
                'error': f"no GroupInstanceBinding named "
                         f"'{binding_name}'"}
    if row.status == 'revoked':
        return {'ok': True, 'binding': binding_summary(row),
                'alreadyRevoked': True}
    primaries = (
        [g for g in _active_grants(manager, 'GroupAuthorityGrant',
                                   'group_name', row.group_name)
         if g.role == 'primary']
        + [g for g in _active_grants(manager,
                                     'InstanceAuthorityGrant',
                                     'instance_name',
                                     row.instance_name)
           if g.role == 'primary'])
    if not any(g.subject == revoked_by_subject for g in primaries):
        return {'ok': False,
                'error': f"'{revoked_by_subject}' is not a primary "
                         'authority on either side of the binding',
                'activePrimary': [_grant_summary(g)
                                  for g in primaries]}
    row.status = 'revoked'
    row.revoked_at = _now()
    _persist(manager, row)
    return {'ok': True, 'binding': binding_summary(row)}


def binding_summary(row):
    return {'name': row.name, 'groupName': row.group_name,
            'instanceName': row.instance_name,
            'counterparty': row.counterparty, 'status': row.status,
            'proposedBy': row.proposed_by_username
            or row.proposed_by_subject,
            'identitySource': getattr(row, 'identity_source', ''),
            'confirmedLocalAt': row.confirmed_local_at,
            'confirmedRemoteAt': row.confirmed_remote_at,
            'confirmedRemoteBy': row.confirmed_remote_by}


# --------------------------------------------------------------- #
# 3. The admission verdict
# --------------------------------------------------------------- #

def authority_check(manager, subject, group_name, instance_name=''):
    """The three named checks behind 'this person may assert for
    this group through this instance'. Each check carries its
    evidence rows; the verdict is their conjunction."""
    instance_name = instance_name or _self_instance_name()
    checks = []
    group_grants = [g for g in _active_grants(
        manager, 'GroupAuthorityGrant', 'group_name', group_name)
        if g.subject == subject]
    checks.append({
        'check': 'group-authority', 'passed': bool(group_grants),
        'evidence': ([_grant_summary(g) for g in group_grants]
                     or f"no active grant for '{subject}' on group "
                        f"'{group_name}'")})
    instance_grants = [g for g in _active_grants(
        manager, 'InstanceAuthorityGrant', 'instance_name',
        instance_name) if g.subject == subject]
    checks.append({
        'check': 'instance-authority',
        'passed': bool(instance_grants),
        'evidence': ([_grant_summary(g) for g in instance_grants]
                     or f"no active grant for '{subject}' on "
                        f"instance '{instance_name}'")})
    binding = _by_name(manager, 'GroupInstanceBinding').get(
        f'binding--{group_name}--{instance_name}')
    active_binding = (binding is not None
                      and binding.status == 'active')
    checks.append({
        'check': 'binding-active', 'passed': active_binding,
        'evidence': (binding_summary(binding)
                     if binding is not None else
                     f"no binding for group '{group_name}' ↔ "
                     f"instance '{instance_name}'")})
    return {'ok': True,
            'authorized': all(c['passed'] for c in checks),
            'subject': subject, 'groupName': group_name,
            'instanceName': instance_name, 'checks': checks,
            'failedChecks': [c['check'] for c in checks
                             if not c['passed']]}


def authority_report(manager, group_name='', instance_name='',
                     subject=''):
    """Everything the hub UI needs in one read: grants + bindings,
    optionally filtered."""
    def keep(row, field, value):
        return not value or getattr(row, field, '') == value

    return {'ok': True,
            'selfInstance': _self_instance_name(),
            'groupGrants': [
                _grant_summary(g) | {'groupName': g.group_name}
                for g in _rows(manager, 'GroupAuthorityGrant')
                if keep(g, 'group_name', group_name)
                and keep(g, 'subject', subject)],
            'instanceGrants': [
                _grant_summary(g) | {'instanceName': g.instance_name}
                for g in _rows(manager, 'InstanceAuthorityGrant')
                if keep(g, 'instance_name', instance_name)
                and keep(g, 'subject', subject)],
            'bindings': [
                binding_summary(b)
                for b in _rows(manager, 'GroupInstanceBinding')
                if keep(b, 'group_name', group_name)
                and keep(b, 'instance_name', instance_name)]}


# --------------------------------------------------------------- #
# 4. Term-availability signals
# --------------------------------------------------------------- #

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


def signal_summary(row):
    try:
        verdict = json.loads(row.verdict_json or '{}')
    except Exception:
        verdict = {}
    return {'name': row.name, 'termName': row.term_name,
            'contextName': row.context_name,
            'conceptName': row.concept_name,
            'groupName': row.group_name,
            'instanceName': row.instance_name,
            'requestedBy': row.requested_by_username
            or row.requested_by_subject,
            'identitySource': row.identity_source,
            'status': row.status, 'verdict': verdict,
            'createdAt': row.created_at,
            'decidedAt': row.decided_at}


def signal_report(manager, name):
    row = _by_name(manager, 'TermAvailabilitySignal').get(name)
    if row is None:
        return {'ok': False,
                'error': f"no TermAvailabilitySignal named '{name}'",
                'knownSignals': sorted(
                    _by_name(manager, 'TermAvailabilitySignal'))}
    return {'ok': True, 'signal': signal_summary(row)}


def list_signals(manager, group_name='', status=''):
    rows = [s for s in _rows(manager, 'TermAvailabilitySignal')
            if (not group_name or s.group_name == group_name)
            and (not status or s.status == status)]
    return {'ok': True,
            'signals': [signal_summary(s) for s in rows]}
