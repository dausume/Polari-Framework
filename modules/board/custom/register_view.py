"""
@module board.custom.register_view

rm-3 (REGISTER_MAPPING_PLAN.md §5): the rows the Registers bench view reads, derived on every read from the hardware chain (Register, RegisterField,
RegisterAccessKind) + the taxonomy (rm-0) + the pin stages (rm-1) + what the firmware does with a register (cmod, imported lazily: board never depends on it).

  categories(soc)                 -> one row per REGISTER CATEGORY (his word, 2026-10-29: "register categories" - Polari already says tree for the object
                                     tree): domain / category / count / registers / state; a chip with no ingested registers (the C3 until rm-2b) answers every
                                     category with count 0, said
  registers(soc, category)        -> the registers of one register category (or all): title, address, reset, categories, read / write roles, fields, cite
  pins(soc) / pin_uses(soc, pin)  -> THE OTHER WAY IN (his ask: "if we choose a pin in the Bench view we should be able to see relevant registers and their
                                     categories and places they are used in Catoms in the firmware"): a pin -> its register fields (named for the pin, or for a
                                     function the pin offers: D2 -> INT0 -> EICRA.ISC0) with their register categories -> the firmware's settings of them, the
                                     Catom assertions naming the pin, the HAL variable at it, the C atoms touching those registers
  detail(soc, name, view)         -> fields: every bit field with its access word SPELLED OUT (the RegisterAccessKind row's read / write effect), reset, values,
                                     pin, signal, roles; settings: the RegisterSetting / RegisterFieldSetting rows a firmware solution derives for it (phase, value,
                                     the field's meaning, the task that owns it); atoms: the C atoms that touch it (the cmod parse)
  field_pins(soc, field)          -> the pin a field drives, the board pin it is, and its lifecycle stages (rm-1 assess) - a field with no pin says so
"""
import json

SOCS = {'atmega328p': 'arduino-uno-r3', 'esp32c3': 'esp32-c3'}
DETAIL_VIEWS = ('fields', 'settings', 'atoms')
SOLUTIONS = {'atmega328p': (('uno-light', 'uno-light-graph'),)}   # the firmware solutions whose settings are shown (the bench's light)
_C3 = 'not ingested yet: the ESP32-C3 registers are rm-2b (the drawing set from the TRM)'


def _get(o, k, d=''):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _rows(tables, cls, fallback):
    rows = (tables or {}).get(cls)
    return [r if isinstance(r, dict) else {k: _get(r, k) for k in vars(r) if not k.startswith('_')} for r in rows] if rows else fallback()


def _registers(tables):
    from board.custom import hardware_chain as H
    from board.custom import hardware_chain_c3 as H3
    return _rows(tables, 'Register', lambda: H.registers() + H3.registers())   # rm-2b: both chips' seeds when no server rows


def _fields(tables):
    from board.custom import hardware_chain as H
    from board.custom import hardware_chain_c3 as H3
    return _rows(tables, 'RegisterField', lambda: H.register_fields() + H3.register_fields())


#: which chip a cmod C project's atoms run on (the project prefix of CFunctionAtom.name) - an atom of another chip's firmware never "uses" this chip's pin
ATOM_PROJECT_SOC = {'uno': 'atmega328p', 'c3': 'esp32c3'}   # c3: cmod.custom.c3_atoms (2026-10-29)


def _known(soc):
    if soc not in SOCS:
        raise KeyError('soc must be one of %s' % ', '.join(SOCS))


def socs(tables=None):
    """One row per chip the view knows: its board, how many registers / fields are ingested, and the state."""
    regs, fields = _registers(tables), _fields(tables)
    out = []
    for soc, board in SOCS.items():
        n = sum(1 for r in regs if r.get('soc') == soc)
        out.append({'soc': soc, 'board': board, 'registers': n, 'fields': sum(1 for f in fields if f.get('soc') == soc),
                    'state': 'ingested (cited)' if n else _C3})
    return out


