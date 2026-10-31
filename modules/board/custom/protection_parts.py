"""
@module board.custom.protection_parts

esd-3 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): PROTECTION PARTS FROM THEIR DATASHEET NUMBERS - the catalogue (cited SEED + rows people define) and each
part's SPICE model, DERIVED from its ratings or refused in words.

  catalogue(manager)                     every ProtectionPart, one row each with its ratings in words and whether it can be modelled
  part(name, manager)                    one as a dict, or None
  spice_model(row) -> (model_name, line, basis, why)   a unidirectional TVS as an ngspice diode:
        BV  = V_BR max at I_T (the top of the spread - the worst case for the protected net), IBV = I_T, NBV = 1
        RS  = (V_C - BV - Vt ln(I_PP / IBV)) / I_PP     the clamping pair at its rated pulse lands exactly on V_C at I_PP
        N   = (V_F - I_F RS) / (Vt ln(I_F / IS))         the forward pair lands exactly on V_F at I_F (IS = 1e-14 A, ngspice's default)
        Vt  = k T / q at ngspice's TNOM 27 C; no CJO when the datasheet gives the capacitance only as a graph (said - no capacitance means less of the
              shock is soaked up, so the protected net's peak is, if anything, overstated)
     refused: tvs-bi (two diodes in anti-series add a forward drop the datasheet's V_BR already includes - needs the vendor's model), varistor (a power
     law, not a breakdown knee - the vendor's model), polymer (snapback: it triggers at hundreds of volts and then clamps - not a breakdown diode)
  define(manager, body) -> (status, body)   a person's own part (origin custom, or cited when a document is given)

SEED:
  smbj5.0a  Bourns SMBJ series datasheet REV. 09/20, Electrical Characteristics table, row SMBJ5.0A: V_RWM 5.0 V; V_BR 6.40 min / 7.00 max at I_T 10 mA;
            I_R 800 uA at V_RWM; V_C 9.2 V at I_PP 65.3 A (10/1000 us); V_C 12.0 V at I_PP 326.5 A (8/20 us); the first table: P_PK 600 W (1 ms),
            V_F 3.5 V max at I_PP 50 A (SMBJ5.0A ~ SMBJ90A, unidirectional), T_J -55 .. +150 C; capacitance only as the "Typical Junction Capacitance" graph
  cg0603mlc-05e  Bourns CG0603MLC-05E & -12E ChipGuard ESD Protectors REV. A 11/18, Electrical Characteristics: V_W(DC) <= 5 V; V_C 30 V typ and
            V_T 300 V typ (both by TLP, Note 1); V_P 300 V typ (IEC 61000-4-2 8 kV contact, Note 2); C_O 0.2 pF typ at 1 MHz; bidirectional; IEC 61000-4-2
            level 4 (+-8 kV contact, +-15 kV air); -55 .. +125 C; "not recommended for new designs" (CGA0603MLC-05E). The UNO R3's Z1 / Z2
            (board.custom.uno_schematic_paths). A snapback polymer: catalogued, not modelled.
"""
import math

CLS = 'ProtectionPart'
_MEM = {CLS: {}}
UNKNOWN = -1.0
IS_A = 1e-14                       # ngspice's diode default saturation current
VT_TNOM = 1.380649e-23 * 300.15 / 1.602176634e-19   # k T / q at ngspice's TNOM 27 C
SMBJ_DOC = 'Bourns SMBJ Transient Voltage Suppressor Diode Series datasheet (REV. 09/20)'
CG_DOC = 'Bourns CG0603MLC-05E & -12E - ChipGuard ESD Protectors datasheet (REV. A 11/18)'

