"""board_hal_roles_selftest - hal-3a review (econ): for EVERY seeded firmware variant and every firmwarefaults scenario variant, the
roles gen.base_roles asks the generated HAL header for are exactly the blocks the shared uno/hal.c turns on, judged from that
variant's OWN rendered board_config.h (render_config) through hal.c's own guards:
    LED    <- #if FEATURE_LED
    BUTTON <- #if CFG_INT0 && !CFG_BUTTON_ROUTE      (a build flag CFG_INT0=1 turns it on too: uno-button-count)
    SENSE  <- #if CFG_INT1 && !CFG_SENSE_ROUTE
    PWM    <- #if FEATURE_PWM                        (hal.c #errors on any PWM_PIN but 5 / 6 / 9 / 10)
    UART   <- always (hal.c's USART0 link is unguarded)  TICK <- always (the Timer2 1 ms tick)      (hal-3b step 1)
    ADC    <- #if FEATURE_ADC                        WDT  <- #if CFG_WDT (a build flag: uno-sim-rig-wdt)   (hal-3b step 1)
plus each role's pin (BUTTON D2 = INT0, SENSE D3 = INT1: hal.c's blocks are hardware-fixed to them). A proof that cannot fail is
not a proof, so the comparator is also run on a role set and on a config that must FAIL it.

    PYTHONPATH=.:modules python3 -m board.board_hal_roles_selftest      # from polari-framework/ (standalone)
"""
import re

_results = []

HAL_C_GUARDS = ('FEATURE_LED', 'CFG_INT0 && !CFG_BUTTON_ROUTE', 'CFG_INT1 && !CFG_SENSE_ROUTE', 'FEATURE_PWM', 'FEATURE_ADC', 'CFG_WDT')   # guarded_roles mirrors these
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
    if g('CFG_INT0') and not g('CFG_BUTTON_ROUTE'):
        out.add('BUTTON')
    if g('CFG_INT1') and not g('CFG_SENSE_ROUTE'):
        out.add('SENSE')
    if g('FEATURE_PWM'):
        out.add('PWM')
    out |= {'UART', 'TICK'}
    if g('FEATURE_ADC'):
        out.add('ADC')
    if g('CFG_WDT'):
        out.add('WDT')
    return out


def judge(roles, cfg, flags=()):
    """-> [] when base_roles' answer agrees with the config's guards, else the reasons in words. `flags` = the build's -D flags,
    which reach hal.c's #if exactly as board_config.h's #defines do (CFG_INT0 on uno-button-count, CFG_WDT on uno-sim-rig-wdt)"""
    why = []
    d = defines(cfg)
    d.update({n: int(v) for n, v in flags if n not in d and str(v).lstrip('-').isdigit()})
    got, exp = {x['role'] for x in roles}, guarded_roles(d)
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
    flagged = wdt_flagged = 0
    for kind, v in rows:
        try:
            r = V.resolve(v, {})
        except V.VariantRefused as e:
            check('%s variant %s resolves' % (kind, v['name']), False, e)
            continue
        flagged += any(n == 'CFG_INT0' for n, _ in r.get('flags') or [])
        why = judge(G.base_roles(r), V.render_config(r), r.get('flags') or [])
        wdt_flagged += any(n == 'CFG_WDT' for n, _ in r.get('flags') or [])
        check('%s variant %s: base_roles == the hal.c blocks its board_config.h turns on' % (kind, v['name']), not why, '; '.join(why))
    check('the build-flag path is exercised (a variant sets CFG_INT0 as a flag: uno-button-count / -debounce)', flagged >= 1, flagged)
    check('the WDT flag path is exercised (a variant sets CFG_WDT as a build flag: uno-sim-rig-wdt)', wdt_flagged >= 1, wdt_flagged)
    # controls: the comparator must fail
    cfg = '#define FEATURE_LED  1\n#define FEATURE_PWM  0\n#define CFG_INT0     1\n#define CFG_BUTTON_ROUTE 1\n'
    base = [{'role': 'UART', 'pin': 'USART0'}, {'role': 'TICK', 'pin': 'TIMER2'}]
    check('control: a route-rendered button (CFG_BUTTON_ROUTE 1) turns hal.c\'s INT0 block OFF', guarded_roles(defines(cfg)) == {'LED', 'UART', 'TICK'})
    check('control: a role hal.c does not turn on is caught',
          judge(base + [{'role': 'LED', 'pin': 'PB5'}, {'role': 'BUTTON', 'pin': 'PD2'}], cfg) != [])
    check('control: a missing role is caught', judge([], cfg) != [])
    check('control: a missing UART / TICK is caught (step 1: every build drives them)', judge([{'role': 'LED', 'pin': 'PB5'}], cfg) != [])
    check('control: a WDT role without CFG_WDT is caught, and CFG_WDT as a build flag turns it on',
          judge(base + [{'role': 'LED', 'pin': 'PB5'}, {'role': 'WDT', 'pin': 'WDT'}], cfg) != []
          and judge(base + [{'role': 'LED', 'pin': 'PB5'}, {'role': 'WDT', 'pin': 'WDT'}], cfg, [('CFG_WDT', '1')]) == [])
    check('control: a button off D2 is caught',
          judge(base + [{'role': 'LED', 'pin': 'PB5'}, {'role': 'BUTTON', 'pin': 'PD7'}], cfg.replace('#define CFG_BUTTON_ROUTE 1\n', '')) != [])
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