def categories(soc, tables=None):
    _known(soc)
    from board.custom import register_taxonomy as T
    regs = [r['name'].split(':', 1)[1] for r in _registers(tables) if r.get('soc') == soc]
    rows = T.categories(soc, regs)
    if not regs:
        rows = [dict(r, state=_C3) for r in rows]
    return rows


def registers(soc, category='', tables=None):
    _known(soc)
    fields = _fields(tables)
    out = []
    for r in _registers(tables):
        if r.get('soc') != soc:
            continue
        doms = json.loads(r.get('domains_json') or '[]')
        if category and category not in doms:
            continue
        roles = json.loads(r.get('roles_json') or '{}')
        n = sum(1 for f in fields if f['register'] == r['name'])
        out.append({'name': r['name'], 'register': r['name'].split(':', 1)[1], 'title': r.get('description', ''), 'address': '%s (%s)' % (r.get('addr', ''), r.get('space', '')) if r.get('addr') else '', 'peripheral': r.get('peripheral', ''),
                    'reset_value': r.get('reset_value', ''), 'categories': ', '.join(doms), 'read_roles': ', '.join(roles.get('read', [])),
                    'write_roles': ', '.join(roles.get('write', [])), 'fields': n, 'fields_note': '' if n else (r.get('undetermined') or 'no fields'),
                    'cite': r.get('page_table') or r.get('taxonomy_cite', '')})
    return sorted(out, key=lambda x: x['register'])


def _bits(f):
    return str(f['bit_hi']) if f['bit_hi'] == f['bit_lo'] else '%s:%s' % (f['bit_hi'], f['bit_lo'])


def _values_text(f):
    try:
        v = json.loads(f.get('values_json') or '{}')
    except ValueError:
        return ''
    return '; '.join('%s = %s' % (k, m) for k, m in v.items())


def _settings(soc, reg_name):
    try:
        from cmod.custom import claims as C
    except Exception as e:  # noqa: BLE001
        return [{'solution': '', 'phase': '', 'field': '', 'value': '', 'meaning': 'cmod is not on this instance: no firmware settings to show (%s)' % e, 'task': ''}]
    out = []
    for sol, graph in SOLUTIONS.get(soc, ()):
        got = C.register_settings(sol, graph)
        for rs in [x for x in got['RegisterSetting'] if x['register'] == reg_name]:
            fs = [x for x in got['RegisterFieldSetting'] if x['register_setting'] == rs['name']]
            for x in fs or [None]:
                out.append({'solution': sol, 'phase': rs['phase'], 'register_value': rs['value'], 'write_mask': rs['write_mask'],
                            'field': x['register_field'].split('.', 1)[-1] if x else '(whole register)', 'value': x['value'] if x else rs['value'],
                            'meaning': x['meaning'] if x else '', 'task': x['task'] if x else '', 'pin_claim': x['pin_claim'] if x else '', 'status': rs['status']})
    return out


def _atoms(reg, soc=''):
    try:
        from cmod.cmod_seed import CMOD_SEED_PAIRS
    except Exception as e:  # noqa: BLE001
        return [{'atom': '', 'module': '', 'registers': '', 'note': 'cmod is not on this instance (%s)' % e}]
    atoms = [a for n, _c, rs in CMOD_SEED_PAIRS if n == 'CFunctionAtom' for a in rs
             if not soc or ATOM_PROJECT_SOC.get(a['name'].split(':', 1)[0]) == soc]   # an atom of the register's own chip's firmware
    return [{'atom': a['name'], 'module': a.get('module', ''), 'registers': a.get('registers', ''),
             'note': ('through its ESP-IDF driver calls, each cited to the IDF source (cmod.custom.c3_atoms)' if a['name'].startswith('c3:')
                      else 'the cmod parse of the atom\'s body names it')}
            for a in atoms if reg in [x.strip() for x in (a.get('registers') or '').split(',')]]


