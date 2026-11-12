"""
@module cmod.custom.measure_bands

msv-1 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 4, items 2-3; D-msv-4 worst-case corners): WHAT A CORRECT BUILD MAY READ. The
cst slice's ngspice .op of a node's circuit state is run at every corner of the parts' tolerances, and the band is the lowest to the highest
value each probe takes. A reading outside the band is not explained by the parts; it goes to a person's look.

The parameters and their sources:
  the 5 V rail      VCC_WINDOW_V: KNOB - a USB host port's VBUS window as commonly stated for USB 2.0 (4.75-5.25 V, not read here). When the unit has
                    a reading of its own rail at this node, the rail is THAT reading +/- its meter band instead (derived from the unit, said).
  the pin's drive   DERIVED from the cited ATmega328P Table 30-1 (DS40002061B p.323, board.custom.electrical_atmega328p):
                    - VOH >= 4.2 V at IOH = -20 mA, VCC = 5 V (TA = 85 C): the high side's output resistance 0..(5 - 4.2) / 0.020 = 40 ohm
                    - VOL <= 0.9 V at IOL = 20 mA: the low side's 0..45 ohm
                    0 is the ideal-source bound the deck already used. The 85 C figures bound a room-temperature part from the safe side.
  each resistor     R_TOL: KNOB +/-5 % - a 4-band resistor's gold band; brown (1 %) when the part in hand says so. The kit page does not list it
                    (KitPart arduino-starter-kit:resistors).
  each LED          LED_VF_20MA_V: KNOB 1.8..2.5 V at 20 mA - the kit LED has no rating on its cited page (KitPart arduino-starter-kit:led;
                    ubc-led1 says v_forward is ASSUMED). The renderer's model is moved to each end (cst_netlist._led_model). The user's kit LED
                    Vf (an owed fact) or its datasheet replaces it.
  the pull-up       the cited 20..50 kohm (cst_netlist.PULLUP_OHMS).
Meter loading (item 2) is a separate run with the instrument in the deck: its cited input resistance on a V point, its burden in series on an I
point. The nominal moves by what the meter itself does to the circuit. An instrument with no cited impedance gets no loading, and that is said.

  corners(cat, state, vcc=None)       -> {probe: (lo, hi)} + the words; cached per circuit / state / rail
  loading(cat, state, point, acc)     -> (shift in SI, words)
"""
import itertools
import math

VCC_WINDOW_V = (4.75, 5.25)    # KNOB: USB 2.0 high-power host port VBUS as commonly stated - not read here; the unit's own rail reading replaces it
R_TOL = 0.05                   # KNOB: a gold 4th band (+/-5 %); brown = 1 %
LED_VF_20MA_V = (1.8, 2.5)     # KNOB: no datasheet for the kit LED - a red indicator LED window at 20 mA; the user's kit LED Vf replaces it
VOH_MIN_V, VOL_MAX_V, I_TEST_A = 4.2, 0.9, 0.020   # CITED: DS40002061B Table 30-1 p.323 (5 V, 85 C) via board.custom.electrical_atmega328p
R_OUT_HIGH_MAX = (5.0 - VOH_MIN_V) / I_TEST_A      # DERIVED 40 ohm
R_OUT_LOW_MAX = VOL_MAX_V / I_TEST_A               # DERIVED 45 ohm

_CACHE = {}


def model_vf(i_a):
    """The renderer's LED model's forward voltage at i_a (the diode law + its series resistance, 27 C) - so the knob's window is a shift of it."""
    import re
    from electrodevice.custom.spice_run import LED_MODEL
    f = dict((k, float(v)) for k, v in re.findall(r'(\w+)=([-+0-9.eE]+)', LED_MODEL))
    vt = 1.380649e-23 * 300.15 / 1.602176634e-19
    return f['N'] * vt * math.log(i_a / f['Is'] + 1) + i_a * f['Rs']


def basis_words(vcc=None):
    return ('worst-case corners (D-msv-4) of: the rail %s; each resistor +/-%g %% (KNOB, the gold band); each LED Vf %g..%g V at 20 mA (KNOB: the kit LED has no '
            'cited rating); a driven pin\'s output resistance 0..%g ohm high / 0..%g ohm low (DERIVED from VOH 4.2 V / VOL 0.9 V at 20 mA, DS40002061B Table 30-1); '
            'the pull-up 20..50 kohm (cited)' % ('%.4g V as this unit reads it' % vcc if vcc else '%g..%g V (KNOB: a USB host port, not read here)' % VCC_WINDOW_V,
                                                 R_TOL * 100, LED_VF_20MA_V[0], LED_VF_20MA_V[1], R_OUT_HIGH_MAX, R_OUT_LOW_MAX))


