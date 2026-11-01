"""
@module pcb.custom.electrothermal

tmp-3 (AI-Notes/plans/TEMPERATURE_PLAN.md; the user's words 2026-10-31: "Build it starting with whole temperagure ... then part level, and so
on"): THE CIRCUIT HEATS ITSELF - the two-way loop. tmp-2 ran each part at the temperature the board gave it; here the run's own powers set those
temperatures, and the circuit is run again at them, until nothing changes (it settled) or every pass comes out hotter by more than the last
(thermal runaway). Nothing new is modelled: the circuit is ngspice's (each part's own temperature terms), the heat is the existing models.

  the pass    run the deck with every part at its temperature (pcb.custom.spice_temperature.run_at, instance temp= where ngspice takes one) and its
              device vectors kept (kicad_spice.POWER_VECTORS), read each part's average power (pcb.custom.thermal.dissipation)
  the heat    a board with a layout: the steady plate FEM (pcb.custom.thermal_spread.spread with those powers, every part with pads probed), a part's
              junction = the board under it + P x its datasheet Rth j-board (sum of its Foster R; steady, so the Foster and Cauer forms agree).
              No layout (a schematic only): a part's datasheet Rth j-a (PartThermalModel rth_ja_k_w - measured on THE DATASHEET'S test board, said);
              a part with neither stays at the background, said
  the loop    plain fixed-point iteration T_{k+1} = T_ambient + rise(P(T_k)), optionally under-relaxed (RELAX, a knob). For one part it converges
              exactly when the loop gain g = d(rise)/dT < 1, the same condition under which the real part is thermally stable (its temperature
              obeys tau dT/dt = T_ambient + rise(P(T)) - T, stable for g < 1) - so a diverging loop IS the runaway, not a numerical artefact.
              The estimated gain (each pass's change over the last) is reported.

Time scales: the circuit's (us - ms) and the board's (s - min) are far apart, so each pass is the circuit settled at fixed temperatures; this is
the steady loop - a pulsed power's electro-thermal transient is the board over time (pcb.custom.thermal_transient), not iterated here.

  settle(manager, board, ambient_c, runner=None, rows=None, h=None, tol_c=TOL_C, max_passes=MAX_PASSES, relax=RELAX, t_cap_c=T_CAP_C) -> result
  last(board)   the newest loop's result in this process (the runs themselves are kept as every run is)
"""
import datetime

TOL_C = 0.05        # a KNOB: settled when no part moves more than this between passes (K)
MAX_PASSES = 12     # a KNOB
RELAX = 1.0         # a KNOB: 1 = plain iteration; below 1 damps it (a damped loop still diverges on a true runaway, only slower)
T_CAP_C = 400.0     # a KNOB: past this a part is called run away whatever the trend (silicon is long gone; no datasheet rates it)
_LAST = {}


def _heat(manager, board, powers, ambient_c, rows, h):
    """{ref: (temp C, how)} for every part the heat reaches, from these powers."""
    from pcb.custom.thermal import H_FREE_AIR
    from pcb.custom.thermal_inputs import models
    from pcb.custom.thermal_spread import plate_inputs, spread
    mods = models(manager, board, rows)
    plate, why = plate_inputs(board, rows)
    out = {}
    if not why:
        probe = {r: 0.0 for r in plate['pads']}
        probe.update({r: w for r, w in powers.items()})
        summary, hot, _f, why2 = spread(manager, board, rows=rows, h=h or H_FREE_AIR, powers=probe)
        if why2:
            return {}, why2
        for row in hot:
            m = mods.get(row['ref'])
            rise, how = row['mean_rise_c'], 'the board under its pads (steady plate FEM)'
            if m and m['stages'] and row['power_w'] > 0:
                rise += row['power_w'] * m['rth']
                how = 'its junction: the board under it + P x Rth j-%s %.4g K/W (%s)' % (m['reference'], m['rth'], m['name'])
            out[row['ref']] = (ambient_c + rise, how)
        return out, ''
    for ref, w in powers.items():
        m = mods.get(ref)
        if m and m['rth_ja_k_w']:
            out[ref] = (ambient_c + w * m['rth_ja_k_w'], 'P x its datasheet Rth j-a %g K/W (%s) - on the datasheet\'s own test board: this board has no '
                                                          'layout' % (m['rth_ja_k_w'], m['name']))
    return out, ''


def _powers(manager, board, run, rows):
    from pcb.custom import kicad_spice as P
    from pcb.custom.thermal import dissipation
    parts, why = dissipation(manager, board, run, rows)
    if why:
        return {}, [], why
    refs = {n: e.get('ref', n) for n, e in P.build_deck(rows)['elements'].items()}
    powers = {refs.get(p['ref'], p['ref']): p['avg_w'] for p in parts if p['kind'] != 'V' and p['avg_w'] > 0}
    unknown = [refs.get(p['ref'], p['ref']) for p in parts if p['avg_w'] == -1.0]
    return powers, unknown, ''


