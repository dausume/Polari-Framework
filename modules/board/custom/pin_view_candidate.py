"""
@module board.custom.pin_view_candidate

pv-5 (PIN_VIEW_PLAN.md 2.9, MISSION_PROFILE_SOLVER_PLAN.md 8.4-8.5): the pin view's CANDIDATE stage - it DRAWS a solution the attempt engine found (sol-0). The view only READS: the search itself is a POST
(`/api/missions/{name}/solve`) the view never makes; this stage reads the stored `SolveRun` rows.

    GET /api/board/{board}/pin-view?stage=candidate[&run=<SolveRun name>][&candidate=<rank | id>][&mission=<Mission>]

  run        a SolveRun name (GET /api/missions/{mission}/solve-runs lists them); default = the LATEST run whose hardware is this board (404 with the reason, and the command that makes one, when there is none)
  candidate  a rank (1 = the best) or a candidate id from the run's list; default = the run's chosen candidate
  The chosen candidate is read from the run as recorded. Another candidate is read by replaying the run (same recorded inputs); when the replay no longer gives the recorded result sha256
  (the rules changed since), that candidate cannot be drawn and the door says so (409-style refusal, 404 here) rather than draw a plan the run did not make.

Every pin the candidate assigns shows stage `proposed`, with a task consumer {who = the profile's role, route, why = the run's reason for THIS pin} and the Purposes it serves; the pins it leaves free keep their base stage.
The response carries a `candidate` block: the run, the score summary (resources, cycle - both objectives), tier, variants, the assignment (profile -> pin, function, route, reason), risks, what is unchecked,
what lost (pins refused by name at their rung, Purposes that lost their pins, the part the bench lacks, the runner-ups with their deciding differences), the list of candidates to pick from and the link to "Solutions found".
"""
import json

SOLUTIONS_PAGE = '/display/solutions-found'
PICK_LIMIT = 40
MODE = {'digital-in': 'in', 'interrupt-in': 'in', 'pin-change-in': 'in', 'digital-out': 'out'}


class CandidateRefused(ValueError):
    def __init__(self, msg, status=404):
        super().__init__(msg)
        self.status = status


def _runs(manager):
    return list(((getattr(manager, 'objectTables', None) or {}).get('SolveRun') or {}).values())


def _j(row, key, default):
    try:
        return json.loads(getattr(row, key, '') or 'null') or default
    except ValueError:
        return default


def _board_of(row):
    ch = _j(row, 'chosen_json', {})
    b = (ch.get('hardware') or {}).get('board')
    if b:
        return [b]
    return _j(row, 'boards_json', [])


def pick_run(manager, board, name='', mission=''):
    """-> the SolveRun row asked for, or the latest one whose hardware is `board` (optionally of one Mission)."""
    runs = _runs(manager)
    if name:
        row = next((r for r in runs if r.name == name), None)
        if row is None:
            raise CandidateRefused('no solution search %r (GET /api/missions/{mission}/solve-runs lists the stored ones: %s)' % (name, ', '.join(sorted(r.name for r in runs)[:8]) or 'none stored yet'))
        return row
    mine = [r for r in runs if (not mission or r.mission == mission) and (board in _board_of(r))]
    if not mine:
        raise CandidateRefused('no solution search has been stored for board %s%s: run one with POST /api/missions/{mission}/solve or `pol capability solve mission <name>` (the view only reads stored runs)' % (
            board, (' and Mission %s' % mission) if mission else ''))
    return sorted(mine, key=lambda r: (r.ran_at, r.name))[-1]


def _replay(row, manager):
    from cmod.custom import solve_doors as D
    res = D.compute(row.mission, _j(row, 'boards_json', []) or None, _j(row, 'tiers_json', []) or None, row.objective, _j(row, 'limits_json', {}), manager)
    return res if res['result_sha256'] == row.result_sha256 else None


