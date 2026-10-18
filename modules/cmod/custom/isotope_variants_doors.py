"""
@module cmod.custom.isotope_variants_doors

The isotope variant doors (iso-0), plain functions over an IsotopeVariantAPI (`cmod_isotope_api` registers the routes and delegates here).
Read-only: the rows are code-owned seeds; everything derived is worked out per request (`cmod.custom.isotope_variants`).

GET /api/atom-jobs                         {ok, rows[]}  every job with its atoms (listed + found by its pin macro), purposes, variant counts, best status
GET /api/atom-jobs/{job}/variants          {ok, job, board, rows[]}  every variant of the job with status, costs, parts (on the bench or not) and,
                                           with ?board=, the eligibility on that board (?tier= asks for a runtime tier); 404 for an unknown job,
                                           422 for an unknown board or tier
GET /api/atom-variants                     {ok, board, rows[]}  every variant of every job in one flat table (the page reads this); ?board= as above
"""


def _board_ctx(request, response):
    """-> (ctx or None, board, tier, ok)"""
    import falcon
    from cmod.custom import isotope_variants_eligibility as E
    board = (request.get_param('board') or '').strip()
    tier = (request.get_param('tier') or '').strip() or None
    if not board:
        return None, '', tier, True
    ctx = E.context(board)
    if ctx is None:
        response.status = falcon.HTTP_422
        response.media = {'ok': False, 'error': 'no board %r with a SoC row (known: %s)' % (board, ', '.join(E.boards()))}
        return None, board, tier, False
    return ctx, board, tier, True


def jobs_table(api, request, response):
    from cmod.custom import isotope_variants as IV
    response.media = {'ok': True, 'rows': [IV.job_dict(j, api.manager) for j in IV.jobs(api.manager)]}


def job_variants(api, request, response, job):
    import falcon
    from cmod.custom import isotope_variants as IV
    j = next((x for x in IV.jobs(api.manager) if x['name'] == job), None)
    if j is None:
        response.status = falcon.HTTP_404
        response.media = {'ok': False, 'error': 'no job %r (GET /api/atom-jobs lists them)' % job}
        return
    ctx, board, tier, ok = _board_ctx(request, response)
    if not ok:
        return
    response.media = {'ok': True, 'job': IV.job_dict(j, api.manager), 'board': board,
                      'rows': [IV.variant_dict(v, ctx, api.manager, tier) for v in IV.variants(api.manager, job)]}


def all_variants(api, request, response):
    from cmod.custom import isotope_variants as IV
    ctx, board, tier, ok = _board_ctx(request, response)
    if not ok:
        return
    response.media = {'ok': True, 'board': board, 'rows': [IV.variant_dict(v, ctx, api.manager, tier) for v in IV.variants(api.manager)]}
