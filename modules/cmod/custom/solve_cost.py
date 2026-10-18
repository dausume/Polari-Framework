"""
@module cmod.custom.solve_cost

sol-0: the two COST MODELS of the Mission's objective (MISSION_PROFILE_SOLVER_PLAN.md section 5), both over the variants a candidate chose. Every number is a quantity
{kind: measured | estimated | cited | undetermined, value, unit, basis}; an UNDETERMINED cost is NEVER scored as zero - it is scored at a STATED stand-in (a penalty) and the
candidate shows how many it carries.

MINIMUM-RESOURCES  a weighted sum of FRACTIONS OF WHAT THE HARDWARE HAS:  pins used / header pins · on-chip blocks claimed / block kinds · parts to acquire (each counts a whole
                   unit: a part the bench lacks) · parts used / 10 · flash / the chip's cited limit · RAM / the chip's cited limit · CPU class / 4. Defaults in DEFAULT_WEIGHTS;
                   they are KNOBS (limits['weights']), not rulings. Flash and RAM come from iso-0's costs (measured from the atoms where they exist, else its labelled estimates)
                   plus the runtime tier's own kernel footprint (rt-0: measured, cited, or undetermined -> stand-in 25% of the limit).
FASTEST-CYCLE      the estimated MISSION CYCLE TIME in microseconds, by his definitions: a Purpose cycle = every task relevant to that one Purpose once (from its trigger to the last
                   one done: a POLLED trigger waits up to one pass of the main loop - rt-0's bound), the Mission cycle = one pass through every Purpose. Per task: the atoms'
                   cyc-0 MEASURED cycles (a recorded simavr twin run, board.custom.cycle_records) where a cycle record has the route's atoms, else rt-0 cycle UPPER BOUNDS
                   where the route has atoms; counted instructions / the bus rate for a route that has none (labelled). Every candidate says which basis each part used. The unchanged tasks of the firmware
                   (apply, telemetry ...) add the same to every candidate; they are included so the number is a cycle, not a delta, and their unbounded parts are said.
The other objective is always computed too and shown as the secondary column.
"""
from cmod.custom import isotope_variants as IV
from cmod.custom import pin_profiles as PP
from cmod.custom import solve_inputs as SI

DEFAULT_WEIGHTS = {'pins': 3.0, 'peripherals': 2.0, 'parts_to_acquire': 3.0, 'parts_used': 0.5, 'flash': 1.0, 'ram': 1.0, 'cpu': 1.0}
WEIGHT_WORDS = {'pins': 'pins used', 'peripherals': 'on-chip blocks claimed', 'parts_to_acquire': 'parts to get (not on the bench)', 'parts_used': 'part classes used',
                'flash': 'flash bytes', 'ram': 'RAM bytes', 'cpu': 'CPU load class'}
KERNEL_STANDIN = 0.25           # fraction of the chip limit scored for an undetermined kernel footprint
CPU_STANDIN = 0.5               # fraction of the 4-step CPU class scored for a route with no class
#: ordinal CPU class read off iso-0's own cpu_share words per route (0 = the hardware does the work, 4 = busy for a bit-timed exchange)
CPU_CLASS = {'ext-interrupt': 0, 'analog-comparator': 0, 'gpio-out': 0, 'pwm': 0, 'transistor-switch': 0, 'pin-change-interrupt': 1, 'gpio-poll': 1, 'uart-rx-interrupt': 1,
             'analog-threshold': 2, 'analog-read': 2, 'analog-sensor': 2, 'uart-tx': 2, 'spi-shift-register': 3, 'i2c-expander': 3, 'i2c-sensor': 3, 'spi-sensor': 3, 'one-wire': 4}
