"""
@module cmod.custom.isotope_variants_eligibility

`eligible(variant, ctx, tier=None)` (iso-0): can this variant be done on this hardware, with this bench, at this runtime tier? Three-valued, never
silently ok: ok | blocked (the reason BY NAME) | undetermined (why we cannot say). The checks:

  part         every part class: on the bench (KitPart rows), not on the bench = blocked, unknown = undetermined
  peripheral   every on-chip block: the board's Peripheral rows (the UNO); a board without them (the ESP32-C3 model) is read from its SocDefinition's
               Zephyr devicetree list where that names the block, else undetermined (a block missing from that list is not proof it is absent)
  pin          every pin profile: a pin carrying the function the kind needs (PinFunction rows on the UNO; GPIO / ADC names on a board whose routing
               is not modelled; everything else undetermined)
  runtime      the variant's minimum tier against the board's RuntimeProfile rows (`level_ok`); with `tier` also that the board offers that tier -
               a refused tier names the profile's own refusal (Zephyr has no AVR port: cited to its arch/ listing)
"""
import fnmatch
import json
import re

from board.custom import soc_functions as SF   # c3pf: kinds on the ESP32-C3 are patterns over its PinFunction names
from cmod.custom.code_interface import LEVEL_ORDER, level_ok

# the functions a pin kind needs when the profile names none (patterns: 'X*' = starts with, else exact)
KIND_FUNCTIONS = {'digital-in': ['GPIO*'], 'digital-out': ['GPIO*'], 'analog-in': ['ADC*'], 'pwm-out': ['OC*'], 'spi-mosi': ['MOSI'],
                  'spi-miso': ['MISO'], 'spi-sck': ['SCK'], 'spi-ss': ['SS'], 'i2c-sda': ['SDA'], 'i2c-scl': ['SCL'], 'uart-rx': ['RXD'],
                  'uart-tx': ['TXD'], 'interrupt-in': ['INT*', 'PCINT*']}
# block kind -> the Peripheral.kind rows that satisfy it (UNO)
_PER_KIND = {'gpio-port': 'gpio-port', 'exint': 'exint', 'pcint': 'pcint', 'adc': 'adc', 'comparator': 'comparator', 'spi': 'spi', 'twi': 'twi',
             'timer-pwm': 'timer', 'usart': 'usart'}
# block kind -> the Zephyr devicetree compatible that names it (a board with no Peripheral rows)
_DTS = {'gpio-port': 'espressif,esp32-gpio', 'adc': 'espressif,esp32-adc', 'spi': 'espressif,esp32-spi', 'twi': 'espressif,esp32-i2c',
        'timer-pwm': 'espressif,esp32-ledc', 'usart': 'espressif,esp32-uart'}
_C3_FUNC = re.compile(r'^(GPIO\d+|ADC\d_CH\d)$')
_CACHE = {}


def _tables():
    if 'tables' not in _CACHE:
        from board.custom import board_object as BO
        _CACHE['tables'] = BO.seed_tables()
    return _CACHE['tables']


def boards():
    return sorted(b['name'] for b in _tables()['BoardDefinition'] if b.get('soc_definition'))


def context(board, tables=None, kit=None):
    """The hardware context of one board, or None when the board is unknown / has no SoC row."""
    t = tables or _tables()
    b = next((x for x in t['BoardDefinition'] if x['name'] == board), None)
    if b is None or not b.get('soc_definition'):
        return None
    soc = next((s for s in t['SocDefinition'] if s['name'] == b['soc_definition']), None)
    if soc is None:
        return None
    per = [p for p in t['Peripheral'] if p['soc'] == soc['name']]
    from board.custom import soc_functions as _SF
    pf = _SF.pin_functions(t, soc['name'])   # c3-derive: stored + derived rows
    pins = [p for p in t['SocPin'] if p['soc'] == soc['name']]
    funcs = {f['function'] for f in pf} or {fn for p in pins for fn in json.loads(p['functions_json'] or '[]')}
    from cmod.custom import isotope_variants as IV
    # c3pf: a SoC's Peripheral rows are COMPLETE when they come from a register snapshot (the UNO) or when a cited fact enumerates the datasheet's peripherals
    lst = next((f for f in t.get('DatasheetFact', []) if f['name'] == '%s:peripherals.list' % soc['name']), None)
    complete = bool(lst) or any(json.loads(p.get('registers_refs_json') or '[]') for p in per)
    return {'board': board, 'soc': soc['name'], 'soc_row': soc, 'peripherals': per, 'pin_functions_modelled': bool(pf), 'functions': funcs,
            'peripherals_complete': complete, 'peripheral_list': lst,
            'dts': json.loads(soc.get('peripherals_json') or '[]') if not per else [],
            'runtime': [r for r in t['RuntimeProfile'] if r['board'] == board], 'kit': kit if kit is not None else IV.kit_rows()}


