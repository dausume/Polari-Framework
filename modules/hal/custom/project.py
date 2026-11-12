"""
@module hal.custom.project

THE HAL IN A GENERATED FIRMWARE PROJECT (hal-2/hal-3, HAL_CATOM_CATALOGUE_PLAN.md §5): an isotope declares what it REQUIRES of
the HAL, per variable pin (isotope.json `requires`: {"button_pin": ["gpio.input", "gpio.pull_up", ...]}); this module resolves
those operations on the pin the configuration chose, refuses by name when one does not resolve on that chip (that refusal IS the
isotope's eligibility on the board), and writes the one header the project includes — only the units the isotope uses.

  requires(isotope_dir)                      -> {variable: [operation, ...]} from isotope.json (empty when it declares none)
  resolve(soc, requires, pins)               -> {ok, units[{variable, operation, pin, key, macro, status, why}], refused[]}
  project_header(soc, requires, pins)        -> {file, text, sha256, keys, macros{(variable, operation): macro}} or raises HalRefused
"""
import json
import os

from hal.custom import generate as G
from hal.custom import render as RD


class HalRefused(ValueError):
    pass


def requires(isotope_dir):
    p = os.path.join(isotope_dir, 'isotope.json')
    if not os.path.isfile(p):
        return {}
    return dict(json.load(open(p)).get('requires') or {})


def resolve(soc, reqs, pins):
    units, refused = [], []
    for var, ops in sorted(reqs.items()):
        pin = pins.get(var)
        for op in ops:
            if not pin:
                refused.append({'variable': var, 'operation': op, 'why': 'no pin chosen for %s' % var})
                continue
            u = G.unit(soc, op, pin)['unit']
            row = {'variable': var, 'operation': op, 'pin': pin, 'key': u['key'], 'macro': u.get('macro', ''), 'status': u['status'], 'why': u.get('why', '')}
            units.append(row)
            if u['status'] != 'resolved':
                refused.append(row)
    return {'ok': not refused, 'units': units, 'refused': refused}


def project_header(soc, reqs, pins):
    r = resolve(soc, reqs, pins)
    if not r['ok']:
        raise HalRefused('; '.join('%s on %s (%s): %s' % (x['operation'], x.get('pin') or '?', x['variable'], x['why']) for x in r['refused']))
    keys = []
    for u in r['units']:
        if u['key'] not in keys:
            keys.append(u['key'])
    h = RD.header(soc, keys)
    return {'file': h['name'], 'text': h['text'], 'sha256': h['sha256'], 'keys': keys,
            'macros': {(u['variable'], u['operation']): u['macro'] for u in r['units']}, 'units': r['units']}


def isotope_header(isotope_dir, soc, pins):
    """The header for ONE isotope's requires on the chosen pins, or None when the isotope declares none (still register-level)."""
    reqs = requires(isotope_dir)
    return project_header(soc, reqs, pins) if reqs else None


def merged_header(soc, headers):
    """One header for every isotope of a project (a firmware with two isotopes includes ONE polari_hal_<soc>.h): the union of their
    units, in the order they first appear."""
    keys = []
    for h in headers:
        for k in (h or {}).get('keys', []):
            if k not in keys:
                keys.append(k)
    if not keys:
        return None
    hdr = RD.header(soc, keys)
    return {'file': hdr['name'], 'text': hdr['text'], 'sha256': hdr['sha256'], 'keys': keys}
