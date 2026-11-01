"""
@module board.custom.protection_models

esd-3 / esd-6 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): EACH PROTECTION PART'S SPICE MODEL, DERIVED FROM ITS DATASHEET NUMBERS on ngspice's own elements (a
diode, a behavioural current source, a capacitor) - no vendor model file (the user's words 2026-10-31: "remember to prefer open source"; vendor models
come under their own licences). Re-exported by board.custom.protection_parts.

  spice_model(row) -> (model_name, line, basis, why)   why = the refusal in words ('' when modelled); line = the .model line, or the varistor's law
  elements(row, k, model_name) -> deck lines           part k between esd_p<k> and ground (the 0 V meter Vprotm<k> is the caller's)
  check_points(row) / check_deck(row)                  the cited (current, voltage) points the model must land on, both polarities for a
                                                       bidirectional part, and an ngspice operating-point deck forcing each current into its own copy

  tvs-uni   one diode: BV = V_BR max at I_T, IBV = I_T, NBV = 1; RS = (V_C - BV - Vt ln(I_PP / IBV)) / I_PP; N = (V_F - I_F RS) / (Vt ln(I_F / IS))
  tvs-bi    two equal diodes cathode to cathode (the forward one adds its drop - V_BR and V_C are the PAIR's): the pair lands exactly on V_BR max at I_T and on
            V_C at I_PP for any forward N:
              RS = (V_C - V_BR - (1 + N) Vt ln(I_PP / I_T)) / (2 (I_PP - I_T)),   BV = V_BR - N Vt ln(I_T / IS) - 2 I_T RS
            N = N_FWD_BI = 1, a LABELLED assumption (the ideal junction): a bidirectional datasheet gives no forward pair (Bourns' V_F is "for unidirectional
            units only"); N shapes the curve between the two rated points, not the points
  varistor  the varistor law I = k V^alpha (both polarities), through the two cited points: V_V max (V_V + its tolerance) at its 1 mA test
            current and v_c max at i_c:  alpha = ln(i_c / I_T) / ln(v_c / V_V max), k = I_T / V_V max^alpha; plus its typical capacitance when it is
            a number; written sgn(V) pwr(abs(V), alpha) (KiCad 10's libngspice has no pwrs).
            Above i_c a real varistor rises faster than the law (its grain resistance - the datasheet gives that only as a graph): there the law
            UNDERSTATES the voltage, and the event's rows say when the peak current went past i_c
  polymer   refused: a snapback device (triggers at hundreds of volts, then clamps) is not a breakdown diode, and its clamping voltage comes without the
            current it is measured at
Vt = k T / q at ngspice's TNOM 27 C; IS = 1e-14 A (ngspice's diode default).
"""
import math

UNKNOWN = -1.0
IS_A = 1e-14                       # ngspice's diode default saturation current
VT_TNOM = 1.380649e-23 * 300.15 / 1.602176634e-19   # k T / q at ngspice's TNOM 27 C
N_FWD_BI = 1.0                     # labelled assumption: a bidirectional TVS's forward emission coefficient (the ideal junction)


def model_name(name):
    return 'esdp_' + ''.join(c if c.isalnum() else '_' for c in name.lower())


def _num(r, k):
    v = r.get(k, UNKNOWN)
    return float(v) if v is not None else UNKNOWN


def _v(r, k, unit='V'):
    v = _num(r, k)
    return '%g %s' % (v, unit) if v >= 0 else 'not given'


def _need(r, keys, what):
    miss = [k for k in keys if _num(r, k) <= 0]
    return ('%s needs %s from the datasheet (not given)' % (what, ', '.join(miss))) if miss else ''


def _cap(r):
    return (' CJO=%gp' % _num(r, 'cap_pf')) if _num(r, 'cap_pf') > 0 else ''


def _cap_words(r):
    return ('CJO %g pF' % _num(r, 'cap_pf')) if _num(r, 'cap_pf') > 0 else 'no capacitance given as a number - none modelled (the peak is, if anything, overstated)'


