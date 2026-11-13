"""
@module hal.custom.render

THE FINISHED HAL CODE, at every level of abstraction (hal-0; the user 2026-11-11: "HAL specific pages, which can be used when
running finalized Bench Simulations to show the exact rendered code at different levels of abstractions and the final code").

  levels(unit_result)          -> rows, top to bottom: the operation an isotope calls, the board pin, the chip pin, each register
                                  binding (register / field / bit / value), its access mechanism, its C statement, the macro, and
                                  where the macro lands in the final header. Each row says where its content came from.
  header(soc, keys)            -> {name, text, sha256, lines[], units[]}: the generated header for EXACTLY the given units
                                  (soc:operation:pin keys: the ones a firmware's isotopes require, hal.custom.project) — every
                                  line carries the unit and the generation step it came from. Never the whole chip (hal-1).
  header_lines(header)         -> one row per line of the file (line, text, unit, step), for a line-by-line page table.

The header is plain C a normal build compiles (RULE 2): avr-libc names on the AVR, volatile address casts on the ESP32-C3. It
names its own sources and the digest of every unit's trace, so the file says how it was made.
"""
import hashlib
import re

from hal.custom import generate as G
from hal.custom import soc_rules as SR

SPDX = 'GPL-3.0-or-later'
FIRST = ('operation', 'board-pin', 'soc-pin')


def levels(res):
    u = res['unit']
    if not u or u.get('status') != 'resolved':
        return [{'level': 0, 'layer': 'refused', 'code': '', 'what': (u or {}).get('why', ''), 'source': ''}]
    steps = {s['step']: s for s in res['steps'] if s['step'] in FIRST}
    rows = [{'level': 1, 'layer': 'operation (what an isotope calls)', 'code': '%s();   /* %s */' % (u['macro'], u['operation']),
             'what': steps['operation']['output'], 'source': steps['operation']['source']}]
    if 'board-pin' in steps:
        rows.append({'level': 2, 'layer': 'board pin', 'code': '%s -> %s' % (u['board_pin'], u['pin']), 'what': steps['board-pin']['output'],
                     'source': '%s; %s' % (steps['board-pin']['source'], steps['board-pin']['cite'])})
    rows.append({'level': 3, 'layer': 'chip pin', 'code': u['pin'], 'what': steps['soc-pin']['output'],
                 'source': '%s; %s' % (steps['soc-pin']['source'], steps['soc-pin']['cite'])})
    for b in res['bindings']:
        bits = 'bit %d' % b['bit_lo'] if b['bit_lo'] == b['bit_hi'] else 'bits %d-%d' % (b['bit_hi'], b['bit_lo'])
        rows.append({'level': 4, 'layer': 'register binding %d' % b['part'],
                     'code': '%s.%s (%s)%s @ %s' % (b['register'], b['field'], bits, ' = %s' % b['value'] if b['value'] else '', b['address']),
                     'what': b['purpose'], 'source': '%s; %s' % (SR.fields_source(u['soc']), b['cite'])})
        rows.append({'level': 5, 'layer': 'access mechanism %d' % b['part'], 'code': b['mechanism'],
                     'what': 'chosen from access %s, %s space' % (b['access'], b['space']), 'source': 'hal.custom.mechanisms'})
        rows.append({'level': 6, 'layer': 'C statement %d' % b['part'], 'code': b['c_text'], 'what': '', 'source': 'hal.custom.mechanisms template'})
    vec = [st for st in res['steps'] if st['step'] == 'vector']
    if vec:
        rows.append({'level': 4, 'layer': 'interrupt vector', 'code': vec[0]['output'], 'what': vec[0]['inputs'],
                     'source': '%s; %s' % (vec[0]['source'], vec[0]['cite'])})
    rows.append({'level': 7, 'layer': 'macro (generated C)', 'code': u['c_text'] + ('\n' + u['c_text_init'] if u.get('c_text_init') else ''),
                 'what': ('guarded; the _INIT form is unguarded for init code' if u['guarded'] else 'no guard needed'),
                 'source': 'hal.custom.generate, steps sha256 %s' % u['steps_sha256'][:12]})
    hdr = header(u['soc'], [u['key']])
    line = next((ln for ln in hdr['lines'] if ln['unit'] == u['key'] and ln['text'].startswith('#define')), None)
    rows.append({'level': 8, 'layer': 'final file', 'code': '%s line %d' % (hdr['name'], line['line'] if line else 0),
                 'what': 'where it lands in polari_hal_%s.h, which holds ONLY the units a firmware requires; this unit is in it only '
                         'when an isotope of that firmware requires it (the Firmware headers tab)' % u['soc'], 'source': 'hal.custom.render.header'})
    return rows


