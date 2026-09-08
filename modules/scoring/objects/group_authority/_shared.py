"""@module scoring.objects.group_authority._shared — what the group_authority row classes share (constants, seeds, helpers); split from group_authority_basis.py (sap-2c)."""
from scoring.worldview_elections_basis import _by_name, _rows
from datetime import datetime, timezone
import json
import os

AUTHORITY_ROLES = ('primary', 'shared')
GRANT_STATUSES = ('active', 'revoked')
BINDING_STATUSES = ('confirmed-local', 'active', 'revoked')
SIGNAL_STATUSES = ('pending', 'admitted', 'refused')
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
