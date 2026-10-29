"""
@module cmod.custom.hal_nocode

THE HAL IN NO-CODE (hsp-3c, HARDWARE_SYSTEM_PINS_PLAN.md section 7 "From no-code": "the no-code editor offers a catom's variables as SLOTS filtered by role
... choosing one writes the variable's bench value, which makes the assertion, which draws it and generates the firmware value"). A firmware variant's
Catom variables drawn as ONE no-code solution of category `hal` (`hal-<variant>`): one `hal-variable` card per variable, read like a form.

It is DECLARATIVE (the `hal` category validator, hwnocode.custom.cross_domain, refuses every compute and runtime kind). The rows are the single source of
truth: `render` draws them; `write_back` turns a card's new `value` into catom_variables.propose (the ONE write path) and refuses an edit to a worked-out
field by name. A card's `options` are its slot: the pins the role may use on this chip that ALSO pass the variant's own rules, accepted first, then
warnings - so a pin picked from the list is a pin the write will keep.
"""
import json

from polariNoCode import graph_builder as GB
from cmod.custom import catom_variables as CV

CATEGORY = 'hal'
SOLUTION_PREFIX = 'hal-'
CLS = 'HalVariableState'
#: worked out on every render - never typed in
DERIVED_FIELDS = ('role', 'scope', 'verdict', 'options', 'why')
_COLS, _COL_W, _ROW_H, _W, _H = 3, 250, 150, 225, 120


def solution_name(variant):
    return SOLUTION_PREFIX + variant


def slot_options(variant, var, vs, variant_rows=None):
    """[{pin (as the variable writes it), verdict, why}] - CV.slots narrowed to the pins the variant's own rules accept too."""
    if var['role'] in CV.NUMBER_ROLES:
        return []
    out = []
    for o in CV.slots(var, vs)['options']:
        pin = CV.board_form(var['soc'], o['pin'], var['c_form'])
        if pin != var['value'] and not CV.propose(variant, {var['variable']: o['pin']}, [dict(v) for v in vs], variant_rows)['ok']:
            continue
        out.append({'pin': pin, 'verdict': o['verdict'], 'why': o['why']})
    return sorted(out, key=lambda o: (CV.VERDICTS.index(o['verdict']), _natural(o['pin'])))


def _natural(pin):
    """D2 < D10 < A0 on the UNO; GPIO2 < GPIO10 on the C3; PB0 < PD1 otherwise."""
    import re
    m = re.match(r'^([A-Z]*?)(\d+)$', pin)
    return ({'D': 0, 'A': 1}.get(m.group(1), 2), m.group(1), int(m.group(2))) if m else (3, pin, 0)


def _options_text(opts):
    return ', '.join('%s%s' % (o['pin'], ' (warning)' if o['verdict'] == 'warning' else '') for o in opts) or 'a number, typed in'


def fields(variant, var, vs, variant_rows=None):
    """The card's fields: `value` authored, the rest worked out."""
    return {'variable': var['variable'], 'value': var['value'], 'role': var['role'], 'scope': var['scope'], 'verdict': var['status'],
            'options': _options_text(slot_options(variant, var, vs, variant_rows)), 'why': var['status_why']}


def render_definition(variant, rows=None, variant_rows=None):
    vs = CV.variables(variant, rows, variant_rows)
    states = []
    for i, v in enumerate(vs):
        f = fields(variant, v, vs, variant_rows)
        f.update(displayName='%s - %s' % (v['variable'], v['role']), derived=False,
                 purpose='%s = %s (%s scope): %s' % (v['variable'], v['value'] or '(none)', v['scope'], v['status']))
        st = GB.node('hal-%s' % v['variable'], CLS, f, outs=[])
        st['stateLocationX'], st['stateLocationY'] = 40 + _COL_W * (i % _COLS), 60 + _ROW_H * (i // _COLS)
        st['shapeType'] = st['stateSvgName'] = 'rectangle'
        st['layerName'] = 'rectangle-layer'
        st['backgroundColor'] = {'accepted': '#00695C', 'warning': '#EF6C00', 'refused': '#C62828'}.get(v['status'], '#9E9E9E')
        st['slotRadius'] = 5
        st['stateSvgWidth'], st['stateSvgHeight'], st['cornerRadius'] = _W, _H, 8
        st['stateSvgRadius'] = None
        st['stateSvgSizeX'] = st['stateSvgSizeY'] = None
        st['runtime'] = ''
        states.append(st)
    d = GB.solution(solution_name(variant), *states)
    d['edgeKind'] = 'none'
    return d


def contract():
    return {'description': 'The named values a firmware variant is built with (its HAL): each pin or number, where it was set, and whether the rules '
                           'accept it. Pick a value from the pins it may use; it is checked and written to the firmware recipe. Declarative: '
                           'nothing here is executed.', 'inputs': [], 'returns': [], 'executionRights': 'definer'}


def render(variant, rows=None, variant_rows=None):
    """The SolutionDefinition ROW dict for one variant's HAL (category 'hal')."""
    name = solution_name(variant)
    return {'name': name, 'function_name': name.replace('-', '_'), 'target_runtime': 'python_backend',
            'definition': json.dumps(render_definition(variant, rows, variant_rows)), 'contract_json': json.dumps(contract()), 'category': CATEGORY}


def validate(definition):
    from hwnocode.custom import cross_domain as CD
    return CD.validate(definition, CATEGORY)


def write_back(definition, variant, rows=None, variant_rows=None):
    """(ok, why, proposal) - the drawing's new values -> catom_variables.propose. Refuses, naming the state: a non-HAL kind, a card for a variable the
    variant does not have, an edit to a worked-out field; then whatever propose refuses (the pin functions, the lifecycle, one pin one role, the
    variant's rules). `proposal` carries the writes for the door to apply; nothing is written here."""
    ok, why = validate(definition)
    if not ok:
        return False, why, {}
    vs = CV.variables(variant, rows, variant_rows)
    by = {v['variable']: v for v in vs}
    edits = {}
    for s in definition.get('stateInstances') or []:
        f = dict(s.get('boundObjectFieldValues') or {})
        name = f.get('variable') or str(s.get('stateName', ''))[len('hal-'):]
        if name not in by:
            return False, 'refused: state %r - %s has no HAL value %r (it has %s)' % (s.get('stateName'), variant, name, ', '.join(by)), {}
        fresh = fields(variant, by[name], vs, variant_rows)
        for k in DERIVED_FIELDS:
            v = f.get(k)
            if v is not None and str(v) not in ('', str(fresh[k])):
                return False, ('refused: state %r - its %s is worked out, never typed in (got %r, it is %r)' % (s.get('stateName'), k, v, fresh[k])), {}
        if 'value' in f and str(f['value']).strip() != by[name]['value']:
            edits[name] = str(f['value']).strip()
    if not edits:
        return True, 'ok: no value changed', {'ok': True, 'results': [], 'variant_rule': '', 'writes': []}
    p = CV.propose(variant, edits, rows, variant_rows)
    if not p['ok']:
        bad = [r for r in p['results'] if r['verdict'] == 'refused']
        text = '; '.join('%s = %s refused: %s' % (r['variable'], r['value'], ' | '.join(r['refusals'])) for r in bad)
        if p['variant_rule'].startswith('refused'):
            text = (text + '; ' if text else '') + p['variant_rule']
        return False, 'refused: ' + (text or p.get('error', '')), p
    return True, 'ok: %s' % ', '.join('%s = %s (%s)' % (r['variable'], r['value'], r['verdict']) for r in p['results']), p
