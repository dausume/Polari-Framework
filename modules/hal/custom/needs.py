"""
@module hal.custom.needs

WHAT THE HARDWARE GIVES AN ISOTOPE (hal-iso, HAL_CATOM_CATALOGUE_PLAN.md §5a; the user, 2026-11-14: "the HAL code should be set up to
interact with the isotope it gets embedded into so that the isotope gets the data about what is needed from hardware to make it
viable, this way they all tie together").

An isotope declares, per variable, the HAL operations it calls (isotope.json `requires`). For ONE chip and the pins a configuration
chose, every (variable, operation) is a NEED. The HAL answers each need with a record, not a yes/no:

  verdict    fits | chip-lacks (a cited fact about the chip) | not-recorded (a gap in our tables, NOT a fact about the chip) | refused
  name       the isotope's own word for it: HAL_<ROLE>_<OP> where ROLE comes from the isotope's variable (button_pin -> BUTTON), so
             the isotope's C is the same text on every chip; which register plays it is the header's business only
  settings   register.field = value via mechanism, per binding, each with its datasheet cite
  yields     what the hardware told the generator on the way (signum = 0, the vector INT0_vect)

  role_of(variable)                         -> 'BUTTON' for 'button_pin'
  answer(soc, requires, pins)               -> {viable, needs[record], missing[record]}
  header(soc, requires, pins, reserved)     -> the isotope's header (units + its own names), or raises NeedsRefused naming each unmet need
  rows(catom, isotope, soc, pin)            -> HalIsotopeNeed rows for one isotope on one pin (every pin variable on that pin)
"""
from hal.custom import generate as G
from hal.custom import operations as OPS
from hal.custom import render as RD
from hal.custom import soc_rules as SR

VERDICT = {'resolved': 'fits', 'unsupported': 'chip-lacks', 'undetermined': 'not-recorded', 'refused': 'refused'}


class NeedsRefused(ValueError):
    pass


def role_of(variable):
    v = str(variable)
    return (v[:-len('_pin')] if v.endswith('_pin') else v).upper()


def _suffix(op, role):
    from board.custom.gen import _role_suffix   # ONE naming rule with the shared hal.c roles (HAL_LED_SET_HIGH)
    return _role_suffix(op, role)


def _verdict(soc, operation, status):
    """the generator's status -> the isotope's verdict. A role the chip rules do not name at all is a gap in OUR data
    (not-recorded), never a claim that the chip lacks it; `unsupported` stays chip-lacks only when a rule or a pin fact says so."""
    v = VERDICT.get(status, 'refused')
    if v == 'chip-lacks':
        roles = SR.RULES[soc].get('roles') or {}
        if any(p['role'] not in roles for p in OPS.parts(OPS.by_name(operation) or {'parts': []})):
            return 'not-recorded'
    return v


def _record(soc, variable, operation, pin):
    res = G.unit(soc, operation, pin)
    u = res['unit']
    role = role_of(variable)
    yields = [s['output'] for s in res['steps'] if s.get('step') == 'yield']
    yields += ['vector ' + s['output'] for s in res['steps'] if s.get('step') == 'vector' and u['status'] == 'resolved']
    yields = list(dict.fromkeys(yields))   # two parts may report the same fact (EICRA and EIMSK both yield signum)
    return {'variable': variable, 'role': role, 'operation': operation, 'pin': pin, 'soc': soc,
            'name': 'HAL_%s_%s' % (role, _suffix(operation, role)), 'key': u['key'], 'unit_macro': u.get('macro', ''),
            'status': u['status'], 'verdict': _verdict(soc, operation, u['status']), 'why': u.get('why', ''),
            'settings': '; '.join('%s.%s%s via %s' % (b['register'], b['field'], (' = %s' % b['value']) if str(b.get('value', '')) != '' else '',
                                                    b['mechanism']) for b in res['bindings']),
            'cites': '; '.join(sorted({b['cite'] for b in res['bindings'] if b.get('cite')})),
            'yields': '; '.join(yields), 'intent': (OPS.by_name(operation) or {}).get('intent', '')}


def answer(soc, reqs, pins):
    needs = []
    for var, ops in sorted(reqs.items()):
        pin = pins.get(var)
        for op in ops:
            if not pin:
                needs.append({'variable': var, 'role': role_of(var), 'operation': op, 'pin': '', 'soc': soc, 'name': '', 'key': '',
                              'unit_macro': '', 'status': 'refused', 'verdict': 'refused', 'why': 'no pin chosen for %s' % var,
                              'settings': '', 'cites': '', 'yields': '', 'intent': ''})
                continue
            needs.append(_record(soc, var, op, pin))
    missing = [n for n in needs if n['verdict'] != 'fits']
    return {'viable': not missing, 'needs': needs, 'missing': missing}


def header(soc, reqs, pins, reserved=None):
    """the header an isotope is embedded with: only its units, each also under the isotope's own name. One render path
    (hal.custom.render.header), so this and the catalogue cannot drift."""
    a = answer(soc, reqs, pins)
    if not a['viable']:
        raise NeedsRefused('; '.join('%s %s on %s: %s (%s)' % (n['variable'], n['operation'], n['pin'] or '?', n['verdict'], n['why'])
                                     for n in a['missing']))
    keys = []
    for n in a['needs']:
        if n['key'] not in keys:
            keys.append(n['key'])
    aliases = [{'name': n['name'], 'key': n['key'], 'form': 'call'} for n in a['needs']]
    h = RD.header(soc, keys, aliases=aliases, reserved=reserved)
    return dict(h, needs=a['needs'])


def rows(catom, isotope, soc, pin):
    """HalIsotopeNeed rows: the isotope's every pin variable on `pin` (peripheral variables are answered by fit())."""
    from hal.custom import isotopes as ISO
    c = ISO._find(catom, isotope)
    if c is None or not c['requires']:
        return []
    reqs = {v: ops for v, ops in c['requires'].items() if not ISO._peripheral_var(ops)}
    a = answer(soc, reqs, {v: pin for v in reqs})
    return [{'name': '%s:%s:%s:%s:%s' % (catom, isotope, soc, n['pin'], n['operation']), 'catom': catom, 'isotope': isotope, 'soc': soc,
             'pin': n['pin'], 'variable': n['variable'], 'role': n['role'], 'operation': n['operation'], 'need_name': n['name'],
             'unit': n['key'], 'verdict': n['verdict'], 'settings': n['settings'], 'yields': n['yields'], 'cites': n['cites'],
             'why': n['why'], 'proof': ''} for n in a['needs']]
