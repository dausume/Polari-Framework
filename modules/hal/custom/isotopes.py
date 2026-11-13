"""
@module hal.custom.isotopes

ISOTOPE FIT, derived from what each isotope REQUIRES of the HAL (hal-2, HAL_CATOM_CATALOGUE_PLAN.md §5). An isotope (one WAY of
doing a catom's job) fits a pin of a chip when every HAL operation it declares for that variable resolves there. Nothing per board
is coded: a new chip (or a new isotope) is answered by the same rule.

  catalogue()                     -> [{catom, isotope, dir, requires{variable: [ops]}}] for every isotope.json under board's catoms
  fit(catom, isotope, soc)        -> [{pin, verdict fits | missing, missing ops, why}] one row per pin the chip's tables reach
  summary()                       -> [{catom, isotope, requires, <soc>_fits, ...}] one row per isotope with its fit count per chip

Isotopes without `requires` are listed with requires '' (not yet written against the HAL) and no fit answer.
"""
import glob
import json
import os

from hal.custom import generate as G
from hal.custom import project as HP
from hal.custom import soc_rules as SR


def _catoms_root():
    import board.custom as bc
    return os.path.join(os.path.dirname(bc.__file__), 'firmware', 'uno', 'catoms')


def catalogue():
    out = []
    for p in sorted(glob.glob(os.path.join(_catoms_root(), '*', 'isotopes', '*', 'isotope.json'))):
        d = os.path.dirname(p)
        catom = os.path.basename(os.path.dirname(os.path.dirname(d)))
        out.append({'catom': catom, 'isotope': os.path.basename(d), 'dir': d, 'requires': HP.requires(d)})
    return out


def _find(catom, isotope):
    return next((c for c in catalogue() if c['catom'] == catom and c['isotope'] == isotope), None)


def _peripheral_var(ops):
    """hal-3b step 1: a variable whose operations target a peripheral INSTANCE (adc, uart, tick, wdt), not a pin"""
    from hal.custom import operations as OPS
    return any((OPS.by_name(o) or {}).get('target') == 'peripheral' for o in ops)


def _instance(soc, var, ops):
    """the first instance of the chip that serves the ops' family and resolves every op -> (instance, []) or (None, refused rows)"""
    from hal.custom import operations as OPS
    fams = {(OPS.by_name(o) or {}).get('family') for o in ops}
    pers = SR.RULES[soc].get('peripherals') or {}
    tried = []
    for inst, per in sorted(pers.items()):
        if not fams <= set(per.get('families') or ()):
            continue
        r = HP.resolve(soc, {var: ops}, {var: inst})
        if r['ok']:
            return inst, []
        tried += r['refused']
    return None, tried or [{'operation': ', '.join(ops), 'why': '%s has no %s peripheral' % (soc, '/'.join(sorted(f for f in fams if f)))}]


def fit(catom, isotope, soc):
    """one row per pin (an isotope with pin variables) or one row for the chip (peripheral variables only); a peripheral variable is
    answered by the chip's own instances (RULES peripherals), never by trying pins"""
    c = _find(catom, isotope)
    if c is None or not c['requires']:
        return []
    pvars = {v: ops for v, ops in c['requires'].items() if not _peripheral_var(ops)}
    perbad, insts = [], {}
    for var, ops in sorted(c['requires'].items()):
        if var not in pvars:
            inst, bad = _instance(soc, var, ops)
            insts[var] = inst
            perbad += bad
    note = ', '.join('%s = %s' % (v, i) for v, i in sorted(insts.items()) if i)
    rows = []
    for pin in (G.default_pins(soc) if pvars else [note or '(chip)']):
        bad = list(perbad)
        for var, ops in sorted(pvars.items()):
            r = HP.resolve(soc, {var: ops}, {var: pin})
            bad += r['refused']
        rows.append({'catom': catom, 'isotope': isotope, 'soc': soc, 'pin': pin, 'verdict': 'missing' if bad else 'fits',
                     'missing': ', '.join(b['operation'] for b in bad), 'instances': note,
                     'why': '; '.join('%s: %s' % (b['operation'], b['why']) for b in bad)})
    return rows


def summary():
    out = []
    for c in catalogue():
        row = {'catom': c['catom'], 'isotope': c['isotope'], 'key': '%s:%s' % (c['catom'], c['isotope']),
               'requires': '; '.join('%s: %s' % (v, ', '.join(ops)) for v, ops in sorted(c['requires'].items()))}
        for soc in SR.socs():
            rows = fit(c['catom'], c['isotope'], soc) if c['requires'] else []
            row['%s_fits' % soc] = (('%d of %d pins' % (sum(r['verdict'] == 'fits' for r in rows), len(rows))) if len(rows) > 1 or rows[0]['pin'] in G.default_pins(soc)
                                    else ('fits (%s)' % rows[0]['instances'] if rows[0]['verdict'] == 'fits' else 'missing: ' + rows[0]['missing'])) if rows else ('not written against the HAL yet' if not c['requires'] else '0 pins')
        out.append(row)
    return out