#: the structural timing of a route that has no atoms: (mode of the TRIGGER side, work cycles, init cycles, undetermined parts, how counted)
_DS = 'ATmega328P datasheet DS40002061B (exact page not reconfirmed)'
ROUTE_CYCLES = {
    'gpio-poll': ('polled', 5, 12, [], 'IN + SBIS/SBIC + branch is about 5 cycles (AVR instruction set); init = DDR/PORT writes about 12'),
    'ext-interrupt': ('event', 38, 12, [], 'ISR entry 4 + RETI 4 + register save/restore about 10 + a short body about 20; init = EICRA/EIMSK about 12'),
    'pin-change-interrupt': ('event', 50, 16, [], 'as the external interrupt, plus reading the port, comparing with the saved copy and finding which pin moved, about 12 more'),
    'analog-comparator': ('event', 38, 16, ['the comparator propagation delay was not read'], 'ISR entry/exit and a short body as the external interrupt; init = ACSR/DIDR1 about 16'),
    'analog-threshold': ('polled', None, 20, [], 'one ADC conversion: 13 ADC clocks at the system clock / 128 (the Arduino default prescaler - the project\'s own ADCSRA setting was not read), plus about 20 cycles to start, read and compare (%s, conversion time)' % _DS),
    'analog-read': ('polled', None, 20, [], 'as analog-threshold'),
    'analog-sensor': ('polled', None, 20, [], 'as analog-threshold'),
    'spi-shift-register': ('polled', 46, 24, [], 'a load pulse about 4 cycles + one SPI byte: 8 bits x 4 cycles at fosc/4 = 32 + about 10 to start and read; init = SPCR/DDR about 24'),
    'i2c-expander': ('polled', 'bus', 40, [], 'one two-byte bus transaction at the standard 100 kHz (START + address + data + STOP, about 20 bit times = 200 us); the project\'s TWBR was not read'),
    'i2c-sensor': ('polled', 'bus', 40, ['the sensor\'s own conversion time was not read'], 'as i2c-expander'),
    'spi-sensor': ('polled', 46, 24, ['the converter\'s own conversion time was not read'], 'as spi-shift-register'),
    'one-wire': ('polled', None, 12, ['the whole bit-timed exchange and the sensor\'s conversion time were not derived'], 'bit-timed in software; not derived here'),
    'gpio-out': ('immediate', 2, 12, [], 'one OUT/SBI/CBI is 2 cycles; init = DDR write about 12'),
    'pwm': ('immediate', 2, 40, ['the PWM period (how long a new duty takes to show) was not measured'], 'one OCRnx write is 2 cycles; init = TCCRn/OCRn about 40'),
    'transistor-switch': ('immediate', 2, 12, ['the transistor\'s switching time was not read'], 'the same C as gpio-out'),
    'uart-tx': ('immediate', None, 0, [], 'rt-0'), 'uart-rx-interrupt': ('event', None, 0, [], 'rt-0'),
}


def q(kind, value, unit, basis):
    return {'kind': kind, 'value': value, 'unit': unit, 'basis': basis}


def _standin_catalogue():
    """Largest KNOWN flash / RAM over the whole variant catalogue - the stand-in for an undetermined size of a variant (stated, never zero)."""
    out = {'flash_bytes': 0, 'ram_bytes': 0}
    for v in IV.variants(None):
        c = IV.costs(v)
        for k in out:
            val = (c.get(k) or {}).get('value')
            if isinstance(val, (int, float)):
                out[k] = max(out[k], val)
    return {k: (v or 64) for k, v in out.items()}


_CACHE = {}


def standin():
    if 'standin' not in _CACHE:
        _CACHE['standin'] = _standin_catalogue()
    return _CACHE['standin']


def variant_costs(v):
    if v['name'] not in _CACHE:
        _CACHE[v['name']] = (IV.costs(v), IV.parts_of(v), IV.status(v)['status'])
    return _CACHE[v['name']]


def limits_of(tier_rep):
    out = {}
    for m in (tier_rep or {}).get('memory', []):
        out[m['what']] = (m.get('limit') or {}).get('value')
    return {'flash': out.get('flash') or 32256, 'ram': out.get('static RAM') or 2048,
            'basis': 'rt-0\'s cited limits for the board' if out.get('flash') else 'no cited limit - the UNO figures 32256 / 2048 are used for scale only'}


