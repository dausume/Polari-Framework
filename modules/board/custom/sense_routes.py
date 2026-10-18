"""
@module board.custom.sense_routes

fgm-5b (MISSION_PROFILE_SOLVER_PLAN.md section 16): the sense-led-line catom's ISOTOPES as REAL Jinja2 templates, the sibling of board.custom.button_routes (fgm-5a) and built the same way.
hal.c's INT1 sense (D3, any edge) is the hand-written isotope; the other routes of the catalogue (`cmod.custom.isotope_variants_seeds`, job sense-led-line) are rendered here, per variant, into one
extra file of the generated project:

    route 1  gpio-poll              hal_sense_poll.c    the sense pin read in the main loop, once per pass (hal_sense_read samples it and counts a change)
    route 2  pin-change-interrupt   hal_sense_pcint.c   the sense pin on ANY pin that carries a PCINTn function (an ISR counts and stamps every edge)

Both supply the SAME two functions hal.h declares for a sense pin (hal_sense_init / hal_sense_read), so the app (apps/button_clock.c) is unchanged, and switch hal.c's INT1 block off with
HAL_SENSE_ROUTE (board_config.h; undefined = 0, so every existing variant's bytes are unchanged). The layout is `catoms/sense-led-line/{catom.json, README.md, _common.j2,
isotopes/<iso>/{isotope.json, substitutions.json, template.c.j2}}` under board/custom/firmware/uno/ (the manifests rule allows only objects/ custom/ initialData/ as module subfolders).

Nothing reaches a template as free text: every register, bit and vector comes from the board's own rows (BoardPin / SocPin / the cited RegisterField rows) through the same helpers fgm-5a uses,
and the generator's refusing filters. Rendering the same knobs twice gives the same bytes (no timestamp).
"""
import hashlib
import os

from board.custom import button_routes as BR

CATOMS = BR.CATOMS
CATOM = 'sense-led-line'
GENERATOR = 'board.custom.sense_routes'
BOARD = BR.BOARD
RouteRefused = BR.RouteRefused

#: knob value of `sense_route` -> (HAL_SENSE_ROUTE code, isotope dir, rendered file, catalogue variant)
ROUTES = {'poll': (1, 'gpio-poll', 'hal_sense_poll.c', 'sense-led-line:gpio-poll'),
          'pcint': (2, 'pin-change-interrupt', 'hal_sense_pcint.c', 'sense-led-line:pin-change-interrupt')}
ROUTE_NAMES = ('int1',) + tuple(ROUTES)


def template_path(route):
    return '%s/isotopes/%s/template.c.j2' % (CATOM, ROUTES[route][1])


def isotope_dir(route):
    return os.path.join(CATOMS, CATOM, 'isotopes', ROUTES[route][1])


def _check_pin(number):
    if not 2 <= int(number) <= 19:
        raise RouteRefused('sense_pin %s: D2..D13 or 14..19 (A0..A5 as digital); D0/D1 are the USB serial line' % number)


def poll_plan(number):
    """Everything the polled route needs for the pin, from the rows: -> dict (the template's context part)."""
    _check_pin(number)
    bp, sp = BR._pin(int(number))
    port = sp['port']
    return {'pin_name': bp['canonical'], 'soc_pin': sp['pin'], 'port': port, 'bit': int(sp['bit']), 'pin_bit': sp['pin'], 'pin_reg': 'PIN' + port, 'ddr_reg': 'DDR' + port,
            'cites': [BR._cite('DDR' + port, 'DD%s%d' % (port, sp['bit'])), BR._cite('PIN' + port, 'PIN%s%d' % (port, sp['bit']))]}


def pcint_plan(number):
    _check_pin(number)
    return BR.pcint_plan(int(number))


def _knob_text(knobs):
    return ', '.join('%s=%s' % (k, knobs.get(k)) for k in ('sense_pin',))


def plan(route, knobs):
    """The route's typed context (what the template may use) from the resolved knobs."""
    if route == 'poll':
        return poll_plan(int(knobs['sense_pin']))
    if route == 'pcint':
        return pcint_plan(int(knobs['sense_pin']))
    raise RouteRefused('sense route %r: %s' % (route, ' | '.join(ROUTE_NAMES)))


def check(route, knobs):
    """Raise RouteRefused (naming why) when the route cannot be built for these knobs - used by variants.resolve."""
    plan(route, knobs)


def render(route, knobs):
    """-> {'file', 'text', 'template', 'template_sha256', 'common_sha256', 'generator', 'cites', 'plan'}: the route's C file for these knobs."""
    from cmod.custom.generator import env as E
    code, iso, fname, _variant = ROUTES[route]
    p = plan(route, knobs)
    tpl = template_path(route)
    ctx = dict(p, file=fname, route_code=code, banner={'generator': GENERATOR, 'template': 'catoms/' + tpl, 'isotope': iso, 'knobs': _knob_text(knobs), 'cites': p['cites']})
    text = E.render(tpl, ctx, templates_dir=CATOMS).decode()
    return {'file': fname, 'text': text, 'template': 'board/custom/firmware/uno/catoms/' + tpl, 'generator': GENERATOR,
            'template_sha256': E.template_sha(tpl, CATOMS), 'common_sha256': E.template_sha('%s/_common.j2' % CATOM, CATOMS), 'cites': p['cites'], 'plan': p}


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()
