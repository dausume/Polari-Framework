"""
@module cmod.custom.approach_profile_doors

The approach pre-profiler's door (rt-0), a plain function over an ApproachProfileAPI (`cmod_approach_profile_api` registers the route and delegates here).
Read-only: everything is worked out per request (`cmod.custom.approach_profile`); nothing is stored.

GET /api/missions/{name}/approach[?board=B][&tier=T][&view=demand|tiers|priorities]
    {ok, mission, board, demand{}, recommended{tier, reasons[], caveats[], lowest_available, advice}, tiers{bare-c, freertos, zephyr}, priorities{}, chosen, notes[]}
    `board` defaults to the Mission's own board participant; `tier` asks what choosing that tier would cost (advised, never forced). With `view` the
    answer is flat plain-words {ok, view, board, count, rows[]} for the page tables.
    404 for an unknown Mission, 422 for an unknown board / tier / view.
"""
import falcon


def get_approach(api, request, response, name):
    from cmod.custom import approach_profile as AP
    view = (request.get_param('view') or '').strip()
    if view not in ('', 'demand', 'tiers', 'priorities'):
        response.status = falcon.HTTP_422
        response.media = {'ok': False, 'error': 'no view %r (demand, tiers or priorities)' % view}
        return
    try:
        res = AP.approach_profile(name, board=(request.get_param('board') or '').strip() or None, manager=api.manager,
                                  tier=(request.get_param('tier') or '').strip() or None)
    except ValueError as e:
        response.status = falcon.HTTP_404
        response.media = {'ok': False, 'error': str(e)}
        return
    except KeyError as e:
        response.status = falcon.HTTP_422
        response.media = {'ok': False, 'error': e.args[0] if e.args else str(e)}
        return
    if view:
        rows = {'demand': AP.demand_rows, 'tiers': AP.tier_rows, 'priorities': AP.priority_rows}[view](res)
        response.media = {'ok': True, 'view': view, 'mission': res['mission'], 'board': res['board'], 'count': len(rows), 'rows': rows}
        return
    response.media = res