def resources(combo, npins, n_header, tier_rep, weights):
    """-> {terms: [...], score, undetermined: n, parts_missing: [...], parts_unsure: [...]}. combo = {job: variant}."""
    w = dict(DEFAULT_WEIGHTS, **(weights or {}))
    lim = limits_of(tier_rep)
    sin = standin()
    terms, und = [], 0
    pers, parts, missing, unsure, flash, ram, cpu = {}, {}, {}, {}, [], [], []
    all_meas = True
    for job, v in combo.items():
        c, ps, _st = variant_costs(v)
        for p in __import__('json').loads(v['peripherals_json'] or '[]'):
            pers[p['kind']] = p
        if c['peripherals']['kind'] != 'measured':
            all_meas = False
        for p in ps:
            parts[p['class']] = p
            if p['on_bench'] is False:
                missing[p['class']] = p
            elif p['on_bench'] == 'undetermined':
                unsure[p['class']] = p
        flash.append((job, v['route'], c.get('flash_bytes')))
        ram.append((job, v['route'], c.get('ram_bytes')))
        cls = CPU_CLASS.get(v['route'])
        cpu.append((job, v['route'], cls, (c.get('cpu_share') or {}).get('value')))

    def add(key, quantity, fraction, stood=False, note=''):
        nonlocal und
        und += 1 if stood else 0
        terms.append({'key': key, 'label': WEIGHT_WORDS[key], 'kind': quantity['kind'], 'value': quantity['value'], 'unit': quantity['unit'], 'basis': quantity['basis'] + note,
                      'fraction': round(fraction, 4), 'weight': w[key], 'points': round(w[key] * fraction, 4), 'stand_in': stood})
    add('pins', q('measured', npins, 'pins', 'counted from the pin assignment'), npins / float(n_header))
    add('peripherals', q('measured' if all_meas else 'estimated', len(pers), 'blocks', 'union of the chosen routes\' declared on-chip blocks (%s); a block two routes both need counts once' % (', '.join(sorted(pers)) or 'none')),
        len(pers) / float(len(__import__('cmod.custom.isotope_variants_seeds', fromlist=['x']).PERIPHERAL_KINDS)))
    add('parts_to_acquire', q('measured', len(missing), 'parts', 'part classes no KitPart row provides: %s' % (', '.join(sorted(missing)) or 'none')), float(len(missing)))
    add('parts_used', q('estimated', len(parts), 'part classes', 'union of the chosen routes\' declared part classes' + ('; bench status undetermined for: %s' % ', '.join(sorted(unsure)) if unsure else '')),
        len(parts) / 10.0)
    for key, rows, limit, standkey in (('flash', flash, lim['flash'], 'flash_bytes'), ('ram', ram, lim['ram'], 'ram_bytes')):
        total, kinds, bits, stood = 0, set(), [], False
        for job, route, cst in rows:
            val = (cst or {}).get('value')
            if isinstance(val, (int, float)):
                total += val
                kinds.add((cst or {}).get('kind'))
                bits.append('%s %s B (%s)' % (route, val, (cst or {}).get('kind')))
            else:
                total += sin[standkey]
                stood = True
                bits.append('%s undetermined -> stand-in %s B (the largest known size in the catalogue)' % (route, sin[standkey]))
        kern = (tier_rep or {}).get('kernel', {}).get('flash' if key == 'flash' else 'sram')
        if kern is not None:
            if kern.get('value') is None:
                total += int(limit * KERNEL_STANDIN)
                stood = True
                bits.append('kernel undetermined -> stand-in %d B (%d%% of the limit)' % (int(limit * KERNEL_STANDIN), int(KERNEL_STANDIN * 100)))
            else:
                total += kern['value']
                bits.append('kernel %s B (%s)' % (kern['value'], kern['kind']))
        kind = 'undetermined' if stood else ('measured' if kinds == {'measured'} else 'estimated')
        add(key, q(kind, total, 'bytes', '; '.join(bits) + ' - the variable part only (routes + kernel); limit %d B (%s). Several sizes are LOWER BOUNDS (their basis says so)' % (limit, lim['basis'])),
            total / float(limit), stood, ' [scored with a stand-in]' if stood else '')
    cl = [c for _j, _r, c, _t in cpu]
    stood = any(c is None for c in cl)
    tot = sum((c if c is not None else CPU_STANDIN * 4) for c in cl)
    add('cpu', q('undetermined' if stood else 'estimated', tot, 'class points', 'ordinal CPU class per route (0 hardware does it .. 4 busy-bit-timed), read off iso-0\'s cpu_share words: '
                 + '; '.join('%s class %s' % (r, c if c is not None else 'none -> stand-in %.0f' % (CPU_STANDIN * 4)) for _j, r, c, _t in cpu)), tot / (4.0 * max(1, len(cpu))), stood)
    return {'terms': terms, 'score': round(sum(t['points'] for t in terms), 4), 'undetermined': und,
            'parts_missing': [{'class': c, 'why': p['why']} for c, p in sorted(missing.items())], 'parts_unsure': [{'class': c, 'why': p['why']} for c, p in sorted(unsure.items())]}


