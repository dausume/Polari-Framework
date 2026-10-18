"""
@module cmod.custom.fsc_doors

fsc-2 doors (plain functions over a FscAPI; `cmod_fsc_api` registers the routes). Plain-words fields only - the frontend reads them with configured tables. Advised, never blocking.

GET  /api/firmware-scores?mission=&profile=&scope=&board=&normalization=&limit=
       (fsc-3: `label` is the SHORT label, `long_label` the route string; `limit=N` keeps only the N best SCORED rows - the page's bar chart; failed rows are left out when it is set;
       every row also carries `short_label`, e.g. `button ext-int · sense poll · LED out · UNO`)
       rows top -> bottom by the first profile asked (default: every profile, sorted by the first): {rank, solution, label, state finished|plan|failed, score, raw, confidence,
       deciding_terms (the 2-3 largest weighted contributions, single profile only), routes, built_as, also_on, scores {profile: {score, rank, rank_among_finished}}}; failed
       solutions follow with state `failed`, the Purpose they fail and the reason, and NO score. Also: failures[], suggestions[] (flag a safety deadline?), unmatched_configs[], set.
GET  /api/firmware-scores/top?mission=&scope=      the main tab: one row per profile {profile, profile_title, top_solution, top_state, score 100, runner_up, runner_up_score, compared_set, failed_count}
GET  /api/firmware-scores/breakdown?mission=&solution=&profile=    term rows (also under `rows`, for the tables) {term, context, value, unit, kind, normalized, weight, points, basis, normalization}
POST /api/firmware-scores/values   {mission?, limit?}   write the term values down as ScoreContext / ScoreSubject / ContextualizedValue rows (pol firmware score-values refresh)
GET  /api/firmware-score-profiles      every profile (seeded + the person's own)
POST /api/firmware-score-profiles      {name, copy_of?, display_name?, description?, weights?{term: w}, purpose_weights?{purpose: {term: w}}, alpha?, knobs?, hardware?}
       creates or copies a profile, or sets weights on the person's own; a SEEDED profile is never edited in place (409: copy it). Unknown keys / terms / knobs -> 422 naming the known ones.
"""
import json
import re

import falcon

from cmod.custom import fsc_profiles as P
from cmod.custom import fsc_run as R
from cmod.custom import fsc_store as ST
from cmod.custom import fsc_terms as T

DEFAULT_MISSION = 'uno-light-mission'
# `rev` is a page cache-buster (the page appends rev=r<n> after an edit so its tables refetch); it changes nothing here
GET_KEYS = {'scores': ('mission', 'profile', 'scope', 'board', 'normalization', 'unprovable', 'limit', 'rev'), 'top': ('mission', 'scope', 'board', 'normalization', 'unprovable', 'rev'),
            'breakdown': ('mission', 'solution', 'profile', 'scope', 'board', 'normalization', 'unprovable', 'rev')}
NAME_RE = re.compile(r'^[a-z0-9][a-z0-9-]{1,62}$')


def _fail(response, status, text):
    response.status = status
    response.media = {'ok': False, 'error': text}