def _guard_prelude(soc):
    if soc != 'esp32c3':
        return []
    return ['#ifndef POLARI_HAL_ATOMIC',
            '/* %s */' % SR.RULES[soc]['c']['guard_why'],
            '#define POLARI_HAL_ATOMIC(stmt) do { stmt } while (0)',
            '#endif']


def header(soc, keys, aliases=None):
    name = 'polari_hal_%s.h' % soc
    guard = 'POLARI_HAL_%s_H' % soc.upper()
    units, refused = [], []
    for k in keys:
        p = G.parse_key(k)
        res = G.unit(*p) if p and p[0] == soc else None
        if res and res['unit']['status'] == 'resolved':
            units.append(res)
        else:
            refused.append((k, (res or {}).get('unit', {}).get('why', 'not a unit key of %s' % soc) if res else 'not a unit key of %s' % soc))
    includes = []
    for r in units:
        for inc in r['unit']['includes'].split():
            if inc not in includes:
                includes.append(inc)
    out = []   # (text, unit, step)

    def put(text, unit='', step=''):
        out.append((text, unit, step))
    put('/* SPDX-License-Identifier: %s */' % SPDX)
    put('/*')
    put(' * %s - GENERATED by the Polari HAL (hal.custom.render.header); do not edit, regenerate.' % name)
    put(' * Chip: %s. Facts from: %s.' % (SR.RULES[soc]['title'], SR.DOCS[soc]))
    put(' * Every macro below lists its generation trace digest; /display/hal shows each trace step by step.')
    put(' */')
    put('#ifndef %s' % guard)
    put('#define %s' % guard)
    for inc in includes:
        put('#include %s' % inc)
    if soc == 'atmega328p':
        put('#include <stdint.h>')
    for ln in _guard_prelude(soc):
        put(ln, '', 'guard')
    for r in units:
        u = r['unit']
        put('')
        put('/* %s on %s%s: %s */' % (u['operation'], u['pin'], ' (%s)' % u['board_pin'] if u['board_pin'] else '',
                                      '; '.join('%s.%s via %s' % (b['register'], b['field'], b['mechanism']) for b in r['bindings'])), u['key'], 'binding')
        put('/*   steps sha256 %s */' % u['steps_sha256'], u['key'], 'macro')
        put(u['c_text'], u['key'], 'macro')
        if u.get('c_text_init'):
            put(u['c_text_init'], u['key'], 'context')
    for k, why in refused:
        put('')
        put('/* not generated: %s - %s */' % (k, why), k, 'refused')
    # hal-3a: ROLE names (the firmware's own words: HAL_LED_SET_HIGH) pointing at the unit that plays them on this build's pin
    # (HAL_GPIO_SET_HIGH_PD6). The template code calls the role; which pin, which register, is the header's business only.
    have = {r['unit']['key']: r['unit'] for r in units}
    roles = [a for a in (aliases or []) if a['key'] in have]
    if roles:
        put('')
        put('/* roles: what the firmware calls -> the unit above that does it on this build\'s pin */')
        for a in roles:
            u = have[a['key']]
            m = re.match(r'#define %s(\([^)]*\))' % re.escape(u['macro']), u['c_text'])
            params = m.group(1) if m else ''   # hal-3b: a role passes the unit's own arguments through (HAL_PWM_SET_DUTY(level))
            if a.get('form') == 'symbol' or not m:
                put('#define %s %s' % (a['name'], u['macro']), u['key'], 'role')
            elif a.get('form') == 'init' and u.get('c_text_init'):
                put('#define %s%s %s_INIT%s' % (a['name'], params, u['macro'], params), u['key'], 'role')
            else:
                put('#define %s%s %s%s' % (a['name'], params, u['macro'], params), u['key'], 'role')
    put('')
    put('#endif /* %s */' % guard)
    text = '\n'.join(t for t, _, _ in out) + '\n'
    lines = [{'line': i + 1, 'text': t, 'unit': uk, 'step': st} for i, (t, uk, st) in enumerate(out)]
    return {'name': name, 'soc': soc, 'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest(), 'lines': lines,
            'units': [r['unit'] for r in units], 'refused': [{'key': k, 'why': w} for k, w in refused]}
