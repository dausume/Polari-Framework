"""
@module cmod.custom.generator.pin_context

pin_config.h / pin_config.c's CONTEXT: pin_config_gen's register-setting plan (plan_from_rows — the claims already turned into
bits, fixed init order) normalized for avr/pin_config.{h,c}.j2. The derivation stays in pin_config_gen; this only shapes it.
Value/mask terms are composed HERE from validated pieces (c_hex of an int, c_ident of a macro name); the template filters again.
"""
from cmod.custom.generator.filters import c_hex, c_ident

GENERATOR = 'cmod.custom.pin_config_gen'


def _banner(solution_name, graph, board):
    return {'generator': GENERATOR, 'solution': solution_name, 'graph': graph, 'board': board}


def h_context(defines, solution_name, graph, board):
    return {'banner': _banner(solution_name, graph, board),
            'defines': [{'macro': m, 'value': v, 'why': w} for m, v, w in defines]}


def c_context(plan, modes, solution_name, graph, board):
    """modes: [ 'rw' | 'w1c' ] per plan item (pin_config_gen refuses a mix before this is called)."""
    items = []
    for item, mode in zip(plan, modes):
        rs, fields = item['register_setting'], item['fields']
        vt = ' | '.join('((uint8_t)%s << %s)' % (c_hex(f['value_int']), c_ident(f['bit_macro'])) for f in fields)
        mt = ' | '.join('((uint8_t)%s << %s)' % (c_hex(f['width_mask']), c_ident(f['bit_macro'])) for f in fields)
        items.append({'name': rs['name'], 'value_bits': rs['value_bits'], 'write_mask': rs['write_mask'], 'mode': mode,
                      'lhs': fields[0]['reg_macro'], 'value_expr': vt, 'mask_expr': mt, 'fields': fields})
    return {'banner': _banner(solution_name, graph, board), 'plan': items}
