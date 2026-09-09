"""
@module printing_suite.custom.pipeline

The production pipeline (his automation, 2026-09-09): a ProductionRun
walks design → material → nesting → mold → slice → print → measure. Each
step is a function `(run, ctx) -> StepResult` that calls the REAL
machinery through adapters on `ctx` (so the selftest injects fakes and
the API injects the manager, the object store, the slicer container and
Moonraker) and refuses BY NAME when a dependency is absent. Every step's
result is cached as a RunStepRecord (rows + artifact bytes); `retry`
re-runs one step and invalidates the later ones; `reprint` reuses the
cached gcode. Nothing moves the printer without a cached, checksummed
artifact.

Adapters on ctx (all optional; a missing one is a refusal, never a guess):
  rows(class_name) -> list of rows          find_row(class_name, name) -> row | None
  save(row)                                 now() -> iso timestamp
  plan_nesting(part, target, feedstock) -> casting.plan_nesting result dict
  export_shape(shape_name, fmt='stl') -> bytes
  cache_put(key, data) -> store_key         cache_get(key) -> bytes
  slice_stl(stl_bytes, profile_dict, slicer_profile_dict) -> gcode bytes  (kirimoto CLI in the container)
  moonraker_upload(printer_url, filename, gcode_bytes, start=True) -> {'jobId': ...}
  printer_url(printer_name) -> 'http://<guest-ip>:7125' | ''
"""
import hashlib
import json

STEPS = ('design', 'material', 'nesting', 'mold', 'slice', 'print', 'measure')
PRINTABLE_FEEDSTOCKS = ('pla', 'wax', 'petg', 'abs')


def _res(ok, result_class='', result_ref='', error='', detail=None, data=None):
    return {'ok': ok, 'result_class': result_class, 'result_ref': result_ref, 'error': error,
            'detail': detail or {}, 'data': data}


def step_design(run, ctx):
    """The CAD object must exist (uploaded through /api/shapes/import)."""
    row = ctx['find_row']('ImportedCadObject', run['cad_object'])
    if row is None:
        return _res(False, error='no ImportedCadObject %r — upload the CAD file first (POST /api/shapes/import)' % run['cad_object'])
    shape = getattr(row, 'shape_name', '') or run['cad_object']
    return _res(True, 'ImportedCadObject', run['cad_object'], detail={'shape': shape, 'format': getattr(row, 'source_format', '')})


def step_material(run, ctx):
    """The target material must be a known row (materials_science Material or a casting target)."""
    for cls in ('Material', 'CastingMaterialThermalProfile', 'WaxFeedstockDefinition'):
        if ctx['find_row'](cls, run['target_material']) is not None:
            return _res(True, cls, run['target_material'])
    return _res(False, error='target material %r is not a Material / casting thermal profile / wax feedstock row — absent data is absent' % run['target_material'])


def step_nesting(run, ctx):
    """Run the mold nesting automation (casting.plan_nesting) for the part + target."""
    plan = ctx.get('plan_nesting')
    if plan is None:
        return _res(False, error='the casting module (plan_nesting) is not available on this instance')
    design = ctx['step_result'](run, 'design')
    part = (design or {}).get('detail', {}).get('shape') or run['cad_object']
    result = plan(part, run['target_material'], run.get('mold_feedstock') or None)
    if not result.get('ok'):
        return _res(False, error='nesting refused: %s' % (result.get('error') or result.get('verdict') or 'no reason given')[:200], detail=result)
    if result.get('blockers'):
        return _res(False, 'MoldNestingChain', result.get('plan', ''), error='nesting blocked: %s' % '; '.join(str(b) for b in result['blockers'])[:200], detail=result)
    return _res(True, 'MoldNestingChain', result.get('plan', ''), detail={k: result.get(k) for k in ('plan', 'verdict', 'chainKind', 'feedstock', 'steps')})


