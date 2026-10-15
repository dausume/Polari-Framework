"""
@module cmod.custom.pin_config_legacy

The PRE-fgm-0 Python emitters of pin_config.h/.c, kept verbatim for ONE release behind `POLARI_GLUE_LEGACY=1`
(see cmod.custom.glue_legacy) so the template path can be diffed against them byte for byte. Not the default.
"""
from cmod.custom.pin_config_gen import GenRefused, _comment


def _render_h(plan, defines, solution_name, graph, board):
    out = [_comment('pin_config.h — the pin claims\' register/bit facts, as #defines pin_config.c uses.', solution_name, graph, board),
           '#ifndef POLARI_PIN_CONFIG_H', '#define POLARI_PIN_CONFIG_H', '']
    if defines:
        out.append('/* one #define per claimed pin\'s register/bit fact pin_config.c uses — derived from the SocPin + ')
        out.append(' * RegisterField rows (board.custom.hardware_chain), never a bare bit number written below. */')
        for macro, value, why in defines:
            out.append('#define %-32s %-8s /* %s */' % (macro, value, why))
        out.append('')
    out += ['void pin_config_init(void);', '', '#endif /* POLARI_PIN_CONFIG_H */', '']
    return ('\n'.join(out) + '\n').encode()


def _render_c(plan, solution_name, graph, board):
    out = [_comment('pin_config.c — pin_config_init(): the fixed init order (DDR, PORT, EICRA, EIFR, EIMSK, PCMSKx, '
                     'PCICR); sei() stays in main(), after every init, never here.', solution_name, graph, board),
           '#include <avr/io.h>', '#include <stdint.h>', '', '#include "pin_config.h"', '',
           'void pin_config_init(void)', '{']
    if not plan:
        out.append('    /* this solution\'s claims produced no GPIO / external-interrupt / pin-change settings */')
    for item in plan:
        rs, regname, fields = item['register_setting'], item['regname'], item['fields']
        out.append('    /* %s = %s (write_mask %s)' % (rs['name'], rs['value_bits'], rs['write_mask']))
        for f in fields:
            claim = f['pin_claim'] or f['peripheral_claim']
            out.append('     *   %-8s = %-5s %s' % (f['field'], f['value'], '— %s · claim %s · task %s · rule %s'
                        % (f['meaning'], claim, f['task'], f['rule'])))
        out.append('     */')
        access_set = {f['access'] for f in fields}
        value_terms = ['((uint8_t)0x%02X << %s)' % (f['value_int'], f['bit_macro']) for f in fields]
        mask_terms = ['((uint8_t)0x%02X << %s)' % (f['width_mask'], f['bit_macro']) for f in fields]
        value_expr = ' | '.join(value_terms)
        mask_expr = ' | '.join(mask_terms)
        lhs = fields[0]['reg_macro']
        if access_set == {'w1c'}:
            out.append('    %s = (uint8_t)(%s);   /* plain write (access w1c): writing a one CLEARS that pending flag; a' % (lhs, value_expr))
            out.append('                                    read-modify-write would also clear every OTHER pending flag */')
        elif 'w1c' not in access_set:
            out.append('    %s = (uint8_t)((%s & (uint8_t)~(%s)) | (%s));   /* bits outside write_mask %s keep the chip\'s' % (lhs, lhs, mask_expr, value_expr, rs['write_mask']))
            out.append('                                    reset value */')
        else:
            raise GenRefused('%s mixes w1c with rw fields in one register — not generated this slice' % rs['name'])
        out.append('')
    if out[-1] == '':
        out.pop()
    out += ['}', '']
    return ('\n'.join(out) + '\n').encode()
