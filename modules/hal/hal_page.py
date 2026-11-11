"""
@module hal.hal_page

/display/hal — the HAL review page (hal-0): what the generalized HAL generates on each chip, and EXACTLY how — every step, the
data each step read and where it came from, the code at each level of abstraction, the cross-checks, and the final header line by
line (the user, 2026-11-11). Configured tables only (no raw JSON). A link opens it on one unit, e.g. from a finalized Bench
Simulation: /display/hal?tab=atmega328p&unit=atmega328p:gpio.set_high:PB5 (`scope_query` seeds the `unit` scope from the URL).
"""
from polariApiServer.module_pages_seed import _page, _row, _tab, _table
from hal.custom import soc_rules as SR

_U = '/api/hal/units/{scope:unit}'
_CODE = 'c_text:code'


def _soc_rows(soc):
    title = SR.RULES[soc]['title']
    return [
        _row(0, [_table('hal-units-%s' % soc, 0, 12, 'Generated units on the %s (click one to see how it was made)' % title, 'HalCodeUnit',
                        columns='operation,pin,status,mechanisms,c_text,why', column_formats=_CODE, max_height=420,
                        data_path='/api/hal/socs/%s/units' % soc, select_field='key', select_scope='unit', selected_value='{scope:unit}',
                        description='One row = one generalized HAL operation on one pin of this chip. status: resolved (C generated), '
                                    'unsupported (the chip has no register for it, said why), undetermined (the cited tables do not reach it '
                                    'yet). mechanisms = how each register write is done (port-mapped bit, set/clear alias, read-modify-write ...).')]),
        _row(1, [_table('hal-levels-%s' % soc, 0, 12, 'The code at each level of abstraction', 'HalCodeUnit',
                        columns='level,layer,code,what,source', column_formats='code:code', data_path=_U + '?view=levels',
                        empty_text='Pick a unit above.',
                        description='Top to bottom: the operation an isotope calls, the board pin, the chip pin, each register binding, '
                                    'the access mechanism chosen, the C statement, the finished macro, and where it lands in the header.')]),
        _row(2, [_table('hal-steps-%s' % soc, 0, 12, 'Generation steps (inputs, rule, output, and where the data came from)',
                        'HalGenerationStep', columns='index,step,title,inputs,rule,output,source,cite', data_path=_U + '?view=steps',
                        empty_text='Pick a unit above.', max_height=520,
                        description='Every step the generator took for this unit, in order. source = the module the data was read from; '
                                    'cite = the datasheet / manual place behind it. Use it to debug why the code came out as it did.')]),
        _row(3, [_table('hal-bindings-%s' % soc, 0, 12, 'Register bindings', 'HalBinding',
                        columns='part,purpose,register,field,bit_lo,bit_hi,value,access,address,space,mechanism,c_text,cite',
                        column_formats=_CODE, data_path=_U + '?view=bindings', empty_text='Pick a unit above.')]),
        _row(4, [_table('hal-checks-%s' % soc, 0, 12, 'Cross-checks against a second source', 'HalCrossCheck',
                        columns='subject,first,first_source,second,second_source,result,why', data_path=_U + '?view=checks',
                        empty_text='Pick a unit above.',
                        description='Existing HALs and vendor headers as cross-references: pass / fail when both sources are compared '
                                    'here; recorded when the comparison was made as the facts were read.')]),
    ]


def _header_rows(soc):
    return [_row(0, [_table('hal-header-%s' % soc, 0, 12, 'polari_hal_%s.h — the final generated header, line by line' % soc, 'HalCodeUnit',
                            columns='line,text,unit,step', column_formats='text:code', data_path='/api/hal/socs/%s/header' % soc,
                            max_height=640, description='Every resolved unit of the chip. unit = the unit a line belongs to (its trace is on '
                                                        'the chip tab), step = the generation step that wrote it.')])]


def _isotope_rows():
    rows = [_row(0, [_table('hal-isotopes', 0, 12, 'Isotopes and what they require of the HAL (click one to see where it fits)', 'HalCodeUnit',
                            columns='catom,isotope,requires,%s' % ','.join('%s_fits' % soc for soc in SR.SOCS), data_path='/api/hal/isotopes',
                            select_field='key', select_scope='isotope', selected_value='{scope:isotope}',
                            description='An isotope is one way of doing a catom\'s job. It fits a pin when every HAL operation it requires resolves '
                                        'on that chip, so one isotope can run on several boards. "not written against the HAL yet" = it still names '
                                        'registers directly.')])]
    for i, soc in enumerate(SR.SOCS, 1):
        rows.append(_row(i, [_table('hal-isotope-fit-%s' % soc, 0, 12, 'Where it fits on the %s' % SR.RULES[soc]['title'], 'HalCodeUnit',
                                    columns='pin,verdict,missing,why', data_path='/api/hal/isotopes/{scope:isotope}/fit?soc=%s' % soc,
                                    empty_text='Pick an isotope above.')]))
    return rows


SEED_HAL_PAGE_DISPLAYS = [
    _page('hal', 'hal',
          'The generalized HAL: chip-independent operations, how each chip binds them to registers, the access mechanisms that decide '
          'how the C is written (port-mapped vs memory-mapped, set/clear aliases, routing matrices), and the exact steps behind every '
          'generated line.',
          'HalOperation', [], title='HAL',
          tabs=[_tab(soc, SR.RULES[soc]['title'], _soc_rows(soc)) for soc in SR.SOCS]
               + [_tab('%s-header' % soc, '%s header' % soc, _header_rows(soc)) for soc in SR.SOCS]
               + [_tab('isotopes', 'Isotope fit', _isotope_rows())]
               + [_tab('operations', 'Operations', [_row(0, [_table('hal-operations', 0, 12, 'HAL operations (the generalized vocabulary)',
                                                                    'HalOperation', columns='name,title,role,action,setup,returns,c_name,intent,basis')])]),
                  _tab('mechanisms', 'Access mechanisms', [_row(0, [_table('hal-mechanisms', 0, 12, 'Access mechanisms (data that drives code generation)',
                                                                           'HalAccessMechanism',
                                                                           columns='name,title,kind,meaning,selects_when,isr_safe,chips,implemented,cite')])])],
          scope_query=['unit', 'isotope']),
]
