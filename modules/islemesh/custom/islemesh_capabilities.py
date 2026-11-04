"""Pure, conservative app-target evaluation over explicit timestamped evidence.

No runtime probes or mutations. Existing agent/configuration booleans are NOT
promoted to capability evidence. Plans must be revalidated on the target before
execution; this report is not authorization to install.
"""
from datetime import datetime, timezone
import math

SCHEMA_VERSION = 1
MAX_AGE_SECONDS = 300
FAILURES = {'needs-setup', 'unsupported', 'resource-limited', 'policy-restricted'}
ACTIONS = {'use', 'launcher', 'host', 'module'}


def _date(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be an ISO string')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    return parsed.astimezone(timezone.utc)


def _scalar(value):
    return isinstance(value, (str, bool)) or (
        type(value) in (int, float) and math.isfinite(value))


def validate_evidence(report):
    """Validate a complete device capability report; reject rather than coerce."""
    if not isinstance(report, dict) or type(report.get('schema_version')) is not int or report['schema_version'] != 1:
        raise ValueError('capability evidence requires schema_version 1')
    facts = report.get('facts')
    if not isinstance(facts, dict) or len(facts) > 256:
        raise ValueError('facts must be an object with at most 256 entries')
    for dep, fact in facts.items():
        if not isinstance(dep, str) or not dep or len(dep) > 160 or not isinstance(fact, dict):
            raise ValueError('each fact requires a dependency name and evidence object')
        if fact.get('status') not in ('observed', 'error'):
            raise ValueError('fact status must be observed or error')
        if not isinstance(fact.get('source'), str) or not fact['source'].strip():
            raise ValueError('fact source is required')
        _date(fact.get('observed_at'))
        if fact['status'] == 'observed' and not _scalar(fact.get('value')):
            raise ValueError('observed value must be a finite scalar')
    return report


def validate_requirements(descriptor):
    if not isinstance(descriptor, dict) or type(descriptor.get('schema_version')) is not int or descriptor['schema_version'] != 1:
        raise ValueError('requirement descriptor requires schema_version 1')
    if descriptor.get('action') not in ACTIONS:
        raise ValueError('explicit action required: use, launcher, host or module')
    if not isinstance(descriptor.get('kind'), str) or not descriptor['kind']:
        raise ValueError('app kind is required')
    if descriptor['kind'] == 'hardware-app' and descriptor.get('realization') not in ('kvm', 'bridge'):
        raise ValueError('hardware-app requires an explicit supported realization')
    needs = descriptor.get('needs')
    if not isinstance(needs, list) or not needs or len(needs) > 128:
        raise ValueError('needs must contain 1..128 explicit requirements')
    seen = set()
    for need in needs:
        if not isinstance(need, dict) or not isinstance(need.get('dep'), str) or not need['dep']:
            raise ValueError('dependency name required')
        if need.get('scope') not in ('device', 'isle'):
            raise ValueError('scope must be device or isle')
        if need.get('check') not in ('present', 'equals', 'min'):
            raise ValueError('unknown requirement check')
        if need.get('failure', 'needs-setup') not in FAILURES:
            raise ValueError('unknown failure category')
        if need['check'] == 'min' and (type(need.get('value')) not in (int, float) or not math.isfinite(need['value']) or need['value'] < 0):
            raise ValueError('minimum must be finite and nonnegative')
        if need['check'] == 'equals' and not _scalar(need.get('value')):
            raise ValueError('comparison value required')
        group = need.get('group', need['dep'])
        if not isinstance(group, str) or not group:
            raise ValueError('provider group must be a nonempty string')
        key = (need['scope'], need['dep'])
        if key in seen:
            raise ValueError('duplicate dependency; aggregate resource demand before evaluation')
        seen.add(key)
    return descriptor


def _reason(dep, state, message, **extra):
    return dict(dep=dep, status=state, reason=message, **extra)


def check_fact(device, need, now):
    dep = need['dep']
    if device.get('is_mock') is True:
        return _reason(dep, 'unknown', 'Demonstration evidence cannot establish readiness')
    try:
        report = validate_evidence(device.get('capability_evidence'))
        fact = report['facts'].get(dep)
        if fact is None:
            return _reason(dep, 'unknown', 'No observation supplied')
        age = (now - _date(fact['observed_at'])).total_seconds()
        meta = dict(source=fact['source'], observed_at=fact['observed_at'])
        if age < -30:
            return _reason(dep, 'unknown', 'Observation clock is ahead; check the device clock', **meta)
        if fact['status'] != 'observed':
            return _reason(dep, 'unknown', 'Observation failed', **meta)
        value = fact['value']
        if need['check'] == 'present':
            if type(value) is not bool:
                return _reason(dep, 'unknown', 'Expected a boolean observation', **meta)
            matches = value is True
        elif need['check'] == 'min':
            if type(value) not in (int, float):
                return _reason(dep, 'unknown', 'Expected a numeric observation', **meta)
            matches = value >= need['value']
        else:
            matches = type(value) is type(need['value']) and value == need['value']
        state = 'ready' if matches else need.get('failure', 'needs-setup')
        if age > MAX_AGE_SECONDS:
            return _reason(dep, 'unknown', 'Last reported result retained; recheck before installation',
                           last_reported_status=state, value=value, **meta)
        return _reason(dep, state,
                       'Requirement satisfied' if matches else 'Requirement not satisfied',
                       value=value, **meta)
    except (ValueError, TypeError, OverflowError):
        return _reason(dep, 'unknown', 'Missing or invalid capability report')


def _verdict(checks):
    states = {c['status'] for c in checks}
    for status in ('policy-restricted', 'unsupported', 'resource-limited', 'needs-setup', 'blocked', 'unknown'):
        if status in states:
            return status
    return 'ready' if checks else 'unknown'


def evaluate_target(descriptor, target, devices, now=None):
    now = now or datetime.now(timezone.utc)
    result = dict(device=target.get('name', ''), status='unknown', checks=[], providers={},
                  schema_version=SCHEMA_VERSION, evaluated_at=now.isoformat(),
                  revalidation_required=True)
    try:
        validate_requirements(descriptor)
    except (ValueError, TypeError):
        result['checks'] = [_reason('requirements', 'unknown', 'App requirements are missing or invalid')]
        return result
    result['action'] = descriptor['action']
    checks = result['checks']
    if descriptor.get('complete') is not True:
        checks.append(_reason('requirements', 'unknown', 'App-specific requirement closure is incomplete'))
    if target.get('is_mock') is True:
        checks.append(_reason('device', 'unknown', 'Demonstration device is not an installation target'))
        return result
    groups = {}
    for need in descriptor['needs']:
        if need['scope'] == 'device':
            checks.append(check_fact(target, need, now))
        else:
            groups.setdefault(need.get('group', need['dep']), []).append(need)
    for group, needs in groups.items():
        candidates = []
        for device in devices:
            if device.get('is_mock') is True:
                continue
            evidence = [check_fact(device, need, now) for need in needs]
            candidates.append(dict(device=device.get('name', ''), status=_verdict(evidence),
                                   last_reported_status=_verdict([dict(c, status=c.get('last_reported_status', c['status'])) for c in evidence]), checks=evidence))
        ready = [c['device'] for c in candidates if c['status'] == 'ready']
        result['providers'][group] = ready
        if ready:
            checks.append(_reason(group, 'ready', 'Compatible provider reported', providers=ready))
        else:
            # Unknown alternatives can still be compatible; do not call the whole
            # Isle unsupported just because a known device cannot provide this.
            if not candidates or any(any(c['status'] == 'unknown' for c in candidate['checks']) for candidate in candidates):
                status = 'unknown'
            elif all(c['status'] == 'unsupported' for c in candidates):
                status = 'unsupported'
            elif all(c['status'] == 'policy-restricted' for c in candidates):
                status = 'policy-restricted'
            elif any(c['status'] == 'resource-limited' for c in candidates):
                status = 'resource-limited'
            elif any(c['status'] == 'needs-setup' for c in candidates):
                status = 'needs-setup'
            else:
                status = 'blocked'
            checks.append(_reason(group, status, 'No current provider satisfies this requirement group',
                                  last_reported_status='ready' if any(c['last_reported_status'] == 'ready' for c in candidates) else status, candidates=candidates))
    result['status'] = _verdict(checks)
    result['last_reported_status'] = _verdict([dict(c, status=c.get('last_reported_status', c['status'])) for c in checks])
    return result


def evaluate_isle(descriptor, devices, now=None):
    now = now or datetime.now(timezone.utc)
    targets = [evaluate_target(descriptor, d, devices, now) for d in devices if d.get('is_mock') is not True]
    ready = [t['device'] for t in targets if t['status'] == 'ready']
    if ready:
        status = 'ready'
    elif not targets or any(any(c['status'] == 'unknown' for c in t['checks']) for t in targets):
        status = 'unknown'
    elif all(t['status'] == 'unsupported' for t in targets):
        status = 'unsupported'
    elif all(t['status'] == 'policy-restricted' for t in targets):
        status = 'policy-restricted'
    elif any(t['status'] == 'needs-setup' for t in targets):
        status = 'needs-setup'
    elif any(t['status'] == 'resource-limited' for t in targets):
        status = 'resource-limited'
    else:
        status = 'blocked'
    historical = [t.get('last_reported_status', t['status']) for t in targets]
    last_reported = 'ready' if 'ready' in historical else status
    if status == 'unknown' and historical and 'unknown' not in historical:
        last_reported = _verdict([{'status': state} for state in historical])
    return dict(schema_version=1, evaluated_at=now.isoformat(), status=status,
                last_reported_status=last_reported,
                ready_devices=ready, targets=targets, revalidation_required=True)