# ------------------------------------------------------------------ the cycle model
def _atoms_us(v, clock_hz, spec_ctx):
    """For a route with atoms: (init_us, work_us, event?, undetermined [..], basis) from rt-0's per-atom cycle upper bounds."""
    from cmod.custom import approach_profile_atoms as A
    from cmod.custom import code_interface as CI
    imp = IV._implementation(v)
    if not imp['atoms'] or imp['missing']:
        return None
    init_c = work_c = 0
    und, event, blocks = [], False, 0.0
    names, bases = [], []
    ctx = dict(spec_ctx or {}, variant=imp.get('config') or (spec_ctx or {}).get('variant'))   # cyc-0: read the run of the variant that builds this route
    for n, _a, _m in imp['atoms']:
        project, _man, atom = CI.find_atom(n)
        an = A.analyse(project, atom, ctx)
        if not an['bounded']:
            und.append('%s: %s' % (n, '; '.join(an['unbounded'])))
        isr = n.endswith('_vect')
        event = event or isr
        c = an['cycles_ub']
        if '_init' in n:
            init_c += c
        else:
            work_c += c
        bases.append(an['cycles_basis'])
        names.append('%s %d%s' % (n.split(':', 1)[1], c, ' measured' if an['cycles_basis'] == 'measured' else ''))
        for b in an['blocking']:
            val = b['worst_us']['value']
            if b.get('inside_measured'):
                continue
            if val is None:
                und.append('%s waits: %s' % (n, b['worst_us']['basis'][:80]))
            else:
                blocks += val
    measured = bool(bases) and all(b == 'measured' for b in bases)
    waits = blocks
    word = 'MEASURED cycles on the simavr twin (cycle record of %s)' % ctx['variant'] if measured else (
        'measured cycles where a cycle record has them, else rt-0 upper bounds' if any(b != 'upper-bound' for b in bases) else 'rt-0 cycle upper bounds')
    return {'init_us': init_c / clock_hz * 1e6, 'work_us': work_c / clock_hz * 1e6 + blocks, 'event': event, 'und': und, 'measured': measured, 'waits_us': waits,
            'basis': '%s of the route\'s atoms (%s cycles) at %.0f MHz%s' % (word, ', '.join(names), clock_hz / 1e6, (' plus %.0f us of waiting on hardware' % blocks) if blocks else '')}


#: a route with no atoms of its own is timed from the route that has them (same ISR plumbing) plus the extra cycles it needs - one basis, so the two compare fairly
SIBLING = {'pin-change-interrupt': ('ext-interrupt', 12, 'finding which pin of the bank moved (read the port, compare with the saved copy)'),
           'analog-comparator': ('ext-interrupt', 0, 'the same ISR plumbing')}


def standin_work_us(clock):
    """The stand-in for an undetermined step of work: the SLOWEST known step in the route table (the I2C transaction, 200 us) - an unknown never looks faster than that."""
    best = 200.0
    for _r, (_m, cyc, _i, _u, _h) in ROUTE_CYCLES.items():
        if isinstance(cyc, int):
            best = max(best, cyc / clock * 1e6)
    return best