def pick_candidate(row, which, manager):
    """-> (candidate dict, full result or None, note). The chosen one comes from the record; another is replayed."""
    summ = _j(row, 'candidates_json', [])
    chosen = _j(row, 'chosen_json', {})
    if not summ and not chosen:
        raise CandidateRefused('run %s found no candidate (see its pruned log in the Solutions found page)' % row.name)
    sel = None
    if which:
        sel = next((s for s in summ if s['id'] == which), None) or (next((s for s in summ if str(s['rank']) == which), None) if which.isdigit() else None)
        if sel is None:
            raise CandidateRefused('run %s has no candidate %r (rank 1..%d, or an id such as %s)' % (row.name, which, len(summ), summ[0]['id'] if summ else row.chosen))
    is_chosen = sel is None or sel['id'] == row.chosen
    try:
        full = _replay(row, manager)
    except Exception as e:   # noqa: BLE001 - a failing replay says so; the recorded chosen candidate still draws
        full, why = None, 'the run could not be searched again (%s: %s)' % (type(e).__name__, e)
    else:
        why = 'the run, searched again from its recorded inputs, no longer gives the recorded result (the rules changed since %s)' % row.ran_at
    if is_chosen:
        return chosen, full, '' if full is not None else ('shown as recorded; ' + why + ': the runner-ups below are those of the record only')
    if full is None:
        raise CandidateRefused('candidate %s of run %s cannot be drawn: %s' % (which, row.name, why), 409)
    cand = next((c for c in full['_ranked'] if c['id'] == sel['id']), None)
    if cand is None:
        raise CandidateRefused('candidate %s of run %s is not in the search again' % (which, row.name), 409)
    return cand, full, ''


def _pads(model, pin, soc):
    return [p for p in model.pins.values() if p['level'] == 'die' and p['canonical'] == pin and (not soc or p.get('soc') == soc)]


def _line(model, pad_ids):
    from board.custom import pin_view_state as ST
    return ST._outward(model, pad_ids)


def mark(model, cand, row):
    """Pushes the candidate's assignment onto the model as `proposed`. -> (marked pins [{pin, pad}], unmatched [pin names])."""
    from board.custom import pin_view_state as ST
    soc = (cand.get('hardware') or {}).get('soc', '')
    marked, unmatched = [], []
    for a in cand.get('assignment', []):
        pads = _pads(model, a['pin'], soc)
        if not pads:
            unmatched.append(a['pin'])
            continue
        pad = pads[0]['id']
        fn = '' if a['function'] == 'GPIO' else a['function']
        why = 'proposed by candidate %s of run %s: %s - %s' % (cand['id'], row.name, a['role'], a['why'])
        cons = [{'kind': 'task', 'who': a['role'], 'solution': 'solution search %s' % row.name, 'claim': 'candidate:%s' % a['need'], 'mode': MODE.get(a['kind'], '') if not fn else '', 'function': fn, 'pull': 'none',
                 'route': a['route'], 'why': a['why'], 'part': a['part']}]
        cons += [{'kind': 'purpose', 'who': p, 'task': a['role']} for p in a['purposes']]
        for ref in [pad] + _line(model, [pad])[pad]:
            ST._push(model, ref, 'proposed', why, cons)
        marked.append({'pin': a['pin'], 'pad': pad})
    return marked, unmatched


def _score(cand, row):
    ms = lambda us: ('%.1f ms' % (us / 1000.0)) if us >= 1000 else ('%.1f us' % us)   # noqa: E731
    return {'objective': row.objective, 'resources': round(cand['resource_score'], 3), 'cycle': ms(cand['cycle_us']), 'cycle_us': cand['cycle_us'], 'rank': cand.get('rank'), 'rank_class': cand['rank_class'],
            'text': 'Resources %.3f (lower is cheaper), cycle %s; ranked by %s first.' % (cand['resource_score'], ms(cand['cycle_us']), row.objective.replace('-', ' '))}


