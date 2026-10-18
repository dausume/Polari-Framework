"""
@module firmwarefaults.custom.route_proof

THE ROUTE-PROOF DOOR'S RULES (POST /api/firmwarefaults/runs). A finished ScenarioRun of an isotope-variant (route) acceptance
Scenario, proved elsewhere (`pol faults run <scenario> --api URL`), is stored here so the isotope catalogue can read the route
as proven-on-twin. The Purpose door (POST /api/capabilities/<name>/runs) only takes a Purpose's OWN acceptance_scenario; this
door takes exactly the others. It never changes a Purpose's status, and it runs nothing: a pure validate + upsert.

    accept(body, manager) -> (http_status, media)
"""


def refusal(why):
    return 422, {'ok': False, 'error': why}


def purpose_owner(scenario):
    """The Purpose whose own acceptance_scenario is `scenario`, or ''."""
    from cmod.custom import capabilities as CAP
    return next((c['name'] for c in CAP.SEED_CAPABILITIES if c.get('acceptance_scenario') == scenario), '')


def variant_rows(scenario, manager=None):
    """iso-0 variant names (the catalogue's rows) whose implemented_by.proof_scenarios name `scenario`."""
    import json
    from cmod.custom import isotope_variants as IV
    out = []
    for v in IV.variants(manager):
        try:
            imp = json.loads(v.get('implemented_by_json') or '{}')
        except ValueError:
            imp = {}
        if scenario in (imp.get('proof_scenarios') or []):
            out.append(v['name'])
    return out


def accept(body, manager):
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom.sink import ManagerSink
    if manager is None:
        return refusal('no live manager on this server to store a run on')
    if not isinstance(body, dict) or not body:
        return refusal('the run is empty or malformed: send the finished ScenarioRun as a JSON object')
    scenario = body.get('scenario')
    if not scenario or not isinstance(scenario, str):
        return refusal('the run names no scenario')
    sc = ACC.find(scenario)
    if sc is None:
        return refusal('no acceptance scenario named %r (an unknown, or non-acceptance, scenario is not stored here)' % scenario)
    if sc.get('kind') != 'acceptance':
        return refusal('scenario %r is not an acceptance scenario' % scenario)
    owner = purpose_owner(scenario)
    if owner:
        return refusal('scenario %r is the own acceptance scenario of Purpose %r: send it to POST /api/capabilities/%s/runs, '
                       'not here' % (scenario, owner, owner))
    if not body.get('name') or not isinstance(body.get('name'), str):
        return refusal('run has no name')
    if body.get('outcome') not in ('passed', 'failed', 'inapplicable', 'undetermined'):
        return refusal("run outcome must be one of passed, failed, inapplicable, undetermined (got %r)" % (body.get('outcome'),))
    if not body.get('ran_at') or not isinstance(body.get('ran_at'), str):
        return refusal('run has no ran_at time')
    variant = ACC.VARIANT_PROOFS.get(scenario) or sc.get('before_variant') or ''
    if not variant:
        return refusal('scenario %r names no variant it proves' % scenario)
    row = dict(body)
    row['scenario'] = scenario
    row['variant'] = variant
    row.setdefault('side', 'acceptance')
    ManagerSink(manager).upsert('ScenarioRun', row)
    return 201, {'ok': True, 'run': row, 'scenario': scenario, 'variant': variant, 'variant_rows': variant_rows(scenario, manager)}