SEED = [
    {'name': 'smbj5.0a', 'kind': 'tvs-uni', 'part_number': 'SMBJ5.0A', 'package': 'SMB (DO-214AA)', 'v_rwm': 5.0, 'v_br_min': 6.40, 'v_br_max': 7.00,
     'i_t_ma': 10.0, 'v_c_v': 12.0, 'i_pp_a': 326.5, 'pulse': '8/20 us', 'v_f_v': 3.5, 'i_f_a': 50.0, 'v_trigger_v': UNKNOWN, 'cap_pf': UNKNOWN,
     't_min_c': -55.0, 't_max_c': 150.0,
     'model_basis': ('the 8/20 us clamping pair (12.0 V at 326.5 A) - the shorter of the two rated pulses, the nearer to an ESD event; the 10/1000 us pair '
                     '(9.2 V at 65.3 A) is the slower, hotter pulse and is not used; V_F 3.5 V max at 50 A for the forward side'),
     'document': SMBJ_DOC, 'page_table': 'Electrical Characteristics tables (p. 1 and the part table, row SMBJ5.0A)',
     'url': 'https://www.bourns.com/docs/Product-Datasheets/SMBJ.pdf', 'origin': 'cited',
     'notes': 'I_R 800 uA at V_RWM 5.0 V; P_PK 600 W (1 ms); capacitance given only as a graph'},
    {'name': 'cg0603mlc-05e', 'kind': 'polymer', 'part_number': 'CG0603MLC-05E', 'package': '0603 (1608 metric)', 'v_rwm': 5.0, 'v_br_min': UNKNOWN,
     'v_br_max': UNKNOWN, 'i_t_ma': UNKNOWN, 'v_c_v': 30.0, 'i_pp_a': UNKNOWN, 'pulse': 'TLP (Note 1)', 'v_f_v': UNKNOWN, 'i_f_a': UNKNOWN,
     'v_trigger_v': 300.0, 'cap_pf': 0.2, 't_min_c': -55.0, 't_max_c': 125.0, 'model_basis': '',
     'document': CG_DOC, 'page_table': 'Electrical Characteristics @ 25 C', 'url': 'https://www.bourns.com/docs/Product-Datasheets/CG0603MLC.pdf',
     'origin': 'cited', 'notes': ('typical values (V_C 30 V, V_T 300 V by TLP; V_P 300 V at IEC 61000-4-2 8 kV contact); bidirectional; not recommended '
                                  'for new designs (CGA0603MLC-05E); the UNO R3\'s Z1 / Z2')}]

_NUMS = ('v_rwm', 'v_br_min', 'v_br_max', 'i_t_ma', 'v_c_v', 'i_pp_a', 'v_f_v', 'i_f_a', 'v_trigger_v', 'cap_pf')