def _has(ctx, pat):
    return any(fnmatch.fnmatchcase(f, pat) for f in ctx['functions'])


def check_part(part, ctx):
    from cmod.custom import isotope_variants as IV
    r = IV.part_on_bench(part, ctx['kit'])
    if r['on_bench'] is True:
        return {'check': 'part', 'subject': part['class'], 'state': 'ok', 'why': r['why']}
    if r['on_bench'] is False:
        return {'check': 'part', 'subject': part['class'], 'state': 'blocked', 'why': r['why']}
    return {'check': 'part', 'subject': part['class'], 'state': 'undetermined', 'why': r['why']}


def check_peripheral(per, ctx):
    kind = per['kind']
    if ctx['peripherals']:
        want = (SF.PERIPHERAL_KIND.get(ctx['soc']) or _PER_KIND).get(kind)
        hit = next((p for p in ctx['peripherals'] if p['kind'] == want), None)
        if hit is None:
            if not ctx.get('peripherals_complete', True):
                return {'check': 'peripheral', 'subject': kind, 'state': 'undetermined', 'why': 'the %s has no %s block among its Peripheral rows, and those rows are not a complete list - not proof it is absent' % (ctx['soc'], kind)}
            why = 'the %s has no %s block (no Peripheral row of kind %s)' % (ctx['soc'], kind, want)
            if kind == 'comparator' and ctx['soc'] in SF.NO_COMPARATOR:
                why += ': ' + SF.NO_COMPARATOR[ctx['soc']]
            elif ctx.get('peripheral_list'):
                f = ctx['peripheral_list']
                why += ' [cited: %s, %s]' % (f['document'], f['page_table'])
            return {'check': 'peripheral', 'subject': kind, 'state': 'blocked', 'why': why}
        pwm_pats = SF.kind_patterns(ctx['soc'], 'pwm-out') or ['OC*']
        if kind == 'timer-pwm' and not any(_has(ctx, p) for p in pwm_pats):
            return {'check': 'peripheral', 'subject': kind, 'state': 'blocked', 'why': 'no pin of the %s carries a timer output-compare function' % ctx['soc']}
        return {'check': 'peripheral', 'subject': kind, 'state': 'ok', 'why': 'Peripheral row %s (%s)' % (hit['name'], hit.get('chapter') or 'chapter not cited')}
    compat = _DTS.get(kind)
    if compat is None:
        return {'check': 'peripheral', 'subject': kind, 'state': 'undetermined',
                'why': 'the %s has no Peripheral rows and its Zephyr devicetree list names no %s block; absence from that list is not proof it is absent from the silicon' % (ctx['soc'], kind)}
    hit = next((d for d in ctx['dts'] if d.get('compatible') == compat), None)
    if hit:
        return {'check': 'peripheral', 'subject': kind, 'state': 'ok', 'why': 'devicetree node %s (%s) - %s' % (hit['name'], compat, hit.get('cite', ''))}
    return {'check': 'peripheral', 'subject': kind, 'state': 'undetermined', 'why': 'no devicetree node of %s in the %s list; not proof the block is absent' % (compat, ctx['soc'])}


def check_pin(prof, ctx):
    kind = prof['kind']
    own = SF.kind_patterns(ctx['soc'], kind) if SF.has_vocab(ctx['soc']) else None
    if own is not None:   # c3pf: the profile's function names (INT0, OC*, AIN0 ...) are the UNO's; on a PinFunction-vocabulary SoC the KIND names the pattern
        pats, need_all = own, False
    elif prof.get('functions_all'):
        pats, need_all = prof['functions_all'], True
    else:
        pats, need_all = prof.get('functions_any') or KIND_FUNCTIONS.get(kind), False
    if not pats:
        return {'check': 'pin', 'subject': kind, 'state': 'undetermined', 'why': 'no function mapping for pin kind %s' % kind}
    found = [p for p in pats if _has(ctx, p)]
    ok = len(found) == len(pats) if need_all else bool(found)
    if ok:
        return {'check': 'pin', 'subject': kind, 'state': 'ok', 'why': '%s carries %s' % (ctx['soc'], ', '.join(found))}
    if ctx['pin_functions_modelled']:
        return {'check': 'pin', 'subject': kind, 'state': 'blocked', 'why': 'no pin of the %s carries %s (PinFunction rows)' % (ctx['soc'], ' + '.join(pats) if need_all else ' or '.join(pats))}
    return {'check': 'pin', 'subject': kind, 'state': 'undetermined',
            'why': 'the %s\'s pin routing is not modelled as PinFunction rows (a GPIO matrix), so %s cannot be confirmed or refused' % (ctx['soc'], ' or '.join(pats))}


