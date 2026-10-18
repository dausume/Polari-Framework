"""
@module board.custom.button_routes

fgm-5a (MISSION_PROFILE_SOLVER_PLAN.md section 8.5, FIRMWARE_GENERATION_MODULE_PLAN.md section 5b): the read-button catom's
ISOTOPES as REAL Jinja2 templates. hal.c's INT0 button is the hand-written isotope; the other routes of the catalogue
(`cmod.custom.isotope_variants_seeds`) are rendered here, per variant, into one extra file of the generated project:

    route 1  pin-change-interrupt   hal_button_pcint.c   the button on ANY pin that carries a PCINTn function
    route 2  analog-threshold       hal_button_adc.c      the button as a voltage on an ADC pin (pull-up resistor + switch to ground)

Where the template lives (decided here, recorded in the catom README): `board/custom/firmware/uno/catoms/read-button/` - the
section 5b layout (`catoms/<name>/{catom.json, README.md, isotopes/<iso>/{isotope.json, substitutions.json, template.c.j2}}`)
kept UNDER `custom/`, because the manifests selftest allows only objects/ custom/ initialData/ as module subfolders; the layout
moves up to `modules/<module>/firmware/` if and when that rule is extended (ed-0). The BOARD module owns it (the UNO's HAL).

Nothing reaches a template as free text: every register, bit and vector comes from the board's own rows - the BoardPin and
SocPin rows (which pin carries which PCINTn), the cited RegisterField rows (PCMSKn.PCINTx, PCICR.PCIEn, PCIFR.PCIFn, the port
bits), the DatasheetFact for the ADC conversion - and goes through the generator's refusing filters (cmod.custom.generator).
Rendering the same knobs twice gives the same bytes (no timestamp in the file).
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CATOMS = os.path.join(HERE, 'firmware', 'uno', 'catoms')
CATOM = 'read-button'
GENERATOR = 'board.custom.button_routes'
BOARD = 'arduino-uno-r3'

#: knob value of `button_route` -> (HAL_BUTTON_ROUTE code, isotope dir, rendered file, catalogue variant)
ROUTES = {'pcint': (1, 'pin-change-interrupt', 'hal_button_pcint.c', 'read-button:pin-change-interrupt'),
          'adc': (2, 'analog-threshold', 'hal_button_adc.c', 'read-button:analog-threshold')}
ROUTE_NAMES = ('int0',) + tuple(ROUTES)
DEFAULT_ADC = {'button_adc_channel': 0, 'adc_press_below_mv': 1500, 'adc_release_above_mv': 3500, 'adc_pullup_ohms': 10000}
#: the UNO's ADC reference: AVcc = 5 V (uno_facts adc.conversion_result: "the firmware reads channel 0 with REFS0 = AVcc (5 V on the UNO)")
VREF_MV = 5000


class RouteRefused(ValueError):
    pass


def template_path(route):
    return 'read-button/isotopes/%s/template.c.j2' % ROUTES[route][1]


def isotope_dir(route):
    return os.path.join(CATOMS, CATOM, 'isotopes', ROUTES[route][1])


def _rows():
    from board.custom import board_object as bo
    return bo.rows_for(BOARD)


def _field(register, field):
    from board.custom.register_fields_atmega328p import FIELDS
    f = next((x for x in FIELDS if x['register'] == register and x['field'] == field), None)
    if f is None:
        raise RouteRefused('no cited RegisterField row %s.%s' % (register, field))
    return f


def _cite(register, field):
    try:
        f = _field(register, field)
    except RouteRefused:
        # the cited RegisterField set holds ports B and D only: a port C pin is said to be uncited, never given a made-up page
        return '%s.%s - no cited RegisterField row (the set covers ports B and D); same register layout as ports B / D, DS40002061B 14.4 - page not re-read' % (register, field)
    return '%s.%s - ATmega328P DS40002061B %s' % (register, field, f['page_table'])


def _pin(number):
    """Arduino pin number (2..13 = D2..D13, 14..19 = A0..A5 as digital) -> (BoardPin row, SocPin row)."""
    if not 2 <= int(number) <= 19:
        raise RouteRefused('button_pin %s: D2..D13 or 14..19 (A0..A5 as digital); D0/D1 are the USB serial line' % number)
    canonical = 'D%d' % number if number <= 13 else 'A%d' % (number - 14)
    r = _rows()
    bp = next((p for p in r['pins'] if p['canonical'] == canonical), None)
    sp = next((s for s in r['soc_pins'] if bp and s['pin'] == bp['soc_pin']), None)
    if bp is None or sp is None:
        raise RouteRefused('the board has no pin %s with a SoC pin row' % canonical)
    return bp, sp


def pcint_plan(number):
    """Everything the pin-change route needs for the pin, from the rows: -> dict (the template's context part)."""
    bp, sp = _pin(number)
    fns = json.loads(sp['functions_json'])
    pc = next((f for f in fns if f.startswith('PCINT')), None)
    if pc is None:
        raise RouteRefused('%s (%s) carries no PCINTn function in its SocPin row (%s): it cannot raise a pin-change interrupt'
                           % (bp['canonical'], sp['pin'], ', '.join(fns)))
    from board.custom.register_fields_atmega328p import FIELDS
    mask = next((f for f in FIELDS if f['field'] == pc and f['register'].startswith('PCMSK')), None)
    if mask is None:
        raise RouteRefused('no PCMSKn.%s RegisterField row' % pc)
    bank = int(mask['register'][-1])
    port = sp['port']
    pcie, pcif = _field('PCICR', 'PCIE%d' % bank), _field('PCIFR', 'PCIF%d' % bank)
    return {'pin_name': bp['canonical'], 'soc_pin': sp['pin'], 'port': port, 'bit': int(sp['bit']), 'pin_bit': sp['pin'],
            'pin_reg': 'PIN' + port, 'ddr_reg': 'DDR' + port, 'port_reg': 'PORT' + port,
            'mask_reg': mask['register'], 'mask_bit': mask['field'], 'enable_reg': 'PCICR', 'enable_bit': pcie['field'],
            'flag_reg': 'PCIFR', 'flag_bit': pcif['field'], 'vector': 'PCINT%d_vect' % bank,
            'cites': [_cite(mask['register'], mask['field']), _cite('PCICR', pcie['field']), _cite('PCIFR', pcif['field']),
                      _cite('PORT' + port, 'PORT%s%d' % (port, sp['bit'])), _cite('DDR' + port, 'DD%s%d' % (port, sp['bit'])),
                      _cite('PIN' + port, 'PIN%s%d' % (port, sp['bit']))]}


def counts_of(mv):
    """ADC = Vin * 1024 / Vref (DS40002061B 24.7 p.256), rounded down."""
    return int(mv) * 1024 // VREF_MV


def adc_plan(channel, press_below_mv, release_above_mv, pullup_ohms):
    if not 0 <= int(channel) <= 5:
        raise RouteRefused('button_adc_channel %s: the UNO has A0..A5' % channel)
    if not 0 < int(press_below_mv) < int(release_above_mv) < VREF_MV:
        raise RouteRefused('adc_press_below_mv %s / adc_release_above_mv %s: need 0 < press < release < %d mV (the press threshold sits '
                           'below the release one - that gap is the hysteresis)' % (press_below_mv, release_above_mv, VREF_MV))
    if not 1000 <= int(pullup_ohms) <= 100000:
        raise RouteRefused('adc_pullup_ohms %s: 1 kohm..100 kohm (the ADC is specified for a source impedance of about 10 kohm or less)' % pullup_ohms)
    number = 14 + int(channel)
    bp, sp = _pin(number)
    port = sp['port']
    from board.custom.uno_facts import SEED_UNO_FACTS
    fact = next(x for x in SEED_UNO_FACTS if x['fact_key'] == 'adc.conversion_result')
    return {'pin_name': bp['canonical'], 'soc_pin': sp['pin'], 'channel': int(channel), 'port': port, 'bit': int(sp['bit']), 'pin_bit': sp['pin'],
            'ddr_reg': 'DDR' + port, 'port_reg': 'PORT' + port, 'didr_bit': 'ADC%dD' % int(channel), 'vref_mv': VREF_MV,
            'pullup_ohms': int(pullup_ohms), 'press_below_mv': int(press_below_mv), 'release_above_mv': int(release_above_mv),
            'press_below_counts': counts_of(press_below_mv), 'release_above_counts': counts_of(release_above_mv),
            'cites': ['adc.conversion_result: %s - ATmega328P DS40002061B %s' % (fact['value'], fact['page_table']),
                      'DIDR0 - ATmega328P DS40002061B 24.9.5 DIDR0, p.260-261 (board.custom.register_profile)',
                      'ADMUX / ADCSRA: DS40002061B chapter 24 (the exact register pages were not re-read here)']}


def _knob_text(knobs, route):
    keys = ('button_pin', 'debounce_ms') if route == 'pcint' else tuple(DEFAULT_ADC) + ('debounce_ms',)
    return ', '.join('%s=%s' % (k, knobs.get(k, DEFAULT_ADC.get(k))) for k in keys)


def plan(route, knobs):
    """The route's typed context (what the template may use) from the resolved knobs."""
    if route == 'pcint':
        return pcint_plan(int(knobs['button_pin']))
    if route == 'adc':
        return adc_plan(knobs.get('button_adc_channel', DEFAULT_ADC['button_adc_channel']),
                        knobs.get('adc_press_below_mv', DEFAULT_ADC['adc_press_below_mv']),
                        knobs.get('adc_release_above_mv', DEFAULT_ADC['adc_release_above_mv']),
                        knobs.get('adc_pullup_ohms', DEFAULT_ADC['adc_pullup_ohms']))
    raise RouteRefused('button route %r: %s' % (route, ' | '.join(ROUTE_NAMES)))


def check(route, knobs):
    """Raise RouteRefused (naming why) when the route cannot be built for these knobs - used by variants.resolve."""
    plan(route, knobs)


def render(route, knobs):
    """-> {'file', 'text', 'template', 'template_sha256', 'common_sha256', 'generator', 'cites'}: the route's C file for these knobs."""
    from cmod.custom.generator import env as E
    code, iso, fname, _variant = ROUTES[route]
    p = plan(route, knobs)
    tpl = template_path(route)
    ctx = dict(p, file=fname, route_code=code, banner={'generator': GENERATOR, 'template': 'catoms/' + tpl,
                                                       'isotope': iso, 'knobs': _knob_text(knobs, route), 'cites': p['cites']})
    text = E.render(tpl, ctx, templates_dir=CATOMS).decode()
    return {'file': fname, 'text': text, 'template': 'board/custom/firmware/uno/catoms/' + tpl, 'generator': GENERATOR,
            'template_sha256': E.template_sha(tpl, CATOMS), 'common_sha256': E.template_sha('read-button/_common.j2', CATOMS),
            'cites': p['cites'], 'plan': p}


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()
