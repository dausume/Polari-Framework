"""
@module cmod.custom.approach_profile_tiers

rt-0 (MISSION_PROFILE_SOLVER_PLAN.md section 8.2): each runtime tier CHECKED against one board. REUSES iso-0's tier eligibility
(`isotope_variants_eligibility.check_runtime` - the board's RuntimeProfile rows and `level_ok`) and its per-variant `eligible`; nothing is re-decided here.

Per tier the answer is one of
  available      the board's RuntimeProfile row supports the tier and nothing measured or cited says the Mission does not fit
  blocked        the board's row refuses the tier (its refusal, by name and citation), or a measured figure does not fit
  undetermined   the row cannot be read, or a small board has no figure for the tier's kernel
with the memory budget, what is measured and what is not, how many isotope variants of each job stay eligible, and what choosing the tier would cost.

Memory rules: bare-c is checked with the recorded build (flash = .text + .data, static RAM = .data + .bss; the stack is not sized - the RuntimeProfile row
says so) against the board's cited limits. A kernel's footprint is NEVER guessed: it is a measured/cited figure or it is undetermined, and a board of the
S class (BoardDefinition.device_class MCU-S) is not called available on an undetermined kernel figure.
"""
import json

from cmod.custom import approach_profile_atoms as A
from cmod.custom.approach_profile_atoms import q, undetermined
from cmod.custom.code_interface import LEVEL_ORDER

TIERS = ('bare-c', 'freertos', 'zephyr')
_LABEL = {'bare-c': 'bare C (a main loop and interrupts)', 'freertos': 'FreeRTOS (preemptive tasks)', 'zephyr': 'Zephyr (drivers, devicetree, threads)'}


def label(tier):
    return _LABEL.get(tier, tier)


def _limits(board, ctx):
    """-> {flash: q, sram: q} the board's own capacity, each cited."""
    soc = ctx['soc_row']
    mm = json.loads(soc.get('memory_map_json') or '[]')
    sram = sum(r['size'] for r in mm if str(r.get('region', '')).startswith(('sram', 'dram')))
    out = {}
    if board == 'arduino-uno-r3':
        from board.custom import uno_facts as UF
        f = {x['fact_key']: x for x in UF.SEED_UNO_FACTS}
        out['flash'] = q('cited', int(f['upload.maximum_size']['value']), 'bytes', 'ArduinoCore-avr boards.txt upload.maximum_size = 32768 minus the 512-byte Optiboot bootloader (%s)' % f['upload.maximum_size']['url'])
        out['sram'] = q('cited', int(f['upload.maximum_data_size']['value']), 'bytes', 'ArduinoCore-avr boards.txt upload.maximum_data_size (%s)' % f['upload.maximum_data_size']['url'])
        return out
    fl = next((r for r in mm if r.get('region') == 'flash'), None)
    if fl:
        out['flash'] = q('cited', fl['size'], 'bytes', 'SocDefinition %s memory map (%s); a bootloader, if any, is not modelled' % (soc['name'], soc.get('source', '')))
    elif ctx['soc'] == 'esp32c3':
        from board.custom import build_c3
        out['flash'] = q('cited', build_c3.APP_PARTITION_BYTES, 'bytes', 'the C3 template\'s partitions.csv `factory` partition (build_c3.APP_PARTITION_BYTES); the module\'s flash chip size is not modelled')
    else:
        out['flash'] = undetermined('the %s has no flash region in its memory map' % soc['name'], 'bytes')
    out['sram'] = q('cited', sram, 'bytes', 'SocDefinition %s memory map: the sram regions summed (%s)' % (soc['name'], soc.get('source', ''))) if sram else undetermined('no sram region in the memory map', 'bytes')
    return out