def detail(soc, name, view='fields', tables=None):
    """None when the register is not on the chip; else the rows of one view."""
    _known(soc)
    reg_name = name if ':' in name else '%s:%s' % (soc, name)
    if not any(r['name'] == reg_name for r in _registers(tables)):
        return None
    if view == 'fields':
        from board.custom import register_access as RA
        out = []
        for f in sorted([f for f in _fields(tables) if f['register'] == reg_name], key=lambda f: -int(f['bit_hi'])):
            k = RA.kind(f['access']) or {}
            roles = json.loads(f.get('roles_json') or '{}')
            out.append({'name': f['name'], 'field': f['field'], 'bits': _bits(f), 'access': f['access'], 'access_means': k.get('title', '(no RegisterAccessKind row)'),
                        'on_read': k.get('read_effect', ''), 'on_write': k.get('write_effect', ''), 'reset_value': f['reset_value'], 'description': f['description'],
                        'values': _values_text(f), 'pin': f.get('affects_pin', '').split(':')[-1], 'signal': f.get('affects_signal', '').split(':')[-1],
                        'read_roles': ', '.join(roles.get('read', [])), 'write_roles': ', '.join(roles.get('write', [])), 'cite': f['page_table'], 'notes': f.get('notes', '')})
        return out
    if view == 'settings':
        return _settings(soc, reg_name)
    if view == 'atoms':
        return _atoms(reg_name.split(':', 1)[1], soc)
    raise KeyError('view must be one of %s' % ', '.join(DETAIL_VIEWS))


def field_pins(soc, field, tables=None):
    """None when the field is not on the chip; [] rows + a note when it drives no pin; else one row per lifecycle stage of the board pin it drives."""
    _known(soc)
    fname = field if ':' in field else '%s:%s' % (soc, field)
    f = next((x for x in _fields(tables) if x['name'] == fname), None)
    if f is None:
        return None
    pin = (f.get('affects_pin') or '').split(':')[-1]
    if not pin:
        return []
    board = SOCS[soc]
    canon = pin
    if soc == 'atmega328p':
        from board.custom.board_uno import D_PINS, A_PINS
        canon = next((c for c, (s, _n) in list(D_PINS.items()) + list(A_PINS.items()) if s == pin), pin)
    from board.custom import pin_stages as P
    a = P.assess(board, canon)
    return [{'field': fname.split(':', 1)[1], 'soc_pin': pin, 'board_pin': canon, 'stage': s['stage'], 'owner': s['owner'], 'function': s['function'],
             'verdict': s['verdict'], 'boot_critical': s['boot_critical'], 'reasons': s['reasons']} for s in a['stages']]


# ------------------------------------------------------------------------------------------------ the other way in: from a pin
def _pin_table(soc):
    """{soc pin: (board pin, [functions])}."""
    if soc == 'atmega328p':
        from board.custom.soc_atmega328p import PINS
        from board.custom.board_uno import D_PINS, A_PINS
        board = {s: c for c, (s, _n) in list(D_PINS.items()) + list(A_PINS.items())}
        return {p: (board.get(p, ''), list(fns)) for p, (_n, fns) in PINS.items()}
    if soc == 'esp32c3':
        import json
        from board.custom import board_c3
        # the pad's own functions (its SocPin row: the IO MUX functions + analog, datasheet Table 2-4) - matrix-routed signals reach any pad (said per row)
        return {r['pin']: (r['pin'], [f for f in json.loads(r['functions_json']) if f != r['pin']]) for r in board_c3.soc_pins()}
    return {}


def resolve(soc, pin):
    """The SoC pin a name means (UNO D2 / PD2 -> PD2; C3 GPIO9 / 9 -> GPIO9), or ''."""
    t = _pin_table(soc)
    v = str(pin).strip().upper()
    if v in t:
        return v
    if soc == 'esp32c3' and v.isdigit():
        v = 'GPIO' + v
    return next((p for p, (b, _f) in t.items() if b.upper() == v), v if v in t else '')


