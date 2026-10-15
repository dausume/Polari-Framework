"""
@module cmod.custom.purpose_doors

The Purpose no-code doors (fgm-1, FIRMWARE_GENERATION_MODULE_PLAN.md §8.3), implemented as plain functions over a CapabilityAPI
(`cmod_capability_api` registers the routes and delegates here, so that file stays small). The model is `cmod.custom.purpose_nocode`
and `cmod.custom.purpose_derived`; these only read and write rows.

GET  /api/capabilities/{name}/solution      the Purpose drawn as a no-code solution (category 'purpose'), the three derived states worked
                                            out NOW. {ok, solution (the SolutionDefinition row dict), definition (the graph)}
PUT  /api/capabilities/{name}/solution      body = the drawing (the `definition` GET gave, or {"definition": …}). Writes the edits back to
                                            the Purpose ROW (the one door; the drawing is never a second copy). 422 naming the state when
                                            the drawing holds a non-Purpose kind, an edit to a derived state, an unknown life stage /
                                            dependency / participant, or a changed task list. Returns {ok, changes, solution, definition}.
GET  /api/capabilities/{name}/resolution    {state: resolved|unresolved|blocked, why, bindings} worked out from the actual HardwareBindings
GET  /api/capabilities/{name}/observations  the per-device rows + the summary (the weakest device)
POST /api/capabilities/{name}/observations  THE BACKEND'S WRITER: body {board_instance, fulfillment, health, why?, evidence?, observed_at?}.
                                            403 for anyone who is not the backend's own service account - a person's POST is refused (a
                                            person who disagrees records a DerivedOverride). 404 unknown Purpose; 400 a bad word.
GET  /api/purposes                          the Purposes table: every Purpose with its derived resolution + observed columns and the
                                            link to its drawing (the c-canvas page reads this).
"""
import json

BACKEND_CLIENT = 'polari-backend'


def is_backend(request):
    """True only for the backend's own Keycloak service account (preferred_username 'service-account-polari-backend' or client
    polari-backend). A signed-in person, or an anonymous request, is NOT the backend."""
    ui = getattr(getattr(request, 'context', None), 'user_info', None)
    if not isinstance(ui, dict):
        return False
    return (str(ui.get('preferred_username') or '') == 'service-account-' + BACKEND_CLIENT
            or str(ui.get('azp') or ui.get('client_id') or '') == BACKEND_CLIENT)


def _body(request):
    try:
        return json.loads(request.bounded_stream.read() or b'{}')
    except Exception:  # noqa: BLE001
        return {}


def _save(api, row):
    db = getattr(api.manager, 'db', None) if api.manager is not None else None
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        db.saveInstanceInDB(row)


def _cap(api, row):
    return api._d(row)


def get_solution(api, request, response, name):
    from cmod.custom import purpose_nocode as PN
    row = api._capability(name, response)
    if row is None:
        return
    cap = _cap(api, row)
    response.media = {'ok': True, 'solution': PN.render(cap, api.manager), 'definition': PN.render_definition(cap, api.manager)}


def put_solution(api, request, response, name):
    import falcon
    from cmod.custom import purpose_nocode as PN
    row = api._capability(name, response)
    if row is None:
        return
    body = _body(request)
    definition = body.get('definition') if isinstance(body.get('definition'), dict) else body
    cap = _cap(api, row)
    ok, why, changes = PN.write_back(definition, cap, api.manager)
    if not ok:
        response.status = falcon.HTTP_422
        response.media = {'ok': False, 'refused': True, 'error': why}
        return
    for k, v in changes.items():
        setattr(row, k, v)
    if changes:
        _save(api, row)
    cap = _cap(api, row)
    sol = PN.render(cap, api.manager, derive=False)
    live = next((r for r in api._rows('SolutionDefinition') if r.name == sol['name']), None)
    if live is not None and changes:         # keep the stored drawing in step with the row it is drawn from
        live.definition = sol['definition']
        _save(api, live)
    response.media = {'ok': True, 'changes': sorted(changes), 'solution': PN.render(cap, api.manager),
                      'definition': PN.render_definition(cap, api.manager)}


def get_resolution(api, request, response, name):
    from cmod.custom import purpose_derived as PD
    row = api._capability(name, response)
    if row is not None:
        response.media = dict(PD.resolution(_cap(api, row), api.manager), ok=True)


def get_observations(api, request, response, name):
    from cmod.custom import purpose_derived as PD
    row = api._capability(name, response)
    if row is not None:
        response.media = dict(PD.observed_summary(_cap(api, row), api.manager), ok=True)


def post_observations(api, request, response, name):
    import falcon
    from cmod.custom import purpose_derived as PD
    if not is_backend(request):
        response.status = falcon.HTTP_403
        response.media = {'ok': False, 'error': 'only the backend writes what a board was observed to do; a person who disagrees '
                                                'records a derived override instead (POST /api/firmware/overrides)'}
        return
    row = api._capability(name, response)
    if row is None:
        return
    b = _body(request)
    if api.manager is None:
        response.status = falcon.HTTP_422
        response.media = {'ok': False, 'error': 'no live manager on this server to store an observation on'}
        return
    ok, why, out = PD.record_observation(api.manager, name, b.get('board_instance', ''), b.get('fulfillment', ''), b.get('health', ''),
                                        why=b.get('why', ''), evidence=b.get('evidence', ''), observed_at=b.get('observed_at', ''))
    if not ok:
        response.status = falcon.HTTP_400
        response.media = {'ok': False, 'error': why}
        return
    response.media = {'ok': True, 'observation': out, 'summary': PD.observed_summary(_cap(api, row), api.manager)}


def purposes_table(api, request, response):
    """Every Purpose as a table row: the stored fields, the DERIVED status / resolution / observed, and the drawing link."""
    from cmod.custom import capabilities as CAP
    from cmod.custom import purpose_derived as PD
    from cmod.custom import purpose_nocode as PN
    rows = []
    if api.manager is not None and api._rows('CapabilityDefinition'):
        caps = [api._d(r) for r in sorted(api._rows('CapabilityDefinition'), key=lambda r: r.name)]
    else:
        caps = [dict(c) for c in sorted(CAP.SEED_CAPABILITIES, key=lambda c: c['name'])]
    for cap in caps:
        status, last, _why, _pk = CAP.derive_status(cap, manager=api.manager)
        res, obs = PD.resolution(cap, api.manager), PD.observed_summary(cap, api.manager)
        rows.append({'name': cap['name'], 'title': cap.get('title', ''), 'goal': cap.get('goal', ''),
                     'lifecycle': cap.get('lifecycle') or 'enabled', 'status': status, 'last_proof': last,
                     'resolution': '%s: %s' % (res['state'], res['why']), 'observed': obs['summary'],
                     'depends_on': cap.get('depends_on', ''), 'required_targets': cap.get('required_targets', ''),
                     'exposes_fields': cap.get('exposes_fields', ''), 'instance_count': cap.get('instance_count', 0),
                     'drawing': '/display/hardware-solutions?solution=%s' % PN.solution_name(cap['name'])})
    response.media = {'ok': True, 'rows': rows}
