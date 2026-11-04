"""cmod_bands_selftest - msv-1 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 4 items 2-3, D-msv-4): TOLERANCE BANDS AND THE METER'S LOADING.

The UNO light's led-on state is run at every worst-case corner. The checks:
- The LED branch's band edges equal the HAND-COMPUTED corners. The 220 ohm + LED branch is solved with the diode law, by bisection, at the
  extremes: the rail, R1 +/-5 %, the LED Vf window, and D6's output resistance 0..40 ohm derived from VOH.
- Every probe's band holds its nominal, in every circuit state.
- The knobs are labelled.
- The nominal deck is unchanged.
- The meter's loading equals the hand estimate (10 Mohm against the 20 kohm pull-up; a 1 ohm burden in the LED branch).
- A unit's own rail reading narrows the band.

    PYTHONPATH=.:modules python3 -m cmod.cmod_bands_selftest      # from polari-framework/
"""
import math
import os
import re
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def _hand_led(vcc, r, rout, dv):
    """The branch current by hand: vcc = I (rout + r + Rs) + N Vt ln(I / Is' + 1), Is' = Is exp(-dv / (N Vt)); bisection on I."""
    from electrodevice.custom.spice_run import LED_MODEL
    f = dict((k, float(v)) for k, v in re.findall(r'(\w+)=([-+0-9.eE]+)', LED_MODEL))
    vt = 1.380649e-23 * 300.15 / 1.602176634e-19
    is_ = f['Is'] * math.exp(-dv / (f['N'] * vt))
    lo, hi = 1e-9, vcc / r
    for _ in range(200):
        mid = (lo + hi) / 2
        g = vcc - mid * (rout + r + f['Rs']) - f['N'] * vt * math.log(mid / is_ + 1)
        lo, hi = (mid, hi) if g > 0 else (lo, mid)
    return lo


def main():
    from cmod.custom import measure_bands as MB
    from cmod.custom import node_electrical as NE
    from electrodevice.custom import cst_netlist as N
    from electrodevice.custom.spice_run import capability
    if not capability()['available']:
        check('ngspice is available (the cst slice engine)', False, 'ngspice missing: run in the backend image')
        return
    c = NE.circuit('uno-light')
    cat = c['cat']
    st = {s['name']: s for s in c['states']}
    on = st['led-on']
    cor = MB.corners(cat, on)
    lo, hi = cor['bands']['i(vam_ubc_led1)']
    dvs = [v - MB.model_vf(0.020) for v in MB.LED_VF_20MA_V]
    h_hi = _hand_led(5.25, 220 * 0.95, 0.0, dvs[0])
    h_lo = _hand_led(4.75, 220 * 1.05, MB.R_OUT_HIGH_MAX, dvs[1])
    check('THE LED BAND EDGES = THE HAND CORNERS: high = 5.25 V, R1 209 ohm, D6 ideal, Vf at its 1.8 V end; low = 4.75 V, 231 ohm, D6 40 ohm, Vf 2.5 V '
          '(the diode law by bisection) - within 0.2 %%: %.4f..%.4f mA vs %.4f..%.4f mA' % (lo * 1e3, hi * 1e3, h_lo * 1e3, h_hi * 1e3),
          abs(lo - h_lo) / h_lo < 2e-3 and abs(hi - h_hi) / h_hi < 2e-3)
    vlo = cor['bands']['v(led_control)'][0]
    check('the LED_CONTROL net\'s low edge = 4.75 V less D6\'s 40 ohm times the current at that corner (the low rail, the low R, the low Vf) by hand',
          abs(vlo - (4.75 - MB.R_OUT_HIGH_MAX * _hand_led(4.75, 209.0, MB.R_OUT_HIGH_MAX, dvs[0]))) < 2e-3, vlo)
    check('the corner count: rail x R1 x LED x D6 drive (2^4) x the pull-up ends (D2 input-pullup) = 32 runs', cor['runs'] == 32, cor['runs'])
    check('D6\'s output resistance DERIVED from the cited VOH / VOL (5 - 4.2) / 20 mA = 40 ohm, 0.9 / 20 mA = 45 ohm; the knobs labelled in the words',
          abs(MB.R_OUT_HIGH_MAX - 40) < 1e-9 and abs(MB.R_OUT_LOW_MAX - 45) < 1e-9
          and all(w in cor['basis'] for w in ('KNOB, the gold band', 'KNOB: the kit LED has no cited rating', 'DERIVED from VOH', 'KNOB: a USB host port')))
    bad = []
    for name, s in st.items():
        base = N.run(s, cat)
        cb = MB.corners(cat, s)
        for probe, val in base['measurements'].items():
            b = cb['bands'].get(probe)
            if b is None or not (b[0] - 1e-9 <= float(val) <= b[1] + 1e-9):
                bad.append((name, probe, val, b))
    check('EVERY STATE: each probe\'s band holds its nominal (%d states)' % len(st), not bad, bad)
    check('the NOMINAL deck is unchanged by msv-1 (no varied line, the renderer\'s LED model only)',
          'msv-1' not in N.deck(on, cat)[0] and 'polari_led_' not in N.deck(on, cat)[0] and N.deck(on, cat)[0] == N.deck(on, cat, vary=None)[0])

    # loading
    pt_v = {'quantity': 'V dc', 'plus_at': 'BUTTON_INPUT'}
    sh, w = MB.loading(cat, on, pt_v, {'input_ohms': 10e6})
    hand = 5.0 * 10e6 / (10e6 + N.PULLUP_OHMS[0]) - 5.0
    check('LOADING V: a 10 Mohm meter on the pulled-up D2 net reads %.2f mV low; by hand 5 V x 10M / (10M + 20k) - 5 V = %.2f mV' % (sh * 1e3, hand * 1e3),
          abs(sh - hand) < 2e-4 and 'input' in w, w)
    pt_i = {'quantity': 'I dc', 'plus_at': 'ubc-led1'}
    sh2, w2 = MB.loading(cat, on, pt_i, {'burden_v_per_a': 1.0})
    i0 = 0.0147152
    hand2 = -i0 * 1.0 / (220 + 2 + 1.8 * 1.380649e-23 * 300.15 / 1.602176634e-19 / i0)
    check('LOADING I: a 1 ohm burden in the LED branch takes %.1f uA; by hand I x 1 / (R1 + Rs + N Vt / I) = %.1f uA (within 5 %%)' % (sh2 * 1e6, hand2 * 1e6),
          abs(sh2 - hand2) / abs(hand2) < 0.05, w2)
    check('an uncited impedance gives no loading, said', MB.loading(cat, on, pt_v, {'input_ohms': -1})[1].startswith('the meter\'s input resistance is not cited'))
    narrow = MB.corners(cat, on, vcc=(5.00 - 0.075, 5.00 + 0.075))
    nlo, nhi = narrow['bands']['i(vam_ubc_led1)']
    check('THE UNIT\'S OWN RAIL: a 5.00 V +/-75 mV reading narrows the LED band to %.2f..%.2f mA (inside the window\'s %.2f..%.2f)' % (nlo * 1e3, nhi * 1e3, lo * 1e3, hi * 1e3),
          lo < nlo < nhi < hi)


if __name__ == '__main__':
    sys.path[:0] = [os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')), os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))]
    main()
    print('\n%d/%d passed' % (passed, total))
    sys.exit(0 if passed == total else 1)