def settle(manager, board, ambient_c, runner=None, rows=None, h=None, tol_c=TOL_C, max_passes=MAX_PASSES, relax=RELAX, t_cap_c=T_CAP_C):
    from pcb.custom import spice_temperature as ST
    from pcb.custom.thermal_inputs import models
    rows = ST._rows(manager, board, rows)
    if not rows.get('SchematicSymbol'):
        return {'ok': False, 'error': 'no ingested schematic for %r' % board, 'status': 404}
    if not (0 < relax <= 1) or tol_c <= 0 or not 1 <= int(max_passes) <= 50:
        return {'ok': False, 'error': 'relax must be in (0, 1], tol_c > 0 and max_passes 1 .. 50', 'status': 400}
    mods = models(manager, board, rows)
    temps, passes, changes, how = {}, [], [], {}
    verdict, why_stop = '', ''
    for k in range(int(max_passes)):
        res = ST.run_at(manager, board, ambient_c, part_temps=dict(temps) or None, runner=runner, rows=rows, save_power=True)
        if not res.get('ok'):
            verdict, why_stop = 'stopped', 'pass %d did not run: %s' % (k + 1, res.get('refused') or res.get('error') or res.get('errors'))
            break
        powers, unknown, why = _powers(manager, board, res['run'], rows)
        if why:
            verdict, why_stop = 'stopped', why
            break
        heat, why = _heat(manager, board, powers, ambient_c, rows, h)
        if why:
            verdict, why_stop = 'stopped', why
            break
        new = {}
        for ref, (t, words) in heat.items():
            old = temps.get(ref, ambient_c)
            new[ref] = old + relax * (t - old)
            how[ref] = words
        change = max([abs(new[r] - temps.get(r, ambient_c)) for r in new] or [0.0])
        changes.append(change)
        for ref in sorted(set(new) | set(powers)):
            passes.append({'board': board, 'pass': k + 1, 'ref': ref, 'power_w': powers.get(ref, 0.0), 'ran_at_c': temps.get(ref, ambient_c),
                           'temp_c': new.get(ref, ambient_c), 'change_c': new.get(ref, ambient_c) - temps.get(ref, ambient_c), 'run': res['run'],
                           'basis': how.get(ref, 'the heat reaches it from nothing given (no layout and no datasheet Rth j-a): stays at the background')})
        temps = new
        if not heat:
            verdict, why_stop = 'nothing heats', ('no part\'s power reaches a temperature: %s has no layout and no part has a datasheet Rth j-a - '
                                                  'give one on the Thermal over time tab' % board)
            break
        hot = [r for r, t in temps.items() if t > t_cap_c]
        if hot:
            verdict, why_stop = 'runaway', '%s past %g C (a knob) after pass %d' % (', '.join(sorted(hot)), t_cap_c, k + 1)
            break
        if change < tol_c:
            verdict, why_stop = 'settled', 'no part moved more than %g K on pass %d' % (tol_c, k + 1)
            break
        if len(changes) >= 3 and changes[-1] > changes[-2] > changes[-3]:
            verdict, why_stop = 'runaway', ('every pass hotter by more than the last (%s K): the loop gain is above 1 - the part heats faster than its '
                                            'heat leaves' % ', '.join('%.3g' % c for c in changes[-3:]))
            break
    else:
        verdict, why_stop = 'not settled', 'still moving %.3g K after %d passes (a knob)' % (changes[-1], int(max_passes))
    gains = [b / a for a, b in zip(changes, changes[1:]) if a > 0]
    over = []
    for ref, t in temps.items():
        m = mods.get(ref)
        if m and m['tj_max_c'] and t > m['tj_max_c']:
            over.append('%s %.1f C above its Tj max %g C' % (ref, t, m['tj_max_c']))
    result = {'ok': True, 'board': board, 'ambient_c': ambient_c, 'verdict': verdict, 'why': why_stop, 'passes': len(changes),
              'loop_gain': gains[-1] if gains else -1.0, 'changes_c': changes, 'temps': temps, 'rows': passes, 'over_tj_max': over,
              'at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
              'basis': ('fixed-point loop: run the circuit at each part\'s temperature (device vectors kept for its power) -> the heat (%s) -> run again; '
                        'tol %g K, relax %g, at most %d passes, cap %g C (knobs); loop gain = each pass\'s change over the last (below 1 settles, '
                        'the real part\'s stability condition too)' % ('steady plate FEM + datasheet Rth j-board' if not _no_layout(board, rows) else
                                                                       'datasheet Rth j-a: no layout', tol_c, relax, int(max_passes), t_cap_c))}
    _LAST[board] = result
    return result


def _no_layout(board, rows):
    from pcb.custom.thermal_spread import plate_inputs
    return bool(plate_inputs(board, rows)[1])


def last(board):
    return _LAST.get(board)