def corners(cat, state, vcc=None):
    """-> {'bands': {probe: (lo, hi)}, 'runs': n, 'basis': words} over every corner (2^k runs, k = the parameters the state has)."""
    from electrodevice.custom import cst_netlist as N
    key = (cat['circuit'], state['name'], None if vcc is None else round(vcc[0], 6) if isinstance(vcc, tuple) else round(vcc, 6))
    if key in _CACHE:
        return _CACHE[key]
    rails = vcc if isinstance(vcc, tuple) else ((vcc, vcc) if vcc else VCC_WINDOW_V)
    res = [n for n, c in cat['components'].items() if c['kind'] == 'resistor']
    leds = [n for n, c in cat['components'].items() if c['kind'] in ('led',)]
    modes = {state['modes'].get(p, d['at_init']) for p, d in cat['pins'].items()}
    axes = [('vcc', sorted(set(rails)))]
    axes += [('r:' + n, (1 - R_TOL, 1 + R_TOL)) for n in res]
    axes += [('led:' + n, tuple(v - model_vf(I_TEST_A) for v in LED_VF_20MA_V)) for n in leds]
    if 'driven-high' in modes:
        axes.append(('r_out_high', (0.0, R_OUT_HIGH_MAX)))
    if 'driven-low' in modes:
        axes.append(('r_out_low', (0.0, R_OUT_LOW_MAX)))
    pulls = N.PULLUP_OHMS if 'input-pullup' in modes else (N.PULLUP_OHMS[0],)
    bands, runs = {}, 0
    for combo in itertools.product(*[vals for _k, vals in axes]):
        vary = {'r_scale': {}, 'led_dv': {}}
        for (k, _vals), val in zip(axes, combo):
            if k == 'vcc':
                vary['vcc'] = val
            elif k.startswith('r:'):
                vary['r_scale'][k[2:]] = val
            elif k.startswith('led:'):
                vary['led_dv'][k[4:]] = val
            else:
                vary[k] = val
        for pu in pulls:
            r = N.run(state, cat, pu, vary)
            runs += 1
            if not r.get('ok'):
                continue
            for probe, value in r['measurements'].items():
                lo, hi = bands.get(probe, (float(value), float(value)))
                bands[probe] = (min(lo, float(value)), max(hi, float(value)))
    out = {'bands': bands, 'runs': runs, 'basis': basis_words(vcc if not isinstance(vcc, tuple) else None)}
    _CACHE[key] = out
    return out


def loading(cat, state, point, acc):
    """The meter's own effect on the reading: one run with it in the deck, against the nominal. -> (shift in SI, words)."""
    from electrodevice.custom import cst_netlist as N
    if acc is None:
        return 0.0, 'no meter line: no loading'
    if point['quantity'] == 'V dc':
        ohms = float(acc.get('input_ohms') or -1)
        if ohms <= 0:
            return 0.0, 'the meter\'s input resistance is not cited: no loading applied'
        if point['plus_at'] not in {n['net'] for n in cat['nets'].values()}:
            return 0.0, 'not a net of the circuit: no loading applied'
        vary, probe = {'meter_v': (point['plus_at'], ohms)}, 'v(%s)' % point['plus_at'].lower()
        what = 'its %g ohm input from %s to GND' % (ohms, point['plus_at'])
    else:
        ohms = float(acc.get('burden_v_per_a') or -1)
        if ohms <= 0:
            return 0.0, 'the meter\'s burden is not cited: no loading applied'
        vary, probe = {'meter_i': (point['plus_at'], ohms)}, 'i(vam_%s)' % point['plus_at'].replace('-', '_').replace(':', '_').lower()
        what = 'its %g ohm burden in series with %s' % (ohms, point['plus_at'])
    base, loaded = N.run(state, cat, N.PULLUP_OHMS[0]), N.run(state, cat, N.PULLUP_OHMS[0], vary)
    if not (base.get('ok') and loaded.get('ok')) or probe not in base['measurements']:
        return 0.0, 'the loading run did not give %s: no loading applied' % probe
    shift = float(loaded['measurements'][probe]) - float(base['measurements'][probe])
    return shift, 'the meter loads the circuit: %s moves the reading by %+.4g' % (what, shift)