def route_timing(v, direction, hw, spec_ctx, siblings=None):
    """-> {init_us, work_us, mode (polled|event|immediate), undetermined [...], basis, source (rt-0 atoms | counted)} or all-undetermined off the AVR."""
    if hw['soc'] != 'atmega328p' or not hw.get('clock_hz'):
        return {'init_us': None, 'work_us': None, 'mode': 'polled' if direction == 'in' else 'immediate', 'und': ['cycle counts here are for the AVR; %s is not modelled' % hw['soc']],
                'basis': 'undetermined: the timing table is AVR instruction counts', 'source': 'none'}
    clock = float(hw['clock_hz'])
    route = v['route']
    mode, cyc, init_c, und, how = ROUTE_CYCLES.get(route, ('polled' if direction == 'in' else 'immediate', None, None, ['no timing rule for this route'], 'none'))
    sib = SIBLING.get(route)
    if sib and siblings and not IV._implementation(v)['atoms']:
        base = (siblings.get(v['job']) or {}).get(sib[0])
        at0 = _atoms_us(base, clock, spec_ctx) if base is not None else None
        if at0 is not None:
            base_init_c = ROUTE_CYCLES[sib[0]][2] or 0
            return {'init_us': at0['init_us'] + max(0, (init_c or 0) - base_init_c) / clock * 1e6, 'work_us': at0['work_us'] + sib[1] / clock * 1e6, 'mode': 'event', 'und': list(und) + at0['und'],
                    'basis': 'the %s route\'s bound (%s) plus %d counted cycles (%s); %s' % (sib[0], at0['basis'], sib[1], sib[2], how),
                    'source': ('measured atoms + counted' if at0['measured'] else 'rt-0 atoms + counted')}
    at = _atoms_us(v, clock, spec_ctx)
    if at is not None:
        return {'init_us': at['init_us'], 'work_us': at['work_us'], 'mode': 'event' if at['event'] else mode, 'und': at['und'], 'basis': at['basis'],
                'source': ('measured atoms' if not at['waits_us'] else 'measured atoms + estimated wait') if at['measured'] else 'rt-0 atoms'}
    if route in ('analog-threshold', 'analog-read', 'analog-sensor'):
        work = 13.0 * 128 / clock * 1e6 + 20 / clock * 1e6
    elif cyc == 'bus':
        work = 200.0
    elif cyc is None:
        return {'init_us': (init_c or 0) / clock * 1e6 if init_c is not None else None, 'work_us': None, 'mode': mode, 'und': und or ['not derived'], 'basis': how, 'source': 'none'}
    else:
        work = cyc / clock * 1e6
    return {'init_us': (init_c or 0) / clock * 1e6, 'work_us': work, 'mode': mode, 'und': list(und), 'basis': '%s (counted by structure, not measured)' % how, 'source': 'counted'}


