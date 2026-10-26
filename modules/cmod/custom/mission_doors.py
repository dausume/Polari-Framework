"""
@module cmod.custom.mission_doors

The Hardware Mission no-code doors (mis-0), implemented as plain functions over a MissionAPI (`cmod_mission_api` registers the
routes and delegates here). The model is `cmod.custom.mission_nocode` and `cmod.custom.mission_derived`; these only read and write rows.

GET  /api/missions                      the Missions table: every Mission with its aim, derived resolution and the link to its drawing
GET  /api/missions/{name}/solution      the Mission drawn as a no-code solution (category 'mission'), the last state worked out NOW.
                                        {ok, solution (the SolutionDefinition row dict), definition (the graph)}
PUT  /api/missions/{name}/solution      body = the drawing (the `definition` GET gave, or {"definition": ...}). Writes the edits back to the
                                        Mission ROW (the one door; the drawing is never a second copy). 422 naming the state when the
                                        drawing holds a non-Mission kind, an edit to a derived field, or an unknown life stage / aim /
                                        importance / Purpose / board / stage / participant kind. Returns {ok, changes, solution, definition}.
GET  /api/missions/{name}/resolution    {state: resolved|unresolved|unbound, why, purposes[], estimates} worked out from the Purposes
"""
import json


def _body(request):
    try:
        return json.loads(request.bounded_stream.read() or b'{}')
    except Exception:  # noqa: BLE001
        return {}


def _save(api, row):
    db = getattr(api.manager, 'db', None) if api.manager is not None else None
    if db is not None and hasattr(db, 'saveInstanceInDB'):
        db.saveInstanceInDB(row)


def _m(api, row):
    from cmod.custom import mission_derived as MD
    return MD.mission_dict(row)


def get_solution(api, request, response, name):
    from cmod.custom import mission_nocode as MN
    row = api._mission(name, response)
    if row is None:
        return
    m = _m(api, row)
    response.media = {'ok': True, 'solution': MN.render(m, api.manager), 'definition': MN.render_definition(m, api.manager)}


def put_solution(api, request, response, name):
    import falcon
    from cmod.custom import mission_nocode as MN
    row = api._mission(name, response)
    if row is None:
        return
    body = _body(request)
    definition = body.get('definition') if isinstance(body.get('definition'), dict) else body
    ok, why, changes = MN.write_back(definition, _m(api, row), api.manager)
    if not ok:
        response.status = falcon.HTTP_422
        response.media = {'ok': False, 'refused': True, 'error': why}
        return
    for k, v in changes.items():
        setattr(row, k, v)
    if changes:
        _save(api, row)
    m = _m(api, row)
    sol = MN.render(m, api.manager, derive=False)
    live = next((r for r in api._rows('SolutionDefinition') if r.name == sol['name']), None)
    if live is not None and changes:         # keep the stored drawing in step with the row it is drawn from
        live.definition = sol['definition']
        _save(api, live)
    response.media = {'ok': True, 'changes': sorted(changes), 'solution': MN.render(m, api.manager),
                      'definition': MN.render_definition(m, api.manager)}


def get_resolution(api, request, response, name):
    from cmod.custom import mission_derived as MD
    row = api._mission(name, response)
    if row is not None:
        response.media = dict(MD.resolution(_m(api, row), api.manager), ok=True)


def missions_table(api, request, response):
    """Every Mission as a table row: the stored fields and the DERIVED resolution, plus the drawing link. `purposes` is the COUNT; wb-2 adds `purposes_text`
    ('purpose (importance), ...' as one plain string) so a card can show them."""
    from cmod.custom import mission_derived as MD
    from cmod.custom import mission_nocode as MN
    from cmod.custom import mission_seeds as MS
    if api.manager is not None and api._rows('HardwareMission'):
        ms = [MD.mission_dict(r) for r in sorted(api._rows('HardwareMission'), key=lambda r: r.name)]
    else:
        ms = [dict(x) for x in MS.MISSION_SEEDS]
    rows = []
    for m in ms:
        res = MD.resolution(m, api.manager)
        con = MD._j(m.get('constraints_json'), {})
        rows.append({'name': m['name'], 'title': m.get('title', ''), 'goal': m.get('goal', ''), 'lifecycle': m.get('lifecycle') or 'enabled',
                     'objective': MN.settings_of(m)['objective'], 'stage': con.get('stage', ''),
                     'purposes': len(MD._j(m.get('purposes_json'), [])), 'purposes_text': ', '.join('%s (%s)' % (x.get('purpose', '?'), x.get('importance', '?')) for x in MD._j(m.get('purposes_json'), [])) or 'none', 'resolution': '%s: %s' % (res['state'], res['why']),
                     'drawing': '/display/hardware-solutions?solution=%s' % MN.solution_name(m['name'])})
    response.media = {'ok': True, 'rows': rows}
