"""
@module cmod.custom.fsc_sample

smp-0 (FIRMWARE_SCORE_PROFILES_PLAN.md section 13, his ruling 2026-10-19: "That seems like a bit too many plans and failures ... Maybe just 2 failure examples and success examples for different kinds of devices and
components so that this project which is just a sample project serves as a way to prove out how to use those components along with managing the state of LEDs"): THE CURATED SAMPLE.

The Mission row carries `sample_solutions`: a list of entries {id, config, kind success|failure, device, components, why, [safety_deadline], [twin_only]}. The scores doors default to SCOPE `sample`:
  - the sample SUCCESSES that are FINISHED (built, and every Purpose proven on their own build) compete (competitive: best 100, worst 0);
  - the failures listed are only the sample's FAILURE entries;
  - every other built config (uno-light-pcint, -analog, -v2, ... anything not in the sample) is kept as HISTORY: it is not listed as a failure and not scored in this scope (`scope=all` still has it);
  - an entry whose config is not built yet (the ESP32-C3 sample S5 until its build lands) is shown as "not built yet" - never as a failure.
`scope=all` is the old behaviour (every non-failed solution, every plan, every failure), `scope=plans` the plans nobody built, `scope=finished` every finished config (the sample or not).

A sample FAILURE may state a SAFETY DEADLINE of its own (`safety_deadline`: {purpose, key, safety_critical: true}). That is the D-fsc-1 rule ("a deadline flagged safety-critical that is missed is a failure")
applied to ONE sample entry, WITHOUT touching the real Mission or its Purposes: the deadline's VALUE is read from the Purpose's own criterion (ensure-button-controls-light: max_latency_ms 100 ms), the safety flag is
the entry's, and the time is MEASURED on the twin (board.custom.press_latency, a committed record). The failure row says "misses the safety-critical deadline: X ms against Y ms".
"""
import json

SCOPES = ('sample', 'all', 'plans', 'finished')
ALIASES = {'both': 'all', 'plan': 'plans'}      # the names the scope parameter had before smp-0
KINDS = ('success', 'failure')
NOT_BUILT = 'not built yet'


def norm_scope(scope):
    return ALIASES.get(scope, scope)


def entries(mission_row):
    """-> the validated sample entries of a Mission row (a dict), in order; [] when the Mission carries none or the JSON is not a list of entries."""
    raw = (mission_row or {}).get('sample_solutions')
    try:
        rows = json.loads(raw) if isinstance(raw, str) and raw else (raw or [])
    except ValueError:
        return []
    out = []
    for e in rows if isinstance(rows, list) else []:
        if isinstance(e, dict) and e.get('id') and e.get('config') and e.get('kind') in KINDS:
            out.append(dict(e))
    return out


def default_scope(sample):
    """`sample` for a Mission that carries a sample, else `all` (a person's own Mission has no curated set: it is not shown empty)."""
    return 'sample' if sample else 'all'


def configs_of(sample, kind=None):
    return {e['config']: e for e in sample if kind is None or e['kind'] == kind}


def skipped_configs(sample):
    """The configs a safety-deadline entry takes over: they are not matched to a plan (they have their own failure row)."""
    return {e['config'] for e in sample if e.get('safety_deadline')}


def safety_failures(sample, ctx, known_configs, routes_text=None):
    """-> (failure rows, notes). One row per failure entry with a `safety_deadline` whose measured press-to-light time is over the Purpose's deadline. `notes` = [{id, config, state, words}] for the entries that
    could not be judged (config not built yet, not measured yet, deadline not stated) or that meet it, so the sample table says why there is no failure row."""
    from board.custom import press_latency as PL
    rows, notes = [], []
    for e in sample:
        sd = e.get('safety_deadline')
        if not sd:
            continue
        cfg = e['config']
        if cfg not in known_configs:
            notes.append({'id': e['id'], 'config': cfg, 'state': NOT_BUILT, 'words': 'no firmware config named %s is built yet' % cfg})
            continue
        p = (ctx.get('by_name') or {}).get(sd.get('purpose'))
        dl = (p or {}).get('deadline_ms')
        if p is None or not dl:
            notes.append({'id': e['id'], 'config': cfg, 'state': 'undetermined', 'words': 'the Mission has no Purpose %r with a deadline, so the safety deadline of %s cannot be read' % (sd.get('purpose'), e['id'])})
            continue
        if sd.get('key') and sd['key'] != p.get('deadline_key'):
            notes.append({'id': e['id'], 'config': cfg, 'state': 'undetermined', 'words': 'the Purpose states its deadline as %s, not %s' % (p.get('deadline_key'), sd['key'])})
            continue
        rec = PL.load(cfg)
        if rec is None:
            notes.append({'id': e['id'], 'config': cfg, 'state': 'not measured yet',
                          'words': 'no press-to-light time is recorded for %s: python3 -m board.custom.press_latency measure %s --save (twin)' % (cfg, cfg)})
            continue
        worst, limit = float(rec['worst_ms']), float(dl['value'])
        why = ('%s misses the safety-critical deadline: %s ms against %s ms (Purpose %s, %s). Measured on the twin: the light followed the press after %s ms at worst over %d presses spread across one main-loop pass '
               '(best %s ms); record %s, build %s. The deadline is %s on the real Purpose and flagged safety-critical for this sample only.'
               % (cfg, ('%.1f' % worst).rstrip('0').rstrip('.'), ('%g' % limit), sd['purpose'], p.get('deadline_key'), ('%.1f' % worst).rstrip('0').rstrip('.'),
                  len(rec.get('runs') or []), ('%.1f' % float(rec['best_ms'])).rstrip('0').rstrip('.'), rec['record_sha256'][:12], rec['inputs']['hex_sha256'][:12],
                  'stated but not flagged' if not p.get('safety_critical') else 'already flagged'))
        if sd.get('safety_critical') and worst > limit:
            rows.append({'kind': 'safety-deadline', 'purpose': sd['purpose'], 'reason': why, 'id': 'config:%s' % cfg, 'solution': cfg, 'config': cfg,
                         'routes': (routes_text or {}).get(cfg, ''), 'hardware': 'arduino-uno-r3', 'rank': None, 'state': 'failed', 'sample': e['id'],
                         'measured_ms': worst, 'deadline_ms': limit, 'short_label': '%s (built firmware)' % cfg})
        else:
            notes.append({'id': e['id'], 'config': cfg, 'state': 'meets its deadline', 'words': '%s follows a press in %s ms at worst against %s ms: not a failure' % (cfg, worst, limit)})
    return rows, notes