def _uni(r):
    why = _need(r, ('v_br_max', 'i_t_ma', 'v_c_v', 'i_pp_a', 'v_f_v', 'i_f_a'), 'a TVS model')
    if why:
        return '', '', '', why
    bv, ibv, vc, ipp, vf, i_f = (_num(r, k) for k in ('v_br_max', 'i_t_ma', 'v_c_v', 'i_pp_a', 'v_f_v', 'i_f_a'))
    ibv /= 1000.0
    rs = (vc - bv - VT_TNOM * math.log(ipp / ibv)) / ipp
    n = (vf - i_f * rs) / (VT_TNOM * math.log(i_f / IS_A))
    if rs <= 0 or n <= 0:
        return '', '', '', 'the ratings give a non-physical model (RS %.4g, N %.4g) - check the numbers' % (rs, n)
    name = model_name(r['name'])
    line = '.model %s D(IS=%g N=%.4f RS=%.6g BV=%g IBV=%g NBV=1%s)' % (name, IS_A, n, rs, bv, ibv, _cap(r))
    basis = ('BV = V_BR max %g V at I_T %g mA; RS = (V_C %g V - BV - Vt ln(I_PP/I_T)) / I_PP %g A (%s) = %.4g Ohm; N = (V_F %g V - I_F RS) / (Vt ln(I_F/IS)) '
             'at I_F %g A = %.4g; IS %g A (ngspice default), Vt %.5g V (TNOM 27 C); %s (%s)'
             % (bv, ibv * 1000, vc, ipp, r.get('pulse') or 'its pulse', rs, vf, i_f, n, IS_A, VT_TNOM, _cap_words(r), r.get('document') or r.get('origin')))
    return name, line, basis, ''


def _bi(r):
    why = _need(r, ('v_br_max', 'i_t_ma', 'v_c_v', 'i_pp_a'), 'a bidirectional TVS model')
    if why:
        return '', '', '', why
    vbr, it, vc, ipp = (_num(r, k) for k in ('v_br_max', 'i_t_ma', 'v_c_v', 'i_pp_a'))
    it /= 1000.0
    n = N_FWD_BI
    rs = (vc - vbr - (1.0 + n) * VT_TNOM * math.log(ipp / it)) / (2.0 * (ipp - it))
    bv = vbr - n * VT_TNOM * math.log(it / IS_A) - 2.0 * it * rs
    if rs <= 0 or bv <= 0:
        return '', '', '', 'the ratings give a non-physical model (RS %.4g, BV %.4g) - check the numbers' % (rs, bv)
    name = model_name(r['name'])
    line = '.model %s D(IS=%g N=%g RS=%.6g BV=%.6g IBV=%g NBV=1%s)' % (name, IS_A, n, rs, bv, it, _cap(r))
    basis = ('two equal diodes cathode to cathode, the pair landing on V_BR max %g V at I_T %g mA and on V_C %g V at I_PP %g A (%s): RS = (V_C - V_BR - '
             '(1 + N) Vt ln(I_PP/I_T)) / (2 (I_PP - I_T)) = %.4g Ohm each; BV = V_BR - N Vt ln(I_T/IS) - 2 I_T RS = %.5g V each; N = %g - a LABELLED '
             'assumption (the ideal junction; the datasheet gives no forward pair for a bidirectional part) that shapes the curve between the two rated '
             'points, not the points; IS %g A, Vt %.5g V (TNOM 27 C); %s (%s)'
             % (vbr, it * 1000, vc, ipp, r.get('pulse') or 'its pulse', rs, bv, n, IS_A, VT_TNOM, _cap_words(r), r.get('document') or r.get('origin')))
    return name, line, basis, ''


def varistor_law(r):
    """(k, alpha, v_v_max, i_t_a, v_c, i_c) - the law I = k V^alpha through the two cited points, or None when a number is missing."""
    vv, it, vc = _num(r, 'v_br_max'), _num(r, 'i_t_ma') / 1000.0, _num(r, 'v_c_v')
    ic = _num(r, 'i_c_a') if _num(r, 'i_c_a') > 0 else _num(r, 'i_pp_a')
    if min(vv, it, vc, ic) <= 0 or vc <= vv or ic <= it:
        return None
    alpha = math.log(ic / it) / math.log(vc / vv)
    return it / vv ** alpha, alpha, vv, it, vc, ic