def check_runtime(variant, ctx, tier=None):
    mn = variant.get('minimum_level') or 'bare-c'
    prof = ctx['runtime']
    if not prof:
        return {'check': 'runtime', 'subject': mn, 'state': 'undetermined', 'why': 'no RuntimeProfile rows for %s' % ctx['board']}
    if tier is not None:
        p = next((r for r in prof if r['runtime'] == tier), None)
        if tier not in LEVEL_ORDER:
            return {'check': 'runtime', 'subject': tier, 'state': 'blocked', 'why': '%r is not a tier on the ladder (%s)' % (tier, ' < '.join(LEVEL_ORDER))}
        if p is None:
            return {'check': 'runtime', 'subject': tier, 'state': 'undetermined', 'why': 'no %s RuntimeProfile row for %s' % (tier, ctx['board'])}
        if str(p['supported']) not in ('True', 'true') and p['supported'] is not True:
            return {'check': 'runtime', 'subject': tier, 'state': 'blocked',
                    'why': 'tier %s unavailable on %s: %s%s' % (tier, ctx['board'], p['refusal'], (' [cited: %s]' % p['origin']) if p.get('origin') else '')}
        if not level_ok(mn, tier):
            return {'check': 'runtime', 'subject': tier, 'state': 'blocked', 'why': 'the variant needs tier %s or higher; the chosen tier is %s' % (mn, tier)}
        return {'check': 'runtime', 'subject': tier, 'state': 'ok', 'why': 'RuntimeProfile %s is supported and meets the variant\'s minimum %s' % (p['name'], mn)}
    sup = [r for r in prof if str(r['supported']) in ('True', 'true') or r['supported'] is True]
    if any(level_ok(mn, r['runtime']) for r in sup):
        r = next(r for r in sup if level_ok(mn, r['runtime']))
        return {'check': 'runtime', 'subject': mn, 'state': 'ok', 'why': 'minimum tier %s is met by %s (supported)' % (mn, r['name'])}
    named = next((r for r in prof if r['runtime'] == mn), None)
    why = 'no supported tier at or above %s on %s' % (mn, ctx['board'])
    if named is not None and named['refusal']:
        why = 'tier %s unavailable on %s: %s%s' % (mn, ctx['board'], named['refusal'], (' [cited: %s]' % named['origin']) if named.get('origin') else '')
    return {'check': 'runtime', 'subject': mn, 'state': 'blocked', 'why': why}


def eligible(variant, ctx, tier=None):
    """-> {state, summary, checks[], blocked_by[]}; `variant` is a catalogue row dict (declared fields)."""
    from cmod.custom.isotope_variants import _j
    checks = [check_runtime(variant, ctx, tier)]
    checks += [check_pin(p, ctx) for p in _j(variant.get('profiles_json'), [])]
    checks += [check_peripheral(p, ctx) for p in _j(variant.get('peripherals_json'), [])]
    checks += [check_part(p, ctx) for p in _j(variant.get('parts_json'), [])]
    blocked = [c for c in checks if c['state'] == 'blocked']
    unk = [c for c in checks if c['state'] == 'undetermined']
    state = 'blocked' if blocked else ('undetermined' if unk else 'ok')
    if blocked:
        summary = 'blocked: ' + '; '.join('%s %s - %s' % (c['check'], c['subject'], c['why']) for c in blocked)
    elif unk:
        summary = 'undetermined: ' + '; '.join('%s %s - %s' % (c['check'], c['subject'], c['why']) for c in unk)
    else:
        summary = 'ok on %s: every pin kind, block, part and the runtime tier are available' % ctx['board']
    return {'state': state, 'summary': summary, 'checks': checks, 'blocked_by': [c['check'] + ':' + c['subject'] for c in blocked]}
