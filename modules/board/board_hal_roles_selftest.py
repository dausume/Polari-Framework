"""board_hal_roles_selftest - hal-3a review (econ): for EVERY seeded firmware variant and every firmwarefaults scenario variant, the
roles gen.base_roles asks the generated HAL header for are exactly the blocks the shared uno/hal.c turns on, judged from that
variant's OWN rendered board_config.h (render_config) through hal.c's own guards:
    LED    <- #if FEATURE_LED
    BUTTON <- #if HAL_INT0 && !HAL_BUTTON_ROUTE      (a build flag HAL_INT0=1 turns it on too: uno-button-count)
    SENSE  <- #if HAL_INT1 && !HAL_SENSE_ROUTE
    PWM    <- #if FEATURE_PWM                        (hal.c #errors on any PWM_PIN but 5 / 6 / 9 / 10)
plus each role's pin (BUTTON D2 = INT0, SENSE D3 = INT1: hal.c's blocks are hardware-fixed to them). A proof that cannot fail is
not a proof, so the comparator is also run on a role set and on a config that must FAIL it.

    PYTHONPATH=.:modules python3 -m board.board_hal_roles_selftest      # from polari-framework/ (standalone)
"""
import re

_results = []

HAL_C_GUARDS = ('FEATURE_LED', 'HAL_INT0 && !HAL_BUTTON_ROUTE', 'HAL_INT1 && !HAL_SENSE_ROUTE', 'FEATURE_PWM')   # guarded_roles mirrors these
FIXED_PIN = {'BUTTON': 'PD2', 'SENSE': 'PD3'}   # hal.c: ISR(INT0_vect) on D2, ISR(INT1_vect) on D3


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  ' + str(extra)[:300]) if (extra and not cond) else ''))


def defines(cfg):
    """the integer #defines of a rendered board_config.h (an undefined name is 0 in #if, as in C)"""
    return {m.group(1): int(m.group(2)) for m in re.finditer(r'^#define\s+(\w+)\s+(-?\d+)u?\b', cfg, re.M)}


def guarded_roles(d):
    g = lambda n: d.get(n, 0)
    out = set()
    if g('FEATURE_LED'):
        out.add('LED')
    if g('HAL_INT0') and not g('HAL_BUTTON_ROUTE'):
        out.add('BUTTON')
    if g('HAL_INT1') and not g('HAL_SENSE_ROUTE'):
        out.add('SENSE')
    if g('FEATURE_PWM'):
        out.add('PWM')
    return out


def judge(roles, cfg):
    """-> [] when base_roles' answer agrees with the config's guards, else the reasons in words"""
    why = []
    got, exp = {x['role'] for x in roles}, guarded_roles(defines(cfg))
    if got != exp:
        why.append('roles %s, hal.c turns on %s' % (sorted(got), sorted(exp)))
    for x in roles:
        if x['role'] in FIXED_PIN and x['pin'] != FIXED_PIN[x['role']]:
            why.append('%s on %s, but hal.c\'s block is fixed to %s' % (x['role'], x['pin'], FIXED_PIN[x['role']]))
    return why


def run():
    from board.custom import gen as G, variants as V
    from board.custom.variants import SEED_FIRMWARE_VARIANTS
    from firmwarefaults.custom.scenarios import scenario_variants
    rows = [('seed', v) for v in SEED_FIRMWARE_VARIANTS] + [('scenario', v) for v in scenario_variants()]
    import os
    src = open(os.path.join(os.path.dirname(G.__file__), 'firmware', 'uno', 'hal.c')).read()
    guards = {g: bool(re.search(r'^#if\s+%s\s*(?:/\*|$)' % re.escape(g), src, re.M)) for g in HAL_C_GUARDS}
    check('hal.c still opens its role blocks with the guards this check mirrors (%s)' % ' | '.join(HAL_C_GUARDS), all(guards.values()),
          'missing: %s' % [g for g, ok in guards.items() if not ok])
    check('there are variants to judge (seed + scenario)', len(rows) >= 20, len(rows))
    flagged = 0
    for kind, v in rows:
        try:
            r = V.resolve(v, {})
        except V.VariantRefused as e:
            check('%s variant %s resolves' % (kind, v['name']), False, e)
            continue
        flagged += any(n == 'HAL_INT0' for n, _ in r.get('flags') or [])
        why = judge(G.base_roles(r), V.render_config(r))
        check('%s variant %s: base_roles == the hal.c blocks its board_config.h turns on' % (kind, v['name']), not why, '; '.join(why))
    check('the build-flag path is exercised (a variant sets HAL_INT0 as a flag: uno-button-count / -debounce)', flagged >= 1, flagged)
    # controls: the comparator must fail
    cfg = '#define FEATURE_LED  1\n#define FEATURE_PWM  0\n#define HAL_INT0     1\n#define HAL_BUTTON_ROUTE 1\n'
    check('control: a route-rendered button (HAL_BUTTON_ROUTE 1) turns hal.c\'s INT0 block OFF', guarded_roles(defines(cfg)) == {'LED'})
    check('control: a role hal.c does not turn on is caught',
          judge([{'role': 'LED', 'pin': 'PB5'}, {'role': 'BUTTON', 'pin': 'PD2'}], cfg) != [])
    check('control: a missing role is caught', judge([], cfg) != [])
    check('control: a button off D2 is caught',
          judge([{'role': 'LED', 'pin': 'PB5'}, {'role': 'BUTTON', 'pin': 'PD7'}], cfg.replace('#define HAL_BUTTON_ROUTE 1\n', '')) != [])
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