def _what_lost(cand, full, row):
    from cmod.custom import solve_report as R
    out = []
    seen = set()
    for a in cand.get('assignment', []):
        for r in a.get('refused', []):
            line = 'Pin %s was refused for %s at rung %s (%s): %s' % (r['pin'], a['role'], r['rung'], r['kind'], r['why'])
            if line not in seen:
                seen.add(line)
                out.append(line)
    for l in cand.get('lost', []):
        out.append('The %s lost its pins%s: %s' % (l['role'], (' (serves %s)' % ', '.join(l['purposes'])) if l.get('purposes') else '', l['why']))
    if cand.get('parts_missing'):
        out.append('Needs a part the bench does not have: %s.' % ', '.join(p['class'] for p in cand['parts_missing']))
    if full is not None:
        w = full['chosen_candidate']
        if w is not None and w['id'] != cand['id']:
            out.append('Why it ranks #%s, below the chosen plan: %s' % (cand.get('rank'), R.deciding(cand, w)))
        if w is None or w['id'] == cand['id']:   # the chosen plan: the runner-ups and what could not be placed, each with its deciding difference
            for r in [x for x in full['score_card'] if x['verdict'] != 'chosen'][:6]:
                out.append('%s%s: %s - %s' % (('#%s ' % r['rank']) if r['rank'] != '-' else '', r['verdict'], r['candidate'], r['deciding_difference']))
    return out[:40]


def _picks(row, board):
    return [{'rank': s['rank'], 'id': s['id'], 'text': '%s / %s: %s' % (s['hardware'], s['tier'], ', '.join('%s %s' % (n.split(':')[-1], p) for n, p in sorted(s['pins'].items()))) if s['pins'] else s['hardware'],
             'resources': round(s['resource_score'], 3), 'cycle_us': s['cycle_us'], 'placement': s['placement'], 'chosen': s['id'] == row.chosen}
            for s in _j(row, 'candidates_json', []) if (not s.get('hardware') or s['hardware'].split(' / ')[0] == board)][:PICK_LIMIT]


def block(model, tables, board, params, manager):
    """The whole stage: choose the run and candidate, mark the model, return (stage-info additions, the response's `candidate` block). Raises CandidateRefused."""
    row = pick_run(manager, board, params.get('run', ''), params.get('mission', ''))
    cand, full, note = pick_candidate(row, (params.get('candidate') or '').strip(), manager)
    from cmod.custom import solve_report as R
    hw = cand.get('hardware') or {}
    notes = [note] if note else []
    if hw.get('board') and hw['board'] != board:
        notes.append('this candidate is for hardware %s; the view shows %s, so nothing is marked' % (hw['board'], board))
        marked, unmatched = [], []
    else:
        marked, unmatched = mark(model, cand, row)
    if unmatched:
        notes.append('undetermined: the pins %s are not silicon pads of this board\'s chip (the package or board may differ)' % ', '.join(unmatched))
    assign = [{'need': a['need'], 'role': a['role'], 'part': a['part'], 'pin': a['pin'], 'function': a['function'], 'route': a['route'], 'importance': a['importance'], 'purposes': a['purposes'],
               'why': a['why']} for a in cand.get('assignment', [])]
    risks = [r['text'] for r in cand.get('risks', [])]
    return {
        'run': row.name, 'mission': row.mission, 'objective': row.objective, 'ran_at': row.ran_at, 'result_sha256': row.result_sha256, 'id': cand['id'], 'rank': cand.get('rank'), 'chosen': cand['id'] == row.chosen,
        'hardware': R.short_hw(cand), 'tier': cand['tier'], 'variants': cand['routes'], 'variants_text': ', '.join('%s via %s' % (j.replace('-', ' '), r) for j, r in sorted(cand['routes'].items())),
        'placement': cand.get('placement', ''), 'score': _score(cand, row), 'assignment': assign, 'risks': risks, 'unchecked': [t for t in risks if 'unchecked' in t or 'rung 9' in t or 'rung 10' in t],
        'what_lost': _what_lost(cand, full, row), 'pins_marked': [m['pin'] for m in marked], 'notes': notes, 'candidates': _picks(row, board),
        'links': {'solutions_found': SOLUTIONS_PAGE, 'runs': '/api/missions/%s/solve-runs' % row.mission},
        'note': 'Drawn from the stored run, not searched again by the view; a pin the candidate does not assign keeps its base stage.',
    }