def _body(request):
    try:
        b = json.loads(request.bounded_stream.read() or b'{}')
        return b if isinstance(b, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _params(request, response, which):
    p = request.params
    bad = sorted(k for k in p if k not in GET_KEYS[which])
    if bad:
        _fail(response, falcon.HTTP_422, 'unknown parameter(s) %s (known: %s)' % (', '.join(bad), ', '.join(GET_KEYS[which])))
        return None
    if p.get('scope', 'both') not in R.SCOPES:
        _fail(response, falcon.HTTP_422, 'no scope %r (one of %s)' % (p.get('scope'), ', '.join(R.SCOPES)))
        return None
    if p.get('normalization') and p['normalization'] not in T.NORMALIZATIONS:
        _fail(response, falcon.HTTP_422, 'no normalization %r (one of %s)' % (p['normalization'], ', '.join(T.NORMALIZATIONS)))
        return None
    if p.get('unprovable', 'block') not in ('block', 'ignore'):
        _fail(response, falcon.HTTP_422, "unprovable is 'block' (default: a Purpose with no acceptance scenario keeps a solution from being finished) or 'ignore'")
        return None
    return p


def _built(api, response, p):
    try:
        return R.build(p.get('mission') or DEFAULT_MISSION, api.manager, [b for b in p.get('board', '').split(',') if b] or None, None, p.get('unprovable', 'block'))
    except ValueError as e:
        _fail(response, falcon.HTTP_404, str(e))
    except KeyError as e:
        _fail(response, falcon.HTTP_422, e.args[0] if e.args else str(e))
    return None


def _profiles(api, response, names):
    allp = P.all_profiles(api.manager)
    if not names:
        return list(allp.values())
    out = []
    for n in [x.strip() for x in names.split(',') if x.strip()]:
        if n not in allp:
            _fail(response, falcon.HTTP_422, 'no profile %r (known: %s)' % (n, ', '.join(sorted(allp))))
            return None
        out.append(allp[n])
    return out


def deciding(score_row, n=3):
    top = sorted((r for r in score_row['rows'] if r['points'] > 0), key=lambda r: (-r['points'], r['term']))[:n]
    return '; '.join('%s %s (%.1f of %.0f points)' % (r['label'], ('= %s %s' % (round(r['value'], 2), r['unit'])).strip() if r['value'] is not None else 'has no value', r['points'], 100) for r in top)


def _built_as(rec):
    k = rec['link']
    if not k:
        return ''
    return '%s %s%s' % (k['kind'], k['config'], '' if rec['state'] == 'finished' else ' (built, not finished)')


def get_scores(api, request, response):
    p = _params(request, response, 'scores')
    if p is None:
        return
    profs = _profiles(api, response, p.get('profile', ''))
    if profs is None:
        return
    built = _built(api, response, p)
    if built is None:
        return
    out = R.scores(built, profs, p.get('scope', 'both'), p.get('normalization') or None)
    first = profs[0]['name']
    single = len(profs) == 1
    recs = {r['id']: r for r in built['records']}
    res0 = out['profiles'][first]
    rows = []
    limit = p.get('limit', '')
    if limit and not (limit.isdigit() and int(limit) > 0):
        return _fail(response, falcon.HTTP_422, 'limit is a whole number above 0 (the N best ranked rows to keep)')
    for i in (res0['order'][:int(limit)] if limit else res0['order']):
        row = next(r for r in out['rows'] if r['id'] == i)
        s = res0['scores'][i]
        flat = {'rank': s['rank'], 'solution': row['solution'], 'label': row['short_label'], 'short_label': row['short_label'], 'long_label': row['label'], 'state': row['state'], 'state_why': row['state_why'], 'score': s['score'], 'raw': s['raw'],
                'confidence': s['confidence'], 'routes': row['routes'], 'hardware': row['hardware'], 'built_as': _built_as(recs[i]),
                'also_on': ', '.join(row['also_on']), 'scores': row['scores']}
        if single:
            flat['deciding_terms'] = deciding(s)
        rows.append(flat)
    for f in ([] if limit else built['failures']):
        rows.append({'rank': None, 'solution': f['solution'], 'label': f['short_label'], 'short_label': f['short_label'], 'long_label': f['routes'], 'state': 'failed', 'state_why': f['reason'], 'score': None, 'failed_purpose': f['purpose'], 'reason': f['reason'],
                     'routes': f['routes'], 'hardware': f['hardware'], 'scores': {}})
    response.media = {'ok': True, 'mission': built['mission'], 'scope': p.get('scope', 'both'), 'set': out['set_words'], 'profile': first if single else '',
                      'profiles': [{'name': x['name'], 'title': x['display_name'], 'mode': out['profiles'][x['name']]['mode'], 'notes': out['profiles'][x['name']]['notes']} for x in profs],
                      'counts': built['counts'], 'count': len(rows), 'rows': rows, 'failures': [dict(f) for f in built['failures']], 'suggestions': built['suggestions'],
                      'unmatched_configs': built['unmatched_configs'],
                      'note': 'Scores are competitive: per term the best compared solution gets 100 and the worst 0; then each profile column is normalized again (top 100, bottom 0). Failed solutions get no score.'}


def get_top(api, request, response):
    p = _params(request, response, 'top')
    if p is None:
        return
    profs = _profiles(api, response, '')
    built = _built(api, response, p)
    if built is None:
        return
    out = R.scores(built, profs, p.get('scope', 'both'), p.get('normalization') or None)
    byid = {r['id']: r for r in out['rows']}
    rows = []
    for x in profs:
        res = out['profiles'][x['name']]
        o = res['order']
        if not o:
            continue
        a = byid[o[0]]
        b = byid[o[1]] if len(o) > 1 else None
        rows.append({'profile': x['name'], 'profile_title': x['display_name'], 'top_solution': a['short_label'], 'top_routes': a['label'], 'top_state': a['state'], 'top_solution_name': a['solution'],
                     'score': res['scores'][o[0]]['score'], 'runner_up': b['short_label'] if b else '', 'runner_up_routes': b['label'] if b else '', 'runner_up_state': b['state'] if b else '',
                     'runner_up_score': res['scores'][o[1]]['score'] if b else None, 'compared_set': out['set_words'], 'failed_count': len(built['failures']),
                     'deciding_terms': deciding(res['scores'][o[0]])})
    response.media = {'ok': True, 'mission': built['mission'], 'scope': p.get('scope', 'both'), 'count': len(rows), 'rows': rows}


def _find(built, key):
    for r in built['records']:
        if key in (r['name'], r['id'], r['label']) or (r['link'] and key == r['link']['config'] and r['state'] == 'finished') or (r['link'] and key == r['link']['config']):
            return r
    for f in built['failures']:
        if key in (f['solution'], f['id']):
            return f
    return None


def get_breakdown(api, request, response):
    p = _params(request, response, 'breakdown')
    if p is None:
        return
    if not p.get('solution') or not p.get('profile'):
        return _fail(response, falcon.HTTP_422, 'breakdown needs ?solution= (a solution name, candidate id or built config) and ?profile= (one profile name)')
    profs = _profiles(api, response, p['profile'])
    if profs is None:
        return
    built = _built(api, response, p)
    if built is None:
        return
    hit = _find(built, p['solution'])
    if hit is None:
        return _fail(response, falcon.HTTP_404, 'no solution %r in %s (GET /api/firmware-scores lists them)' % (p['solution'], built['mission']))
    if hit.get('state') == 'failed':
        response.media = {'ok': True, 'mission': built['mission'], 'solution': hit['solution'], 'state': 'failed', 'profile': profs[0]['name'], 'score': None, 'rank': None,
                          'failed_purpose': hit['purpose'], 'reason': hit['reason'], 'terms': [], 'note': 'A failed solution never gets a score.'}
        return
    out = R.scores(built, profs[:1], p.get('scope', 'both'), p.get('normalization') or None)
    res = out['profiles'][profs[0]['name']]
    if hit['id'] not in res['scores']:
        return _fail(response, falcon.HTTP_404, 'solution %r is not in the compared set (%s)' % (p['solution'], out['set_words']))
    s = res['scores'][hit['id']]
    terms = [{k: r[k] for k in ('term', 'label', 'context', 'value', 'unit', 'kind', 'normalized', 'weight', 'weight_share', 'alpha', 'points', 'basis', 'normalization', 'fallback_for')} for r in s['rows']]
    response.media = {'ok': True, 'mission': built['mission'], 'solution': hit['name'], 'label': hit['label'], 'state': hit['state'], 'state_why': hit['state_why'], 'profile': profs[0]['name'],
                      'mode': res['mode'], 'score': s['score'], 'rank': s['rank'], 'raw_weighted': s['raw'], 'profile_normalization': s['profile_norm'], 'confidence': s['confidence'],
                      'set': out['set_words'], 'notes': res['notes'], 'groups': s['groups'], 'count': len(terms), 'terms': terms, 'rows': terms}


def post_values(api, request, response):
    body = _body(request)
    bad = sorted(k for k in body if k not in ('mission', 'limit', 'board'))
    if bad:
        return _fail(response, falcon.HTTP_422, 'unknown key(s) %s (known: mission, limit, board)' % ', '.join(bad))
    if api.manager is None:
        return _fail(response, falcon.HTTP_409, 'no live manager to write rows into')
    built = _built(api, response, {'mission': body.get('mission') or DEFAULT_MISSION, 'board': body.get('board', '')})
    if built is None:
        return
    counts = ST.write(api.manager, built, int(body.get('limit') or ST.DEFAULT_LIMIT))
    response.status = falcon.HTTP_201
    response.media = {'ok': True, 'mission': built['mission'], 'written': counts, 'finished': built['counts']['finished'], 'plans': counts.get('ScoreSubject', 0) - built['counts']['finished']}


def get_profiles(api, request, response):
    allp = P.all_profiles(api.manager)
    rows = [P.public(p) for p in allp.values()]
    for r in rows:   # fsc-3: plain-words columns for the page's profile table (the `terms` list stays for programs)
        r['weights_text'] = '; '.join('%s %g' % (t['term'], t['weight']) for t in r['terms'])
        r['edit_words'] = 'copy it first, then set weights on the copy' if r['seeded'] else 'yours: weights can be set in place'
    response.media = {'ok': True, 'count': len(rows), 'rows': rows, 'terms': list(T.TERM_NAMES), 'knobs': list(P.KNOWN_KNOBS),
                      'note': 'Seeded profiles are copied before they are edited: POST {name: <new>, copy_of: <seeded>, weights: {...}}.'}


def get_profile_terms(api, request, response, name):
    """GET /api/firmware-score-profiles/{name}/terms - the profile editor's table: one row per term {profile, term, label, plain, unit, group, purpose, weight, editable, seeded,
    in_profile}. Every known term is listed (weight 0 = not counted) so a weight can be given to a term the profile does not use yet; the profile's own weighted terms come first,
    heaviest first. A per-Purpose entry is listed read-only (`purpose` says which). A seeded profile's rows are `editable: false` (copy it first: POST copy_of)."""
    allp = P.all_profiles(api.manager)
    p = allp.get(name)
    if p is None:
        return _fail(response, falcon.HTTP_404, 'no profile %r (known: %s)' % (name, ', '.join(sorted(allp))))
    whole = {e['term']: e['weight'] for e in p['entries'] if not e.get('purpose')}
    rows = []
    for e in p['entries']:
        if e.get('purpose'):
            label, plain, unit, group = T.TERM_INFO.get(e['term'], (e['term'], '', '', ''))
            rows.append({'profile': name, 'term': e['term'], 'label': label, 'plain': plain, 'unit': unit, 'group': group, 'purpose': e['purpose'], 'weight': e['weight'],
                         'editable': False, 'seeded': p['seeded'], 'in_profile': True})
    for t in T.TERM_NAMES:
        label, plain, unit, group = T.TERM_INFO[t]
        rows.append({'profile': name, 'term': t, 'label': label, 'plain': plain, 'unit': unit, 'group': group, 'purpose': '', 'weight': whole.get(t, 0), 'editable': not p['seeded'],
                     'seeded': p['seeded'], 'in_profile': t in whole})
    rows.sort(key=lambda r: (not r['in_profile'], -r['weight'], r['term']))
    response.media = {'ok': True, 'profile': name, 'display_name': p['display_name'], 'seeded': p['seeded'], 'count': len(rows), 'rows': rows,
                      'note': ('Seeded: copy it first (POST /api/firmware-score-profiles {name, copy_of}).' if p['seeded'] else 'Yours: POST /api/firmware-score-profiles {name, weights: {term: w}} sets a weight (0 removes the term).')}


def _known_purposes(manager):
    from cmod.cmod_seed import CAPABILITY_ROWS
    names = {r['name'] for r in CAPABILITY_ROWS}
    names |= {getattr(o, 'name', '') for o in ((getattr(manager, 'objectTables', None) or {}).get('CapabilityDefinition') or {}).values()}
    return names


def post_profile(api, request, response):
    body = _body(request)
    errs = P.validate_body(body, _known_purposes(api.manager))
    name = body.get('name')
    if not isinstance(name, str) or not NAME_RE.match(name):
        errs.append('name is required: lowercase letters, digits and dashes (2-63 characters)')
    if errs:
        return _fail(response, falcon.HTTP_422, '; '.join(errs))
    allp = P.all_profiles(api.manager)
    existing = allp.get(name)
    if existing is not None and existing['seeded']:
        return _fail(response, falcon.HTTP_409, 'profile %r is seeded and is never edited in place: copy it with {"name": "<your name>", "copy_of": "%s", "weights": {...}}' % (name, name))
    if body.get('copy_of') and body['copy_of'] not in allp:
        return _fail(response, falcon.HTTP_422, 'no profile %r to copy (known: %s)' % (body['copy_of'], ', '.join(sorted(allp))))
    base = existing or (allp[body['copy_of']] if body.get('copy_of') else {'name': name, 'display_name': name, 'description': '', 'entries': [], 'knobs': {'normalization': 'competitive', 'accept_used': True, 'accept_local': True}})
    if existing is None and body.get('copy_of'):
        base = dict(base, entries=[dict(e) for e in base['entries']], knobs=dict(base['knobs']))
    entries, knobs = P.apply_body(base, body)
    if not entries:
        return _fail(response, falcon.HTTP_422, 'a profile needs at least one term with a weight above 0 (known terms: %s)' % ', '.join(T.TERM_NAMES))
    display = body.get('display_name', '')
    if existing is None and body.get('copy_of') and not display:
        # a copy that the person did not name is "My <title>" - never a second "Fastest" next to the seeded one
        title = base['display_name']
        display = title if title.startswith('My ') else 'My %s' % title
    row = P.save(api.manager, name, base, entries, knobs, display, body.get('description', ''))
    R.clear_scores(name)      # the profile's sha changed, so no stale result can be served; this frees the old ones
    created = existing is None
    response.status = falcon.HTTP_201 if created else falcon.HTTP_200
    parsed = P.parse(row if not isinstance(row, dict) else row)
    response.media = dict(P.public(parsed), ok=True, created=created)
