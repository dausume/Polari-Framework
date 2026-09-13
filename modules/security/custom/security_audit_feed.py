"""
@module security.custom.security_audit_feed

The live feed: a machine posts its `os-security/audit.sh --json` output (pol security os audit --post URL,
pol deploy audit <node> --post URL) and it becomes a SecurityAuditRun row. The LATEST run per scenario is
what "today" means: applied_from_runs() turns its controls into the system → mode map the views and the
ledger read (in place of the hand-kept APPLIED_TODAY), and physical_from_runs() into the Secure Boot /
disk-encryption facts.
"""
import json
import time

from security.custom.security_facts import APPLIED_TODAY


def run_row_from_audit(payload, source=''):
    controls = payload.get('controls') or []
    return {'name': f"{payload.get('host', 'host')}:{payload.get('scenario') or 'dev'}:{payload.get('ran_at') or time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}",
            'host': payload.get('host', ''), 'scenario': payload.get('scenario') or 'dev', 'ran_at': payload.get('ran_at') or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'verdict': payload.get('verdict', ''), 'pass_count': int(payload.get('pass', 0)), 'fail_count': int(payload.get('fail', 0)), 'skip_count': int(payload.get('skip', 0)),
            'controls_json': json.dumps(controls)[:20000], 'containers_json': json.dumps(payload.get('containers') or [])[:20000], 'source': source}


def latest_runs(manager):
    """{scenario: run_row_dict} — the newest posted run per scenario."""
    tables = getattr(manager, 'objectTables', None) or {}
    out = {}
    for row in (tables.get('SecurityAuditRun') or {}).values():
        scn = getattr(row, 'scenario', '') or 'dev'
        if scn not in out or getattr(row, 'ran_at', '') > out[scn]['ran_at']:
            out[scn] = {'host': getattr(row, 'host', ''), 'ran_at': getattr(row, 'ran_at', ''), 'verdict': getattr(row, 'verdict', ''),
                        'controls': json.loads(getattr(row, 'controls_json', '[]') or '[]'), 'containers': json.loads(getattr(row, 'containers_json', '[]') or '[]')}
    return out


def _ctl(controls, name):
    return next((c for c in controls if c.get('control') == name), None)


def applied_from_controls(controls):
    """system → mode, read from the audit's controls (the honest 'today')."""
    applied = {}
    per_app = _ctl(controls, 'per-app-profiles'); node = _ctl(controls, 'node-profile'); enforcing = _ctl(controls, 'profiles-enforcing')
    if (per_app and per_app.get('status') == 'pass') or (node and node.get('status') == 'pass'):
        applied['polari-apparmor'] = 'enforce' if enforcing and enforcing.get('status') == 'pass' else 'complain'
    sec = _ctl(controls, 'seccomp-per-kind')
    if sec and sec.get('status') == 'pass':
        applied['polari-seccomp'] = 'enforce'
    du = _ctl(controls, 'docker-user-rules')
    if du and du.get('status') == 'pass':
        applied['docker-user'] = 'live'
    ufw = _ctl(controls, 'ufw')
    if ufw and ufw.get('status') == 'pass':
        applied['ufw'] = 'live'
    ov = _ctl(controls, 'overlay-encrypted')
    if ov and ov.get('status') == 'pass':
        applied['overlay-ipsec'] = 'live'
    ro = _ctl(controls, 'read-only-rootfs')
    if ro and ro.get('status') == 'pass':
        applied['polari-surface'] = 'live'
    un = _ctl(controls, 'userns-remap')
    if un and un.get('status') == 'pass':
        applied['userns'] = 'live'
    return applied


def physical_from_controls(controls):
    sb = _ctl(controls, 'secure-boot'); enc = _ctl(controls, 'disk-encryption')
    out = {}
    if sb and sb.get('status') in ('pass', 'fail'):
        out['secure_boot'] = sb['status'] == 'pass'
    if enc and enc.get('status') in ('pass', 'fail'):
        out['disk_encryption'] = enc['status'] == 'pass'
    return out


def applied_for(manager=None):
    """{scenario: {system: mode}} — audit runs win over the hand-kept table where a run exists."""
    applied = {k: dict(v) for k, v in APPLIED_TODAY.items()}
    if manager is not None:
        for scn, run in latest_runs(manager).items():
            applied[scn] = applied_from_controls(run['controls']) or applied.get(scn, {})
            applied[scn]['_from'] = f"audit run on {run['host']} at {run['ran_at']} ({run['verdict']})"
    return applied


def verdicts_for(manager=None):
    return {scn: run['verdict'] for scn, run in (latest_runs(manager) if manager is not None else {}).items()}