def tag(sample, records, failures):
    """Mark the records and failure rows that ARE sample entries with the entry's id (`sample`)."""
    ok = configs_of(sample, 'success')
    bad = configs_of(sample, 'failure')
    for r in records:
        c = (r.get('link') or {}).get('config')
        if c in ok:
            r['sample'] = ok[c]['id']
    for f in failures:
        if f.get('config') in bad:
            f['sample'] = bad[f['config']]['id']


def in_scope_failures(built, scope):
    scope = norm_scope(scope)
    return [f for f in built['failures'] if f.get('sample')] if scope == 'sample' else list(built['failures'])


def history(built, scope):
    """The built configs of THIS Mission that the scope leaves out, as plain rows {config, state, words}: in the sample scope, every config that matches a plan or fails a Purpose of the Mission but is not a sample entry
    (uno-light-pcint, -analog, -v2, uno-light-sense-pcint, uno-button-clock ...). They are kept as HISTORY: not scored and not listed as failures in this scope. Configs built for another job (uno-sim-rig, uno-echo ...) are
    not candidates for the Mission at all and stay in `unmatched_configs`. Empty in the other scopes."""
    if norm_scope(scope) != 'sample':
        return []
    out = []
    for r in built['records']:
        c = (r.get('link') or {}).get('config')
        if c and not r.get('sample'):
            out.append({'config': c, 'state': r['state'], 'words': 'built, %s; not in the sample, so not scored here (scope=all lists it)' % ('finished' if r['state'] == 'finished' else 'not finished')})
    for f in built['failures']:
        if not f.get('sample') and f.get('config'):
            out.append({'config': f['config'], 'state': 'failed (history)', 'words': 'built but not in the sample: kept as history, not listed as a failure here (scope=all lists it). %s' % f['reason']})
    return sorted(out, key=lambda x: x['config'])


def sample_rows(built, sample):
    """-> the sample table: one row per entry {id, kind, device, config, components, why, state, outcome} with the entry's state read off the built set - never invented."""
    recs = {(r.get('link') or {}).get('config'): r for r in built['records'] if r.get('link')}
    fails = {f.get('config'): f for f in built['failures'] if f.get('config')}
    notes = {n['id']: n for n in built.get('sample_notes') or []}
    out = []
    for e in sample:
        cfg = e['config']
        row = {'id': e['id'], 'kind': e['kind'], 'device': e.get('device', ''), 'config': cfg, 'components': e.get('components', ''), 'why': e.get('why', ''), 'twin_only': bool(e.get('twin_only'))}
        if cfg not in built.get('known_configs', ()):
            row.update(state=NOT_BUILT, outcome='not built yet: no firmware config named %s exists yet (it is not a failure, and it joins the sample when it is built and proven)' % cfg)
        elif e['kind'] == 'failure':
            f = fails.get(cfg)
            if f is not None:
                row.update(state='failed', outcome=f['reason'])
            elif e['id'] in notes:
                row.update(state=notes[e['id']]['state'], outcome=notes[e['id']]['words'])
            else:
                row.update(state='not a failure now', outcome='%s no longer fails a Purpose or a safety-critical deadline' % cfg)
        else:
            r = recs.get(cfg)
            if r is None:
                why = next((u['why'] for u in built.get('unmatched_configs') or [] if u['config'] == cfg), 'it is not matched to a plan of this Mission')
                row.update(state='built, not scored', outcome=why)
            elif r['state'] == 'finished':
                row.update(state='finished', outcome=r['state_why'])
            else:
                row.update(state='built, not finished', outcome=r['state_why'])
        out.append(row)
    return out