def _app(spec, board):
    """The Mission's own measured footprint on this board, or None with why."""
    for p in spec['processors']:
        if p['board'] == board and p.get('build'):
            b = p['build']
            return {'flash': q('measured', b['flash_bytes'], 'bytes', '%s: .text %s + .data %s' % (b['basis'], b['size_text'], b['size_data'])),
                    'sram': q('measured', (b['size_data'] or 0) + (b['size_bss'] or 0), 'bytes', '%s: .data %s + .bss %s (the stack is not sized)' % (b['basis'], b['size_data'], b['size_bss'])),
                    'stack_floor': _stack_floor(p)}, ''
    other = [p['board'] for p in spec['processors'] if p.get('build')]
    why = ('the Mission\'s atoms are measured for %s, not %s: a build for another chip has a different size' % (', '.join(sorted(set(other))), board)) if other else 'no recorded build of this Mission'
    return None, why


def _stack_floor(proc):
    vals = [(t['stack_bytes'] or 0, t['name']) for t in proc['tasks']] + [(i['stack_bytes'] or 0, i['name']) for i in proc['isrs']]
    if not vals:
        return undetermined('no atom stack frame measured')
    v, name = max(vals)
    return q('measured', v, 'bytes', 'the largest single GCC .su stack frame among the firmware\'s atoms (%s); a LOWER BOUND for one task\'s stack, not a task stack size' % name)


def _kernel(tier, board, ctx, rt_row):
    """-> {flash: q, sram: q, note}: the tier's own footprint on this board - measured/cited or undetermined, never guessed."""
    what = {'bare-c': 'no kernel', 'freertos': 'FreeRTOS kernel + idle task + per-task control blocks and stacks', 'zephyr': 'Zephyr kernel + drivers + per-thread stacks'}[tier]
    if tier == 'bare-c':
        z = q('measured', 0, 'bytes', 'no kernel: one main loop and interrupts (RuntimeProfile %s)' % (rt_row or {}).get('name', ''))
        return {'flash': z, 'sram': z, 'note': what}
    why = 'no %s build for %s is recorded in the suite, and no footprint is cited for it (%s)' % (tier, board, what)
    out = {'flash': undetermined(why, 'bytes'), 'sram': undetermined(why, 'bytes'), 'note': what}
    if tier == 'zephyr' and rt_row and rt_row.get('heap_bytes'):
        out['heap'] = q('cited', int(rt_row['heap_bytes']), 'bytes', 'RuntimeProfile %s heap_bytes: %s' % (rt_row['name'], rt_row.get('origin', '')))
    return out


def variants_by_job(ctx, tier, manager=None):
    from cmod.custom import isotope_variants as IV
    from cmod.custom import isotope_variants_eligibility as E
    out = []
    for j in IV.jobs(manager):
        vs = IV.variants(manager, j['name'])
        st = [E.eligible(v, ctx, tier=tier)['state'] for v in vs]
        out.append({'job': j['name'], 'total': len(vs), 'ok': st.count('ok'), 'undetermined': st.count('undetermined'), 'blocked': st.count('blocked')})
    return out