def cycle(combo, timing_for, mission_purposes, hw, spec, approach, job_purposes, fixed_atoms_skip):
    """The Mission cycle for a choice of variants. -> {total_us: q, purposes: [...], undetermined: n, stand_in_us, notes}."""
    lp = SI.loop_pass_us(approach)
    pass_us = lp['value'] if lp else None
    stand = SC_standin(hw)
    stand_basis = 'the slowest known step in the route table (%.0f us)' % stand
    wait_stand = pass_us if pass_us else 10000.0
    timings = {job: timing_for(job, v) for job, v in combo.items()}
    rows, total, n_und = [], 0.0, 0
    for p in mission_purposes:
        trig = (p.get('trigger') or {}).get('kind', '')
        boot = trig == 'boot'
        us, parts = 0.0, []
        fixed, fixed_bases = 0.0, []
        for proc_ in (spec or {}).get('processors', []):
            for t in proc_['tasks']:
                if p['purpose'] in t['serves'] and t['atom'] not in fixed_atoms_skip and (t['lane'] == 'init') == boot:
                    fixed += t['known_us'] or 0.0
                    fixed_bases.append(t.get('cycles_basis', 'upper-bound'))
        if fixed:
            us += fixed
            all_m = bool(fixed_bases) and all(b == 'measured' for b in fixed_bases)
            parts.append({'what': 'the firmware\'s other tasks (apply, telemetry, clock ...)', 'us': round(fixed, 2), 'kind': 'measured' if all_m else 'estimated',
                          'basis': ('cycle counts MEASURED on the simavr twin (cycle record; the CPU part where a task waits on the USART) of the tasks no route replaces' if all_m else
                                    'rt-0 cycle upper bounds (measured where a cycle record has them) of the tasks no route replaces; their unbounded parts are left out (a lower bound)')})
        for job, v in combo.items():
            if p['purpose'] not in job_purposes.get(job, ()):
                continue
            t = timings[job]
            val = t['init_us'] if boot else t['work_us']
            if val is None:
                val, kind = stand, 'undetermined'
                n_und += 1
                basis = 'undetermined (%s) -> stand-in %s' % ('; '.join(t['und'][:2]) or 'no figure', stand_basis)
            else:
                kind = 'measured' if t['source'] == 'measured atoms' else 'estimated'
                basis = '%s: %s' % (v['route'], t['basis'])
                if t['und']:
                    val += stand
                    kind = 'undetermined'
                    n_und += 1
                    basis += ' + stand-in %s for: %s' % (stand_basis, '; '.join(t['und'][:2]))
            us += val
            parts.append({'what': '%s via %s' % (job, v['route']), 'us': round(val, 2), 'kind': kind, 'basis': basis})
            if not boot and TRIGGER_OF(p) == job and t['mode'] == 'polled':
                w = pass_us if pass_us else None
                if w is None:
                    w, wk = wait_stand, 'undetermined'
                    n_und += 1
                else:
                    wk = 'estimated'
                us += w
                parts.append({'what': 'waiting for the main loop to look at the %s (a polled trigger)' % job, 'us': round(w, 2), 'kind': wk,
                              'basis': 'up to one main-loop pass (rt-0 upper bound %s)' % ('%.0f us' % w if wk == 'estimated' else 'unknown -> stand-in 10 ms')})
        dl = (p.get('deadline_ms') or {}).get('value')
        db = (p.get('debounce_ms') or {}).get('value') or 0
        if dl is None or boot:
            crit = {'state': 'no bound', 'why': 'the Purpose states no deadline' if not boot else 'a boot Purpose: no deadline applies'}
        else:
            budget = dl * 1000.0 - db * 1000.0
            und_here = any(x['kind'] == 'undetermined' for x in parts)
            crit = {'state': 'violates' if us > budget else ('fits (with a stand-in)' if und_here else 'fits'), 'budget_us': budget, 'cycle_us': round(us, 2), 'safety_critical': bool(p.get('safety_critical')),
                    'why': '%s: the Purpose cycle %s against its deadline %s ms%s' % (p['purpose'], '%.0f us' % us, dl, (' minus the %s ms debounce' % db) if db else '')}
        rows.append({'purpose': p['purpose'], 'trigger': trig, 'us': round(us, 2), 'parts': parts, 'criterion': crit})
        total += us
    kinds = [x['kind'] for r_ in rows for x in r_['parts']]
    mix = 'basis of the parts: %d measured on the twin, %d estimated/counted, %d undetermined' % (kinds.count('measured'), kinds.count('estimated'), kinds.count('undetermined'))
    return {'bases': {k: kinds.count(k) for k in ('measured', 'estimated', 'undetermined')},
            'total_us': q('undetermined' if n_und else ('measured' if kinds and all(k == 'measured' for k in kinds) else 'estimated'), round(total, 2), 'us',
                          'sum of the Purpose cycles: each Purpose once, from its trigger to its last task (his definitions); %s%s' % (mix, '; %d part(s) scored at a stand-in' % n_und if n_und else '')), 'purposes': rows, 'undetermined': n_und, 'criteria_violated': [r['criterion']['why'] for r in rows if r['criterion']['state'] == 'violates'], 'timings': {j: {k: t[k] for k in ('mode', 'basis', 'source', 'und')} for j, t in timings.items()}}


def SC_standin(hw):
    return standin_work_us(float(hw.get('clock_hz') or 16000000))


def TRIGGER_OF(purpose):
    return SI.TRIGGER_JOB.get((purpose.get('trigger') or {}).get('kind', ''))