def step_mold(run, ctx):
    """Pick the OUTERMOST printable mold of the chain — the first stage whose mold is the printable feedstock — and cache its STL."""
    nesting = ctx['step_result'](run, 'nesting')
    chain = (nesting or {}).get('result_ref', '')
    stages = sorted([s for s in ctx['rows']('CastingStageDefinition') if getattr(s, 'chain_ref', '') == chain], key=lambda s: getattr(s, 'sequence', 0))
    if not stages:
        return _res(False, error='chain %r has no CastingStageDefinition rows' % chain)
    want = (run.get('mold_feedstock') or 'pla').lower()
    printable = [s for s in stages if want in (getattr(s, 'mold_material_ref', '') or '').lower() or any(f in (getattr(s, 'mold_material_ref', '') or '').lower() for f in PRINTABLE_FEEDSTOCKS)]
    if not printable:
        return _res(False, error='no stage of chain %r has a printable mold material (%s); stages: %s' % (chain, ', '.join(PRINTABLE_FEEDSTOCKS), ', '.join(getattr(s, 'mold_material_ref', '?') for s in stages)))
    outer = printable[0]   # lowest sequence = outermost
    chain_row = ctx['find_row']('MoldNestingChain', chain)
    mold = ctx['find_row']('MoldDefinition', getattr(chain_row, 'mold_def_ref', '') if chain_row else '')
    shape = (getattr(mold, 'body_shape_name', '') or getattr(mold, 'stock_shape_name', '')) if mold else ''
    if not shape:
        return _res(False, 'CastingStageDefinition', outer.name, error='the chain\'s MoldDefinition names no body shape to print (derive the mold first)')
    export = ctx.get('export_shape')
    if export is None:
        return _res(False, 'CastingStageDefinition', outer.name, error='shape export (mathshapes) is not available — cannot produce the STL')
    stl = export(shape, 'stl')
    if not stl:
        return _res(False, 'CastingStageDefinition', outer.name, error='exporting shape %r as STL returned nothing' % shape)
    key = ctx['cache_put']('%s/mold/%s.stl' % (run['name'], shape), stl)
    return _res(True, 'CastingStageDefinition', outer.name, detail={'shape': shape, 'sequence': outer.sequence, 'moldMaterial': outer.mold_material_ref}, data=(key, stl))


def step_slice(run, ctx):
    """Slice the cached mold STL with the printer's profile in the Kiri:Moto container → cached gcode + SliceJob/GcodeArtifact rows."""
    mold = ctx['step_result'](run, 'mold')
    if not mold or not mold.get('ok'):
        return _res(False, error='no valid mold step to slice')
    stl = ctx['cache_get'](mold['store_key'])
    profile = ctx['find_row']('PrintProfile', run.get('profile') or '') or next((p for p in ctx['rows']('PrintProfile') if getattr(p, 'printer', '') == run['printer']), None)
    if profile is None:
        return _res(False, error='no PrintProfile for printer %r — derive one from the material rows first' % run['printer'])
    sprof = next((p for p in ctx['rows']('SlicerProfile') if getattr(p, 'printer', '') == run['printer']), None)
    slicer = ctx.get('slice_stl')
    if slicer is None:
        return _res(False, error='the kirimoto slicer container (polari/kirimoto image) is not available on this host')
    pd = {k: getattr(profile, k) for k in ('nozzle_mm', 'layer_mm', 'nozzle_temp_c', 'bed_temp_c', 'speed_mm_s', 'retraction_mm', 'fan_pct', 'infill_pct')}
    sd = {k: getattr(sprof, k) for k in ('bed_x_mm', 'bed_y_mm', 'bed_z_mm', 'nozzle_mm', 'gcode_flavor')} if sprof else {}
    gcode = slicer(stl, pd, sd)
    if not gcode:
        return _res(False, error='the slicer produced no gcode')
    key = ctx['cache_put']('%s/slice/%s.gcode' % (run['name'], mold['detail'].get('shape', 'mold')), gcode)
    return _res(True, 'GcodeArtifact', '%s:gcode' % run['name'], detail={'profile': profile.name, 'slicerProfile': getattr(sprof, 'name', ''), 'layers': gcode.count(b'\n;LAYER') or 0}, data=(key, gcode))


