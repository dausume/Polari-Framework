"""
@module cmod.custom.pin_profile_doors

pp-0 doors, as plain functions over a PinProfileAPI (cmod.cmod_pin_profile_api registers the routes and delegates here):

GET /api/capabilities/{name}/pin-profiles   the pin profiles of one Purpose, DERIVED now {ok, purpose, profiles[], rows[], unresolved[], ignored[], other_runtime[]}
                                            404 naming the Purpose when there is none.
GET /api/missions/{name}/pin-profiles       the Mission roll-up {ok, mission, basis, purposes[], profiles[], rows[], unresolved[], pins_needed}. The Mission is a HardwareMission
                                            row (mis-0) when the server has one; `?purposes=a,b` names the Purposes instead (the fallback, and what makes the door
                                            work before mis-0 is merged). 404 when neither resolves.
GET /api/pin-profiles                       flat plain-words rows for the page tables: `?view=purposes` (default: every Purpose with a profile), `?view=mission&purposes=a,b`
                                            (or `&mission=name`), `?view=unresolved` (the tasks that gave no profile and why).
`rows` are one-line plain-words summaries (no JSON); `profiles` carry the full structure with the evidence of every field.
"""
import falcon

from cmod.custom import pin_profiles as PP
from cmod.custom import pin_profile_mission as PM


def _csv(request, key):
    return [x.strip() for x in (request.params.get(key) or '').split(',') if x.strip()]


def get_purpose(api, request, response, name):
    try:
        res = PP.derive_profiles(name, manager=api.manager)
    except ValueError as e:
        response.status = falcon.HTTP_404
        response.media = {'ok': False, 'error': str(e)}
        return
    response.media = dict(res, ok=True, rows=[PP.summary(p) for p in res['profiles']])


def get_mission(api, request, response, name):
    try:
        res = PM.mission_profiles(name, purposes=_csv(request, 'purposes') or None, manager=api.manager)
    except ValueError as e:
        response.status = falcon.HTTP_404
        response.media = {'ok': False, 'error': str(e)}
        return
    response.media = dict(res, ok=True, rows=[PP.summary(p) for p in res['profiles']])


def _all_purposes(manager):
    """Every live (not retired) Purpose that names at least one c-device task."""
    import json
    from cmod.custom import capabilities as CAP
    from cmod.custom import pin_profile_bench as PB
    out = []
    for c in sorted(PB.rows(manager, 'CapabilityDefinition', CAP.SEED_CAPABILITIES), key=lambda c: c['name']):
        try:
            tasks = json.loads(c.get('tasks_by_runtime_json') or '{}')
        except ValueError:
            tasks = {}
        if c.get('lifecycle') != 'retired' and tasks.get('c-device'):
            out.append(c['name'])
    return out


def get_table(api, request, response):
    view = request.params.get('view') or 'purposes'
    names = _csv(request, 'purposes')
    try:
        if view == 'mission':
            res = PM.mission_profiles(request.params.get('mission') or '', purposes=names or None, manager=api.manager)
            rows = [PP.summary(p) for p in res['profiles']]
        else:
            rows = []
            for n in (names or _all_purposes(api.manager)):
                res = PP.derive_profiles(n, manager=api.manager)
                if view == 'unresolved':
                    rows += [{'purpose': n, 'task': u['task'], 'why': u['why']} for u in res['unresolved'] + res['ignored']]
                else:
                    rows += [PP.summary(p) for p in res['profiles']]
    except ValueError as e:
        response.status = falcon.HTTP_404
        response.media = {'ok': False, 'error': str(e)}
        return
    response.media = {'ok': True, 'view': view, 'count': len(rows), 'rows': rows}