def _varistor(r):
    why = _need(r, ('v_br_max', 'i_t_ma', 'v_c_v'), 'a varistor model')
    law = None if why else varistor_law(r)
    if law is None:
        return '', '', '', why or 'a varistor model needs v_c above V_V and its current above the 1 mA test current'
    _, alpha, vv, it, vc, ic = law
    name = model_name(r['name'])
    line = 'I = %g * sgn(V) * pwr(abs(V) / %g, %.5g)%s' % (it, vv, alpha, (' with %g pF across it' % _num(r, 'cap_pf')) if _num(r, 'cap_pf') > 0 else '')
    basis = ('the varistor law I = k V^alpha through V_V max %g V (V_V with its tolerance) at %g mA and v_c max %g V at i_c %g A: alpha = ln(i_c / I_T) / '
             'ln(v_c / V_V max) = %.4g; both polarities (sgn(V) |V|^alpha), a behavioural current source; %s; above i_c a real varistor rises faster (its grain '
             'resistance, given only as a graph) - there the law UNDERSTATES the voltage (%s)'
             % (vv, it * 1000, vc, ic, alpha, ('C %g pF typical across it' % _num(r, 'cap_pf')) if _num(r, 'cap_pf') > 0 else 'no capacitance given as a number',
                r.get('document') or r.get('origin')))
    return name, line, basis, ''


def spice_model(r):
    """(model_name, .model line or the varistor's law, basis in words, why) - why is the refusal ('' when modelled)."""
    kind = r.get('kind')
    if kind == 'polymer':
        return '', '', '', ('a snapback polymer suppressor (triggers at %s, then clamps at %s) is not a breakdown diode, and its clamping voltage comes without '
                            'the current it is measured at - no derived model' % (_v(r, 'v_trigger_v'), _v(r, 'v_c_v')))
    return {'tvs-uni': _uni, 'tvs-bi': _bi, 'varistor': _varistor}.get(kind, lambda _r: ('', '', '', 'unknown kind %r' % kind))(r)


def elements(r, k, mname):
    """(element lines, .model lines) for part k between esd_p<k> and ground."""
    kind = r.get('kind')
    if kind == 'tvs-bi':
        return ['Dprot%da 0 esd_q%d %s' % (k, k, mname), 'Dprot%db esd_p%d esd_q%d %s' % (k, k, k, mname)], [spice_model(r)[1]]
    if kind == 'varistor':
        coef, alpha, vv = varistor_law(r)[:3]
        # sgn(V) * pwr(abs(V), alpha): both polarities, whatever pwr's own sign rule (KiCad 10's libngspice has no pwrs - seen on econ-core)
        out = ['Bprot%d esd_p%d 0 I = %g * sgn(v(esd_p%d)) * pwr(abs(v(esd_p%d)) / %g, %.5g)' % (k, k, coef * vv ** alpha, k, k, vv, alpha)]
        if _num(r, 'cap_pf') > 0:
            out.append('Cprot%d esd_p%d 0 %gp' % (k, k, _num(r, 'cap_pf')))
        return out, []
    return ['Dprot%d 0 esd_p%d %s' % (k, k, mname)], [spice_model(r)[1]]


def check_points(r):
    """[(current A, the cited voltage V)] the model is derived to land on (both polarities for tvs-bi / varistor; the forward pair for tvs-uni)."""
    kind = r.get('kind')
    if kind == 'tvs-uni':
        return [(_num(r, 'i_t_ma') / 1000.0, _num(r, 'v_br_max')), (_num(r, 'i_pp_a'), _num(r, 'v_c_v')), (-_num(r, 'i_f_a'), -_num(r, 'v_f_v'))]
    if kind == 'tvs-bi':
        pts = [(_num(r, 'i_t_ma') / 1000.0, _num(r, 'v_br_max')), (_num(r, 'i_pp_a'), _num(r, 'v_c_v'))]
    elif kind == 'varistor' and varistor_law(r):
        _, _, vv, it, vc, ic = varistor_law(r)
        pts = [(it, vv), (ic, vc)]
    else:
        return []
    return pts + [(-i, -v) for i, v in pts]


def check_deck(r):
    """An ngspice deck: each check point's current forced into its own copy of the part (.op); node esd_p<k> should sit at the cited voltage."""
    mname, line, _, why = spice_model(r)
    if why:
        return ''
    out, models = ['* esd-6: %s at its cited points (board.custom.protection_models.check_deck)' % r['name']], set()
    for k, (i, _) in enumerate(check_points(r), 1):
        lines, mods = elements(r, k, mname)
        out += ['Ichk%d 0 esd_p%d DC %g' % (k, k, i)] + lines
        models |= {m for m in mods if m}
    return '\n'.join(out + sorted(models) + ['.op', '.end']) + '\n'