def _get(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def _fields():
    import inspect
    from board.objects.board.ProtectionPart import ProtectionPart
    return [k for k in inspect.signature(ProtectionPart.__init__).parameters if k not in ('self', 'manager')]


def _live(manager):
    if manager is None:
        return list(_MEM[CLS].values())
    return [{k: _get(o, k) for k in _fields()} for o in ((getattr(manager, 'objectTables', None) or {}).get(CLS) or {}).values()]


def model_name(name):
    return 'esdp_' + ''.join(c if c.isalnum() else '_' for c in name.lower())


def spice_model(r):
    """(model_name, .model line, basis in words, why) - why is the refusal ('' when modelled)."""
    kind = r.get('kind')
    if kind == 'polymer':
        return '', '', '', ('a snapback polymer suppressor (triggers at %s, then clamps at %s) is not a breakdown diode - no derived model; a vendor model '
                            'is needed' % (_v(r, 'v_trigger_v'), _v(r, 'v_c_v')))
    if kind == 'varistor':
        return '', '', '', 'a varistor follows a power law, not a diode\'s breakdown knee - no derived model; a vendor model is needed'
    if kind == 'tvs-bi':
        return '', '', '', ('a bidirectional TVS as two diodes in anti-series adds a forward drop that its datasheet V_BR already includes - not derived '
                            'yet; a vendor model is needed')
    if kind != 'tvs-uni':
        return '', '', '', 'unknown kind %r' % kind
    need = [k for k in ('v_br_max', 'i_t_ma', 'v_c_v', 'i_pp_a', 'v_f_v', 'i_f_a') if float(r.get(k, UNKNOWN)) <= 0]
    if need:
        return '', '', '', 'a TVS model needs %s from the datasheet (not given)' % ', '.join(need)
    bv, ibv, vc, ipp, vf, i_f = (float(r[k]) for k in ('v_br_max', 'i_t_ma', 'v_c_v', 'i_pp_a', 'v_f_v', 'i_f_a'))
    ibv /= 1000.0
    rs = (vc - bv - VT_TNOM * math.log(ipp / ibv)) / ipp
    n = (vf - i_f * rs) / (VT_TNOM * math.log(i_f / IS_A))
    if rs <= 0 or n <= 0:
        return '', '', '', 'the ratings give a non-physical model (RS %.4g, N %.4g) - check the numbers' % (rs, n)
    cj = (' CJO=%gp' % float(r['cap_pf'])) if float(r.get('cap_pf', UNKNOWN)) > 0 else ''
    name = model_name(r['name'])
    line = '.model %s D(IS=%g N=%.4f RS=%.6g BV=%g IBV=%g NBV=1%s)' % (name, IS_A, n, rs, bv, ibv, cj)
    basis = ('BV = V_BR max %g V at I_T %g mA; RS = (V_C %g V - BV - Vt ln(I_PP/I_T)) / I_PP %g A (%s) = %.4g Ohm; N = (V_F %g V - I_F RS) / (Vt ln(I_F/IS)) '
             'at I_F %g A = %.4g; IS %g A (ngspice default), Vt %.5g V (TNOM 27 C); %s (%s)'
             % (bv, ibv * 1000, vc, ipp, r.get('pulse') or 'its pulse', rs, vf, i_f, n, IS_A, VT_TNOM,
                ('CJO %g pF' % float(r['cap_pf'])) if cj else 'no capacitance given as a number - none modelled (the peak is, if anything, overstated)',
                r.get('document') or r.get('origin')))
    return name, line, basis, ''


def _v(r, k, unit='V'):
    v = float(r.get(k, UNKNOWN))
    return '%g %s' % (v, unit) if v >= 0 else 'not given'


def ratings_words(r):
    return ('working %s; breakdown %s .. %s at %s; clamps at %s at %s (%s); forward %s at %s; trigger %s; %s'
            % (_v(r, 'v_rwm'), _v(r, 'v_br_min'), _v(r, 'v_br_max'), _v(r, 'i_t_ma', 'mA'), _v(r, 'v_c_v'), _v(r, 'i_pp_a', 'A'), r.get('pulse') or '-',
               _v(r, 'v_f_v'), _v(r, 'i_f_a', 'A'), _v(r, 'v_trigger_v'), _v(r, 'cap_pf', 'pF')))


def catalogue(manager=None):
    by = {r['name']: dict(r) for r in SEED}
    by.update({r['name']: r for r in _live(manager)})
    out = []
    for r in sorted(by.values(), key=lambda r: r['name']):
        name, line, basis, why = spice_model(r)
        out.append(dict(r, ratings=ratings_words(r), modelled='yes' if name else 'no', model=line, model_why=basis or why))
    return out


def part(name, manager=None):
    return next((r for r in catalogue(manager) if r['name'] == name), None)


def define(manager, body):
    from board.objects.board.ProtectionPart import ProtectionPart
    if not isinstance(body, dict):
        return 400, {'ok': False, 'error': 'body must be an object'}
    name = str(body.get('name', '')).strip().lower()
    if not name or not all(c.isalnum() or c in '-_.' for c in name):
        return 400, {'ok': False, 'error': 'name needs letters, digits, - _ . only, got %r' % name}
    if any(s['name'] == name for s in SEED):
        return 409, {'ok': False, 'error': '%r is a cited catalogue part - give yours its own name' % name}
    if body.get('kind') not in ProtectionPart.KINDS:
        return 400, {'ok': False, 'error': 'kind must be one of %s' % ', '.join(ProtectionPart.KINDS)}
    row = {k: str(body.get(k, '')) for k in ('kind', 'part_number', 'package', 'pulse', 'model_basis', 'document', 'page_table', 'url', 'notes')}
    for k in _NUMS:
        try:
            v = float(body.get(k, UNKNOWN))
        except (TypeError, ValueError):
            return 400, {'ok': False, 'error': '%s needs a number' % k}
        if not math.isfinite(v) or (v < 0 and v != UNKNOWN):
            return 400, {'ok': False, 'error': '%s must be >= 0 or -1 (not given), got %r' % (k, body.get(k))}
        row[k] = v
    row.update(name=name, t_min_c=float(body.get('t_min_c', -300.0)), t_max_c=float(body.get('t_max_c', -300.0)),
               origin='cited' if body.get('document') else 'custom')
    if manager is None:
        _MEM[CLS][name] = row
    else:
        o = ProtectionPart(manager=manager, **row)
        try:
            manager.db.saveInstanceInDB(o)
        except Exception:  # noqa: BLE001 - an in-memory manager has no db
            pass
    m = spice_model(row)
    return 201, {'ok': True, 'name': name, 'origin': row['origin'], 'modelled': bool(m[0]), 'model_why': m[2] or m[3]}
