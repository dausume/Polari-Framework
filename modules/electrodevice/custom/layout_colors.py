"""
@module electrodevice.custom.layout_colors

lay-0: WIRE COLOURS. The convention is a `WireColorScheme` row (the seeded default follows the pin view: red = 5 V and supply, black = GND, a signal wire in the colour the pin view paints
its pin's family); a wire's DERIVED colour comes from its class (ground | power | pin:<label> | default) through the chosen scheme; a person's per-wire override is kept BESIDE it and the
EFFECTIVE colour (override, else derived) is what the drawing and the walkthrough text use. A seeded scheme is never edited in place: copy it, then set colours on the copy (as with score profiles).
"""
import json

from electrodevice.custom import layout_rows as LR
from electrodevice.custom.layout_words import LayoutRefused
from electrodevice.objects.layout._shared import SCHEME_DEFAULT, SEED_WIRE_COLOR_SCHEMES, WIRE_COLOURS

KEYS_FIXED = ('power', 'ground', 'default')


def _scheme(row):
    g = (lambda k, d='': row.get(k, d)) if isinstance(row, dict) else (lambda k, d='': getattr(row, k, d))
    try:
        colors = json.loads(g('colors_json') or '{}')
    except ValueError:
        colors = {}
    return {'name': g('name'), 'display_name': g('display_name') or g('name'), 'description': g('description'), 'seeded': bool(g('seeded', False)), 'copy_of': g('copy_of'),
            'follows': g('follows'), 'colors': colors, 'editable': not bool(g('seeded', False)),
            'edit_words': 'copy it first (wire-colors copy), then set colours on the copy' if g('seeded', False) else 'yours: colours can be set in place'}


def all_schemes(manager=None):
    """{name: scheme dict}: the seeded schemes, then the live rows (a live row of a seeded name never replaces the seeded one)."""
    out = {r['name']: _scheme(r) for r in SEED_WIRE_COLOR_SCHEMES}
    for r in LR.rows(manager, 'WireColorScheme'):
        if r.name not in out:
            out[r.name] = _scheme(r)
    return out


def get_scheme(manager, name=None):
    s = all_schemes(manager)
    name = name or SCHEME_DEFAULT
    if name not in s:
        raise LayoutRefused("no wire colour scheme %r (known: %s)" % (name, ', '.join(sorted(s))), status=404)
    return s[name]


def families_table(manager=None):
    """The pin view's family -> hex (board.custom.pv_families.FALLBACK_HEX), the palette source the seeded scheme must agree with."""
    from board.custom import pv_families as F
    return dict(F.FALLBACK_HEX)


def derived_colour(scheme, cls, manager=None):
    """The scheme's colour NAME for a wire class: 'ground' | 'power' | 'pin:<label>' (via the pin's family) | anything else -> default."""
    c = scheme['colors']
    if cls in ('ground', 'power'):
        return c.get(cls) or c.get('default', 'grey')
    if cls.startswith('pin:'):
        from electrodevice.custom import layout_sources as S
        fam, _hex = S.pin_family(manager, cls[4:])
        return c.get(fam) or c.get('default', 'grey')
    return c.get('default', 'grey')


def colour_wires(wires, scheme, overrides=None, manager=None):
    """Add `colour` (derived), `colour_override` ('' if none), `colour_effective` and `hex` to every wire (in place; -> wires). `overrides` is {wire name: colour name}."""
    overrides = overrides or {}
    for w in wires:
        w['colour'] = derived_colour(scheme, w['class'], manager)
        w['colour_override'] = overrides.get(w['name'], '')
        w['colour_effective'] = w['colour_override'] or w['colour']
        w['hex'] = WIRE_COLOURS.get(w['colour_effective'], '')
    return wires


def check_colour(name):
    if name not in WIRE_COLOURS:
        raise LayoutRefused("%r is not a wire colour (colours: %s)" % (name, ', '.join(sorted(WIRE_COLOURS))))
    return name


def copy_scheme(manager, new_name, copy_of=SCHEME_DEFAULT, colors=None, display_name=''):
    """Copy a scheme (seeded or yours) under a new name, optionally with colours set on the copy. -> the new scheme dict."""
    from electrodevice.objects.layout.WireColorScheme import WireColorScheme
    allp = all_schemes(manager)
    if copy_of not in allp:
        raise LayoutRefused("no scheme %r to copy (known: %s)" % (copy_of, ', '.join(sorted(allp))), status=404)
    if new_name in allp:
        raise LayoutRefused("a scheme named %r already exists (%s): choose another name" % (new_name, 'seeded, never edited in place' if allp[new_name]['seeded'] else 'yours'), status=409)
    if not new_name or not all(ch.isalnum() or ch in '-_' for ch in new_name):
        raise LayoutRefused("a scheme name is letters, digits, dashes and underscores (got %r)" % new_name)
    base = dict(allp[copy_of]['colors'])
    for k, v in (colors or {}).items():
        base[_check_key(k, base)] = check_colour(v)
    LR.upsert(manager, WireColorScheme, new_name, display_name=display_name or ('My ' + allp[copy_of]['display_name'] if not allp[copy_of]['display_name'].startswith('My ') else allp[copy_of]['display_name']),
              description='Copied from %s.' % copy_of, colors_json=json.dumps(base, sort_keys=True), seeded=False, copy_of=copy_of, follows=allp[copy_of]['follows'], notes='')
    return get_scheme(manager, new_name)


def _check_key(key, colors):
    if key not in colors and key not in KEYS_FIXED:
        raise LayoutRefused("%r is not a colour key of this scheme (keys: %s)" % (key, ', '.join(sorted(set(colors) | set(KEYS_FIXED)))))
    return key


def set_colour(manager, name, key, colour):
    """Set one key of YOUR scheme. A seeded scheme is refused with the copy words."""
    allp = all_schemes(manager)
    if name not in allp:
        raise LayoutRefused("no scheme %r (known: %s)" % (name, ', '.join(sorted(allp))), status=404)
    if allp[name]['seeded']:
        raise LayoutRefused("scheme %r is seeded and is never edited in place: copy it first (wire-colors copy %s <your name>), then set the colour on the copy" % (name, name), status=409)
    colors = dict(allp[name]['colors'])
    colors[_check_key(key, colors)] = check_colour(colour)
    row = LR.find(manager, 'WireColorScheme', name)
    row.colors_json = json.dumps(colors, sort_keys=True)
    LR._save(manager, row)
    return get_scheme(manager, name)
