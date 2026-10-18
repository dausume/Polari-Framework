"""
@module cmod.custom.mission_derived

What is WORKED OUT about a Hardware Mission every time it is asked and never stored on the Mission (MISSION_PROFILE_SOLVER_PLAN.md
section 2.1): each Purpose's own status and resolution (read from the Purpose via `cmod.custom.capabilities.derive_status` and
`cmod.custom.purpose_derived.resolution`, so the real HardwareBindings decide) and the Mission's own `resolution`:

    resolved    every safety and required Purpose is resolved (a valid binding lays its tasks over real hardware)
    unresolved  one or more is not - the reason names each Purpose and says why
    unbound     the Mission names no Purpose that can be judged

If the Mission has no safety or required Purpose, every Purpose it names decides instead (said in the reason). Cycle time and
resource use are UNDETERMINED until the solution search exists; the text says so rather than carrying a number.
"""
import inspect
import json

from cmod.custom import mission_text as T

HARD = ('safety', 'required')
DRAWING = '/display/hardware-solutions?solution=purpose-%s'


def _j(text, default):
    try:
        v = json.loads(text) if isinstance(text, str) and text else default
    except Exception:  # noqa: BLE001
        return default
    return v if isinstance(v, type(default)) else default


def mission_dict(row):
    """A HardwareMission row (or a seed dict) as a plain dict of its constructor fields."""
    if isinstance(row, dict):
        return dict(row)
    from cmod.objects.cmod.HardwareMission import HardwareMission
    keys = [k for k in inspect.signature(HardwareMission.__init__).parameters if k not in ('self', 'manager')]
    return {k: getattr(row, k, None) for k in keys}


def capability(name, manager=None):
    """The Purpose (CapabilityDefinition) named `name` as a dict - the live row when the manager holds one, else the seed - or None."""
    from cmod.custom import capabilities as CAP
    rows = ((getattr(manager, 'objectTables', None) or {}).get('CapabilityDefinition', {}) or {}).values() if manager is not None else []
    hit = next((r for r in rows if getattr(r, 'name', '') == name), None)
    if hit is not None:
        from cmod.cmod_capability_api import CapabilityAPI
        return CapabilityAPI._d(hit)
    seed = CAP.find(name)
    return dict(seed) if seed else None


def purpose_rows(mission, manager=None):
    """One dict per Purpose the Mission names, in its own order: {purpose, importance, known, title, lifecycle, status, last_proof,
    resolution, why, drawing}. status / resolution are DERIVED here from the Purpose; nothing is read from the Mission for them."""
    from cmod.custom import capabilities as CAP
    from cmod.custom import purpose_derived as PD
    out = []
    for p in _j(mission.get('purposes_json'), []):
        name = str(p.get('purpose', ''))
        cap = capability(name, manager)
        row = {'purpose': name, 'importance': str(p.get('importance', '')), 'known': cap is not None,
               'drawing': DRAWING % name}
        if cap is None:
            row.update(title=name, lifecycle='', status='', last_proof='', resolution='unresolved', why='there is no Purpose named %s' % name)
        else:
            status, last, _why, _kind = CAP.derive_status(cap, manager=manager)
            res = PD.resolution(cap, manager)
            row.update(title=cap.get('title') or name, lifecycle=cap.get('lifecycle') or 'enabled', status=status, last_proof=last,
                       resolution=res['state'], why=res['why'])
        out.append(row)
    return out


def resolution(mission, manager=None):
    """{state, why, purposes, deciding, unresolved, estimates} - DERIVED, never stored."""
    rows = purpose_rows(mission, manager)
    hard = [r for r in rows if r['importance'] in HARD]
    deciding, fallback = (hard, False) if hard else (rows, True)
    base = {'purposes': rows, 'deciding': [r['purpose'] for r in deciding], 'estimates': T.ESTIMATES}
    if not deciding:
        return dict(base, state='unbound', unresolved=[], why='the Mission names no Purpose yet, so there is nothing to put on hardware')
    bad = [r for r in deciding if r['resolution'] != 'resolved']
    scope = 'every Purpose it names' if fallback else 'every safety and required Purpose'
    if not bad:
        return dict(base, state='resolved', unresolved=[],
                    why='%s can run on real bound hardware (%s)' % (scope, ', '.join(r['purpose'] for r in deciding)))
    return dict(base, state='unresolved', unresolved=[r['purpose'] for r in bad],
                why='; '.join('%s is %s: %s' % (r['purpose'], r['resolution'], r['why']) for r in bad))