def step_print(run, ctx):
    """Upload the cached gcode to the printer guest's Moonraker and start it → PrintJob row."""
    sl = ctx['step_result'](run, 'slice')
    if not sl or not sl.get('ok'):
        return _res(False, error='no valid slice step to print (reprint reuses it; retry slice first)')
    url = (ctx.get('printer_url') or (lambda n: ''))(run['printer'])
    if not url:
        return _res(False, error='printer %r has no reachable Moonraker (no HardwareAppState ip for its guest — is the voron guest running?)' % run['printer'])
    upload = ctx.get('moonraker_upload')
    if upload is None:
        return _res(False, error='no Moonraker adapter on this instance')
    gcode = ctx['cache_get'](sl['store_key'])
    rep = upload(url, '%s.gcode' % run['name'], gcode, True)
    if not rep or not rep.get('ok', True):
        return _res(False, error='Moonraker upload failed: %s' % (rep or {}).get('error', 'no reply'))
    return _res(True, 'PrintJob', '%s:print' % run['name'], detail={'moonrakerJobId': rep.get('jobId', ''), 'printer': run['printer'], 'url': url})


def step_measure(run, ctx):
    """The outcome is measured by a person: this step only opens the PrintOutcome row (verdict unmeasured)."""
    return _res(True, 'PrintOutcome', '%s:outcome' % run['name'], detail={'verdict': 'unmeasured', 'note': 'measure the part and set the verdict; it feeds back into mold/material rows'})


RUNNERS = {'design': step_design, 'material': step_material, 'nesting': step_nesting, 'mold': step_mold,
           'slice': step_slice, 'print': step_print, 'measure': step_measure}


def next_step(run):
    i = STEPS.index(run['step']) if run['step'] in STEPS else 0
    return STEPS[i]


def advance(run, ctx):
    """Run the run's current step; returns (record_dict, run_updates)."""
    step = next_step(run)
    started = ctx['now']()
    attempts = [r for r in ctx['rows']('RunStepRecord') if getattr(r, 'run', '') == run['name'] and getattr(r, 'step', '') == step]
    res = RUNNERS[step](run, ctx)
    store_key = sha = ''
    size = 0
    if res.get('data'):
        store_key, blob = res['data']
        sha = hashlib.sha256(blob).hexdigest(); size = len(blob)
    rec = {'name': '%s:%s:%d' % (run['name'], step, len(attempts) + 1), 'run': run['name'], 'step': step, 'attempt': len(attempts) + 1,
           'ok': res['ok'], 'result_class': res['result_class'], 'result_ref': res['result_ref'], 'store_key': store_key, 'sha256': sha, 'bytes': size,
           'error': res['error'], 'detail_json': json.dumps(res['detail'], default=str)[:4000], 'started_at': started, 'finished_at': ctx['now'](), 'valid': True}
    if res['ok']:
        nxt = STEPS[STEPS.index(step) + 1] if step != STEPS[-1] else step
        upd = {'step': nxt, 'state': 'done' if step == STEPS[-1] else 'open', 'last_error': '', 'updated_at': rec['finished_at']}
    else:
        upd = {'step': step, 'state': 'blocked', 'last_error': res['error'][:400], 'updated_at': rec['finished_at']}
    return rec, upd


def retry(run, step, ctx):
    """Re-run one step: later steps' records are invalidated, the run's cursor moves back."""
    if step not in STEPS:
        return None, {'last_error': 'unknown step %r' % step}
    for r in ctx['rows']('RunStepRecord'):
        if getattr(r, 'run', '') == run['name'] and STEPS.index(getattr(r, 'step', 'design')) >= STEPS.index(step):
            r.valid = False; ctx['save'](r)
    run = dict(run, step=step, state='open')
    return advance(run, ctx)


def reprint(run, ctx):
    """Print the cached gcode again without re-slicing (the point of the cache)."""
    return advance(dict(run, step='print', state='open'), ctx)


def latest_valid(records, run_name, step):
    cands = [r for r in records if getattr(r, 'run', '') == run_name and getattr(r, 'step', '') == step and getattr(r, 'valid', True)]
    if not cands:
        return None
    r = max(cands, key=lambda r: getattr(r, 'attempt', 0))
    try:
        detail = json.loads(getattr(r, 'detail_json', '{}') or '{}')
    except ValueError:
        detail = {}
    return {'ok': r.ok, 'result_class': r.result_class, 'result_ref': r.result_ref, 'store_key': r.store_key, 'sha256': r.sha256, 'detail': detail}