def check_tier(tier, board, ctx, spec, recommended, manager=None):
    from cmod.custom import isotope_variants_eligibility as E
    rt = next((r for r in ctx['runtime'] if r['runtime'] == tier), None)
    sup = E.check_runtime({'minimum_level': tier}, ctx, tier=tier)
    lim = _limits(board, ctx)
    app, app_why = _app(spec, board)
    ker = _kernel(tier, board, ctx, rt)
    mem = []
    fit = 'ok'
    if app is not None:
        for key, nm in (('flash', 'flash'), ('sram', 'static RAM')):
            need = (app[key]['value'] or 0) + (ker[key]['value'] if ker[key]['value'] is not None else 0)
            lv = lim[key]['value']
            state = 'undetermined' if lv is None else ('blocked' if need > lv else 'ok')
            if ker[key]['value'] is None:
                state = 'undetermined' if state == 'ok' else state          # a blocked lower bound stays blocked
            mem.append({'what': nm, 'application': app[key], 'kernel': ker[key], 'limit': lim[key],
                        'free_after_application': q('measured' if app[key]['kind'] == 'measured' and lv is not None else 'undetermined',
                                                    (lv - app[key]['value']) if lv is not None else None, 'bytes',
                                                    '%s limit minus the application\'s measured %s (the kernel and stacks come off this)' % (nm, nm)),
                        'state': state})
        fit = 'blocked' if any(m['state'] == 'blocked' for m in mem) else ('undetermined' if any(m['state'] == 'undetermined' for m in mem) else 'ok')
    else:
        for key, nm in (('flash', 'flash'), ('sram', 'static RAM')):
            mem.append({'what': nm, 'application': undetermined(app_why, 'bytes'), 'kernel': ker[key], 'limit': lim[key], 'state': 'undetermined',
                        'free_after_application': undetermined(app_why, 'bytes')})
        fit = 'undetermined'
    dc = next((b.get('device_class', '') for b in _board_rows(board)), '')
    if sup['state'] == 'blocked':
        state, why = 'blocked', sup['why']
    elif sup['state'] == 'undetermined':
        state, why = 'undetermined', sup['why']
    elif fit == 'blocked':
        state, why = 'blocked', 'the application plus the %s does not fit: %s' % (tier, '; '.join('%s %s' % (m['what'], m['state']) for m in mem if m['state'] == 'blocked'))
    elif tier != 'bare-c' and ker['sram']['value'] is None and dc == 'MCU-S':
        state, why = 'undetermined', 'a small (S class) board with no measured or cited %s footprint: it is not called available on a guess' % tier
    else:
        state = 'available'
        why = sup['why'] + ('' if fit == 'ok' else '; memory fit: %s - %s' % (fit, app_why or 'the kernel footprint is not measured or cited'))
    return {'tier': tier, 'label': label(tier), 'state': state, 'why': why, 'recommended': tier == recommended, 'support': sup, 'memory': mem, 'fit': fit,
            'kernel': ker, 'variants': variants_by_job(ctx, tier, manager), 'runtime_row': (rt or {}).get('name', ''),
            'twin': (rt or {}).get('twin', ''), 'built_template': bool(rt and (rt.get('twin') or 'template' in (rt.get('origin') or '')))}


def _board_rows(board):
    from board.custom import board_object as BO
    return [b for b in BO.seed_tables()['BoardDefinition'] if b['name'] == board]


def cost_of_choosing(tier, rep, recommended, superloop_failed, spec, reps, board=''):
    """Plain words + numbers for choosing `tier`: against the recommended tier. A person may pick it; nothing is forced."""
    i, r = LEVEL_ORDER.index(tier), LEVEL_ORDER.index(recommended)
    base = reps[recommended] if recommended in reps else None
    ok_now = sum(v['ok'] for v in rep['variants'])
    ok_rec = sum(v['ok'] for v in base['variants']) if base else None
    parts = []
    if tier == recommended:
        parts.append('the recommended tier: the smallest runtime whose argument holds for this Mission')
    elif i < r:
        parts.append('the deadline argument does not hold at this tier: %s' % (superloop_failed or 'see the recommendation'))
    else:
        k = rep['kernel']
        fl, rm = k['flash'], k['sram']
        parts.append('kernel and stacks: flash %s, RAM %s%s' % (A.text(fl), A.text(rm), '' if fl['value'] is not None else ' - ' + fl['basis']))
        mine = [p for p in spec['processors'] if p['board'] == board]
        fl2 = _stack_floor(mine[0]) if mine else None
        if fl2 and fl2['value'] is not None:
            parts.append('each task needs its own stack, at least %s' % A.text(fl2))
        else:
            parts.append('each task needs its own stack, whose size is undetermined (the atoms\' stack frames are measured for another chip)')
        parts.append('more machinery to learn and debug than %s' % label(recommended))
    if base is not None and tier != recommended:
        parts.append('isotope variants eligible across all jobs: %d here against %d at %s' % (ok_now, ok_rec, recommended))
    return {'text': '; '.join(parts), 'variants_ok': q('measured', ok_now, 'variants', 'counted from iso-0 eligibility at this tier on this board')}
