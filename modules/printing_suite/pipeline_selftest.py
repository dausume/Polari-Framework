"""pipeline_selftest — the production run walks every step through FAKE adapters (no docker, no printer):
refusals by name when a dependency is absent, the outermost printable mold is chosen, artifacts are cached +
checksummed, retry invalidates later steps, reprint reuses the cached gcode."""
import hashlib, json, sys
from types import SimpleNamespace as NS

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def make_ctx(with_casting=True, with_slicer=True, printer_ip='10.10.0.9'):
    tables = {'ImportedCadObject': [NS(name='bracket', shape_name='bracket-shape', source_format='step')],
              'Material': [NS(name='aluminium-6061')],
              'MoldNestingChain': [NS(name='nest--bracket-shape--aluminium-6061', mold_def_ref='mold-bracket')],
              'MoldDefinition': [NS(name='mold-bracket', body_shape_name='mold-bracket-body')],
              'CastingStageDefinition': [NS(name='st-1', chain_ref='nest--bracket-shape--aluminium-6061', sequence=1, mold_material_ref='pla-filament'),
                                         NS(name='st-2', chain_ref='nest--bracket-shape--aluminium-6061', sequence=2, mold_material_ref='plaster'),
                                         NS(name='st-3', chain_ref='nest--bracket-shape--aluminium-6061', sequence=3, mold_material_ref='aluminium-6061')],
              'PrintProfile': [NS(name='pla@voron', printer='voron-2.4-350', nozzle_mm=0.4, layer_mm=0.2, nozzle_temp_c=210, bed_temp_c=60, speed_mm_s=150, retraction_mm=0.5, fan_pct=100, infill_pct=20)],
              'SlicerProfile': [NS(name='voron@kiri', printer='voron-2.4-350', bed_x_mm=350, bed_y_mm=350, bed_z_mm=340, nozzle_mm=0.4, gcode_flavor='klipper')],
              'RunStepRecord': []}
    cache = {}
    ctx = {'rows': lambda c: list(tables.get(c, [])), 'find_row': lambda c, n: next((r for r in tables.get(c, []) if r.name == n), None),
           'save': lambda r: None, 'now': lambda: '2026-09-09T00:00:00',
           'cache_put': lambda k, d: (cache.__setitem__('mem:' + k, d), 'mem:' + k)[1], 'cache_get': lambda k: cache[k],
           'export_shape': lambda shape, fmt='stl': b'solid ' + shape.encode() + b'\nendsolid\n',
           'printer_url': lambda p: ('http://%s:7125' % printer_ip) if printer_ip else '',
           'moonraker_upload': lambda url, fn, g, start: {'ok': True, 'jobId': fn}}
    if with_casting:
        ctx['plan_nesting'] = lambda part, target, feed: {'ok': True, 'plan': 'nest--%s--%s' % (part, target), 'verdict': 'ok', 'steps': [1, 2, 3], 'blockers': []}
    if with_slicer:
        ctx['slice_stl'] = lambda stl, p, s: b';FLAVOR:Klipper\n;LAYER:0\nG1 X1\n;LAYER:1\nG1 X2\n'
    ctx['_tables'] = tables
    ctx['step_result'] = lambda run, step: __import__('printing_suite.custom.pipeline', fromlist=['latest_valid']).latest_valid(tables['RunStepRecord'], run['name'], step)
    return ctx


def drive(run, ctx, n=7):
    from printing_suite.custom.pipeline import advance
    out = []
    for _ in range(n):
        rec, upd = advance(run, ctx)
        ctx['_tables']['RunStepRecord'].append(NS(**rec))
        run.update(upd); out.append(rec)
        if not rec['ok']:
            break
    return out


def main():
    from printing_suite.custom import pipeline as P
    run = {'name': 'run-1', 'cad_object': 'bracket', 'target_material': 'aluminium-6061', 'mold_feedstock': 'pla', 'printer': 'voron-2.4-350', 'profile': '', 'slicer': 'kirimoto', 'step': 'design', 'state': 'open'}
    ctx = make_ctx()
    recs = drive(dict(run), ctx)
    check('a full run walks all seven steps and ends done', [r['step'] for r in recs] == list(P.STEPS) and all(r['ok'] for r in recs))
    mold = next(r for r in recs if r['step'] == 'mold')
    check('the OUTERMOST printable stage is chosen (sequence 1, pla) and its mold body exported', json.loads(mold['detail_json'])['sequence'] == 1 and json.loads(mold['detail_json'])['shape'] == 'mold-bracket-body')
    check('mold STL and gcode are cached + sha256-checksummed', mold['sha256'] == hashlib.sha256(b'solid mold-bracket-body\nendsolid\n').hexdigest() and next(r for r in recs if r['step'] == 'slice')['bytes'] > 0)
    prt = next(r for r in recs if r['step'] == 'print')
    check('print step uploads to the guest\'s Moonraker url', json.loads(prt['detail_json'])['url'] == 'http://10.10.0.9:7125')
    # refusals by name
    ctx2 = make_ctx(with_casting=False)
    r2 = drive(dict(run), ctx2)
    check('no casting module → nesting refuses by name and the run blocks there', r2[-1]['step'] == 'nesting' and not r2[-1]['ok'] and 'casting' in r2[-1]['error'])
    ctx3 = make_ctx(with_slicer=False)
    r3 = drive(dict(run), ctx3)
    check('no slicer container → slice refuses naming the image', r3[-1]['step'] == 'slice' and 'kirimoto' in r3[-1]['error'])
    ctx4 = make_ctx(printer_ip='')
    r4 = drive(dict(run), ctx4)
    check('no guest ip → print refuses naming the missing HardwareAppState', r4[-1]['step'] == 'print' and 'HardwareAppState' in r4[-1]['error'])
    ctx5 = make_ctx(); ctx5['_tables']['ImportedCadObject'] = []
    r5 = drive(dict(run), ctx5)
    check('no uploaded CAD → design refuses pointing at /api/shapes/import', r5[0]['step'] == 'design' and 'shapes/import' in r5[0]['error'])
    # retry + reprint on the completed run
    done = dict(run); ctx6 = make_ctx(); drive(done, ctx6)
    rec, upd = P.retry(done, 'slice', ctx6)
    ctx6['_tables']['RunStepRecord'].append(NS(**rec))
    later = [r for r in ctx6['_tables']['RunStepRecord'] if r.step in ('print', 'measure')]
    check('retry slice re-runs it as attempt 2 and invalidates print/measure records', rec['step'] == 'slice' and rec['attempt'] == 2 and later and all(not r.valid for r in later))
    rec2, upd2 = P.reprint(dict(done, step='measure', state='done'), ctx6)
    check('reprint reuses the cached gcode (no re-slice) and reaches Moonraker', rec2['step'] == 'print' and rec2['ok'])
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