def pins(soc, tables=None):
    _known(soc)
    fields = _fields(tables)
    out = []
    import re as _re
    for p, (board, fns) in sorted(_pin_table(soc).items(), key=lambda kv: [int(t) if t.isdigit() else t for t in _re.split(r'(\d+)', kv[0])]):
        n = sum(1 for f in fields if f.get('soc') == soc and (f.get('affects_pin', '').split(':')[-1] == p or f.get('affects_signal', '').split(':')[-1] in fns))
        out.append({'ref': '%s:%s' % (soc, p), 'soc_pin': p, 'board_pin': board, 'functions': ', '.join(fns), 'register_fields': n})
    return out


def _categories_of(reg_row):
    return ', '.join(dict.fromkeys(json.loads(reg_row.get('domains_json') or '[]')))


def pin_uses(soc, pin, tables=None, cmod_rows=None):
    """None for a pin the chip does not have; else flat rows, one per use: kind = register field | firmware setting | Catom assertion | HAL variable | C atom.
    `cmod_rows` = {'CatomAssertion': [...], 'CatomVariable': [...], 'FirmwareVariant': [...]} from a server (the seeds otherwise)."""
    _known(soc)
    p = resolve(soc, pin)
    if not p:
        return None
    board, fns = _pin_table(soc)[p]
    from board.custom import register_access as RA
    regs = {r['name']: r for r in _registers(tables)}
    out, field_names, reg_names = [], set(), set()
    for f in _fields(tables):
        if f.get('soc') != soc:
            continue
        direct = f.get('affects_pin', '').split(':')[-1] == p
        sig = f.get('affects_signal', '').split(':')[-1]
        # rm-2b: a GPIO-matrix signal (U0RXD_in / U0TXD_out) reaches the pad whose IO MUX function it is (U0RXD on GPIO20)
        base = sig.rsplit('_', 1)[0] if sig.endswith(('_in', '_out')) else sig
        if not direct and sig not in fns and base not in fns:
            continue
        r = regs.get(f['register'], {})
        k = RA.kind(f['access']) or {}
        field_names.add(f['name'])
        reg_names.add(f['register'])
        out.append({'kind': 'register field', 'name': f['name'].split(':', 1)[1], 'category': _categories_of(r),
                    'detail': '%s (bits %s, %s: %s)' % (f['description'], _bits(f), f['access'], k.get('title', '')),
                    'how': 'names the pin' if direct else ('through %s, a function %s offers' % (sig, p) if sig in fns else
                                                           'through %s, the matrix signal of %s - %s\'s IO MUX function' % (sig, base, p)), 'used_by': '', 'status': '', 'cite': f['page_table']})
    try:
        from cmod.custom import claims as C
        from cmod.custom import catom_assertions as CA
        from cmod.custom import catom_variables as CV
        from cmod.cmod_seed import CMOD_SEED_PAIRS
    except Exception as e:  # noqa: BLE001
        out.append({'kind': 'note', 'name': '', 'category': '', 'detail': 'cmod is not on this instance: no firmware uses to show (%s)' % e, 'how': '', 'used_by': '',
                    'status': '', 'cite': ''})
        return out
    cm = cmod_rows or {}
    for sol, graph in SOLUTIONS.get(soc, ()):
        got = C.register_settings(sol, graph)
        for x in [x for x in got['RegisterFieldSetting'] if x['register_field'] in field_names]:
            out.append({'kind': 'firmware setting', 'name': x['register_field'].split(':', 1)[1], 'category': _categories_of(regs.get(x['register_field'].split('.')[0], {})),
                        'detail': '%s = %s: %s' % (x['register_field'].split('.', 1)[-1], x['value'], x['meaning']), 'how': x['register_setting'].rsplit(':', 1)[-1] + ' phase',
                        'used_by': '%s (task %s)' % (sol, x['task']), 'status': x['status'], 'cite': x['rule']})
    sure = {}   # atom (short name) -> why it certainly uses THIS pin
    hal_here = set()   # the HAL variables whose value is this pin
    variants = sorted({a['variant'] for a in CA.SEED_ASSERTIONS} | {v['variant'] for v in CV.SEED_VARIABLES if v['soc'] == soc})
    for variant in variants:
        for a in CA.assertions(variant, cm.get('CatomAssertion')):
            if p in [x.strip() for x in (a['pins'] or '').split(',')]:
                sure.setdefault(CA._short(a['atom']), 'the Catom assertion %s names %s' % (a['kind'], p))
                out.append({'kind': 'Catom assertion', 'name': CA._short(a['atom']), 'category': '', 'detail': '%s %s (%s lane, %s)' % (a['kind'], a['fields'] or a['bridge'],
                            a['lane'], a['event'] or '-'), 'how': 'the assertion names the pin', 'used_by': variant, 'status': a['status'], 'cite': a['basis']})
        for v in CV.pin_roles(variant, cm.get('CatomVariable'), cm.get('FirmwareVariant')):
            if v['pin'] == p:
                hal_here.add(v['variable'])
                full = next((x for x in CV.variables(variant, cm.get('CatomVariable'), cm.get('FirmwareVariant')) if x['variable'] == v['variable']), {})
                for atom in [x for x in (full.get('used_by') or '').split(',') if x]:
                    sure.setdefault(atom, 'it reads the HAL value %s, which is %s' % (v['variable'], p))
                out.append({'kind': 'HAL variable', 'name': v['variable'], 'category': '', 'detail': '%s = %s (%s scope)' % (v['role'], v['value'], v['scope']),
                            'how': 'the HAL value is this pin', 'used_by': variant, 'status': v['verdict'], 'cite': ''})
    short = {r.split(':', 1)[1] for r in reg_names}
    atoms = []
    for a in [a for n, _c, rs in CMOD_SEED_PAIRS if n == 'CFunctionAtom' for a in rs]:
        if ATOM_PROJECT_SOC.get(a['name'].split(':', 1)[0]) != soc:
            continue   # another chip's firmware (the C3's firmware is not parsed into atoms yet: said in the note below)
        touched = short & {x.strip() for x in (a.get('registers') or '').split(',')}
        key = a['name'].split(':', 1)[-1]
        declared = sorted(h for h in hal_here if 'declared %s' % h in (a.get('resources_summary') or ''))
        if not touched and not declared:
            continue
        if declared and key not in sure:
            if a['name'].startswith('c3:'):
                from cmod.custom.c3_atoms import PIN_MACROS
                macro = {v: k for k, v in PIN_MACROS.items()}
                sure[key] = 'its body names %s (the HAL value %s), which is %s - read from the source text (cmod.custom.c3_atoms)' % (
                    ', '.join(macro.get(h, h) for h in declared), ', '.join(declared), p)
            else:
                sure[key] = 'its POLARI_NODE annotation declares uses(%s), and %s is %s' % (', '.join(declared), ', '.join(declared), p)
        cats = sorted({c.strip() for t in touched for c in _categories_of(regs.get('%s:%s' % (soc, t), {})).split(',') if c.strip()})
        why = sure.get(key)
        atoms.append((0 if why else 1, {'kind': 'C atom', 'name': a['name'], 'category': ', '.join(cats), 'detail': ('its body touches %s' % ', '.join(sorted(touched))) if touched else 'touches none of these registers itself (it goes through the HAL)',
                                        'how': ('USES THIS PIN: ' + why) if why else 'shares the register: which bit it writes is not parsed (the cmod parse names registers, '
                                                                                     'not bits) and no uses() annotation or assertion ties it to this pin', 'used_by': a.get('module', ''), 'status': 'certain' if why else 'register only',
                                        'cite': 'the cmod parse of the atom'}))
    if soc not in ATOM_PROJECT_SOC.values():
        atoms.append((2, {'kind': 'note', 'name': '', 'category': '', 'detail': 'no C firmware of the %s is parsed into atoms yet (cmod parses the UNO project): no C atom rows' % soc,
                          'how': '', 'used_by': '', 'status': '', 'cite': ''}))
    return out + [r for _o, r in sorted(atoms, key=lambda x: (x[0], x[1]['name']))]
