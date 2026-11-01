"""
@module board.custom.protection_parts

esd-3 / esd-6 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): PROTECTION PARTS FROM THEIR DATASHEET NUMBERS - the catalogue (cited SEED + rows people define) and each
part's SPICE model, DERIVED from its ratings or refused in words.

  catalogue(manager)                     every ProtectionPart, one row each with its ratings in words and whether it can be modelled
  part(name, manager)                    one as a dict, or None
  spice_model(row) -> (model_name, line, basis, why)   board.custom.protection_models (re-exported): tvs-uni, tvs-bi (esd-6) and varistor (esd-6)
     DERIVED from the ratings on ngspice's own elements (no vendor model file); polymer refused in words
  define(manager, body) -> (status, body)   a person's own part (origin custom, or cited when a document is given)

SEED:
  smbj5.0a  Bourns SMBJ series datasheet REV. 09/20, Electrical Characteristics table, row SMBJ5.0A: V_RWM 5.0 V; V_BR 6.40 min / 7.00 max at I_T 10 mA;
            I_R 800 uA at V_RWM; V_C 9.2 V at I_PP 65.3 A (10/1000 us); V_C 12.0 V at I_PP 326.5 A (8/20 us); the first table: P_PK 600 W (1 ms),
            V_F 3.5 V max at I_PP 50 A (SMBJ5.0A ~ SMBJ90A, unidirectional), T_J -55 .. +150 C; capacitance only as the "Typical Junction Capacitance" graph
  cg0603mlc-05e  Bourns CG0603MLC-05E & -12E ChipGuard ESD Protectors REV. A 11/18, Electrical Characteristics: V_W(DC) <= 5 V; V_C 30 V typ and
            V_T 300 V typ (both by TLP, Note 1); V_P 300 V typ (IEC 61000-4-2 8 kV contact, Note 2); C_O 0.2 pF typ at 1 MHz; bidirectional; IEC 61000-4-2
            level 4 (+-8 kV contact, +-15 kV air); -55 .. +125 C; "not recommended for new designs" (CGA0603MLC-05E). The UNO R3's Z1 / Z2
            (board.custom.uno_schematic_paths). A snapback polymer: catalogued, not modelled.
  smbj5.0ca  esd-6: the same Bourns table, the bidirectional column of the SMBJ5.0A's row - the same V_BR 6.40 / 7.00 V at 10 mA, V_C 12.0 V at 326.5 A
            (8/20 us); V_F is "for unidirectional units only"
  s05k11    esd-6: TDK (EPCOS) SIOV metal oxide varistors, leaded, StandarD series (March 2018), type S05K11 = B72205S0110K101: V_V 18 V +-10 % at 1 mA;
            v_c,max 36 V at i_c 1.0 A; C_typ 1750 pF at 1 kHz; maximum ratings (T_A 105 C) V_RMS 11 V, V_DC 14 V, i_max 100 A (8/20 us, once); -40 .. +105 C
"""
import math

from board.custom.protection_models import IS_A, VT_TNOM, _v, elements, model_name, spice_model, varistor_law  # noqa: F401 - the models, their own file

CLS = 'ProtectionPart'
_MEM = {CLS: {}}
UNKNOWN = -1.0
SIOV_DOC = 'TDK (EPCOS) SIOV metal oxide varistors, leaded, StandarD series, B722* (March 2018)'
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
                                  'for new designs (CGA0603MLC-05E); the UNO R3\'s Z1 / Z2')},
    {'name': 'smbj5.0ca', 'kind': 'tvs-bi', 'part_number': 'SMBJ5.0CA', 'package': 'SMB (DO-214AA)', 'v_rwm': 5.0, 'v_br_min': 6.40, 'v_br_max': 7.00,
     'i_t_ma': 10.0, 'v_c_v': 12.0, 'i_pp_a': 326.5, 'pulse': '8/20 us', 'v_f_v': UNKNOWN, 'i_f_a': UNKNOWN, 'v_trigger_v': UNKNOWN, 'cap_pf': UNKNOWN,
     'i_c_a': UNKNOWN, 't_min_c': -55.0, 't_max_c': 150.0,
     'model_basis': 'the 8/20 us clamping pair (12.0 V at 326.5 A) and V_BR max at I_T, both the pair\'s; no forward pair (unidirectional units only)',
     'document': SMBJ_DOC, 'page_table': 'Electrical Characteristics part table, row SMBJ5.0A / SMBJ5.0CA (the bidirectional column)',
     'url': 'https://www.bourns.com/docs/Product-Datasheets/SMBJ.pdf', 'origin': 'cited',
     'notes': 'I_R 800 uA at V_RWM 5.0 V; P_PK 600 W (1 ms); "CA = 5 % tolerance bidirectional device" (How to Order); capacitance given only as a graph'},
    {'name': 's05k11', 'kind': 'varistor', 'part_number': 'SIOV-S05K11 (B72205S0110K101)', 'package': 'leaded disc, 5 mm', 'v_rwm': 14.0,
     'v_br_min': 16.2, 'v_br_max': 19.8, 'i_t_ma': 1.0, 'v_c_v': 36.0, 'i_pp_a': 100.0, 'pulse': '8/20 us (once)', 'v_f_v': UNKNOWN, 'i_f_a': UNKNOWN,
     'v_trigger_v': UNKNOWN, 'cap_pf': 1750.0, 'i_c_a': 1.0, 't_min_c': -40.0, 't_max_c': 105.0,
     'model_basis': 'V_V 18 V +-10 % at 1 mA (V_V max 19.8 V, the top of the spread) and v_c,max 36 V at i_c 1.0 A; C_typ 1750 pF (1 kHz)',
     'document': SIOV_DOC, 'page_table': 'Maximum ratings (T_A 105 C) and Characteristics (T_A 25 C) tables, V_RMS 11 V block, B72205S0110K101',
     'url': 'https://www.tdk-electronics.tdk.com/inf/70/db/var/SIOV_Leaded_StandarD.pdf', 'origin': 'cited',
     'notes': ('v_rwm = V_DC 14 V (maximum rating); i_pp_a = i_max 100 A (8/20 us, 1 time; 50 A nominal discharge, 15 times); W_max 0.3 J (2 ms); '
               'TDK\'s PSpice models come under TDK\'s own terms - the model here is derived from the two cited points instead')}]

_NUMS = ('v_rwm', 'v_br_min', 'v_br_max', 'i_t_ma', 'v_c_v', 'i_pp_a', 'v_f_v', 'i_f_a', 'v_trigger_v', 'cap_pf', 'i_c_a')


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


def ratings_words(r):
    at = ('%s; peak pulse %s (%s)' % (_v(r, 'i_c_a', 'A'), _v(r, 'i_pp_a', 'A'), r.get('pulse') or '-') if float(r.get('i_c_a', UNKNOWN)) > 0 else
          '%s (%s)' % (_v(r, 'i_pp_a', 'A'), r.get('pulse') or '-'))
    return ('working %s; breakdown %s .. %s at %s; clamps at %s at %s; forward %s at %s; trigger %s; %s'
            % (_v(r, 'v_rwm'), _v(r, 'v_br_min'), _v(r, 'v_br_max'), _v(r, 'i_t_ma', 'mA'), _v(r, 'v_c_v'), at,
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
