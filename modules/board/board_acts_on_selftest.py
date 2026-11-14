"""board_acts_on_selftest - hal-3b (pol's pin twin, PIN_TWIN_PLAN.md §2a): RegisterField.acts_on, the register a write-1-to-set / write-1-to-clear alias
acts on, as DATA (the pin twin's generic device needs it; until now it was only in words). Filled by econ's importers, never guessed:
  esp32c3   registers_esp32c3 (the TRM rows): OUT_W1TS/W1TC -> GPIO_OUT_REG, ENABLE_W1TS/W1TC -> GPIO_ENABLE_REG, STATUS_W1TC -> GPIO_STATUS_REG
  rp2350    chipdesc_rp2350.ACTS_ON, refused unless the alias's own cited SVD text names it (`GPIO_OUT |= wdata`)
  svd / rdl the generic importers state none (the formats carry no alias target): blank
CROSS-CHECK: each target is a register of the same chip, and the TRM / SVD words name it - the alias field's own text, or the target's text naming the alias.

    PYTHONPATH=.:modules python3 -m board.board_acts_on_selftest
"""
import inspect
import json

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  <- ' + str(extra)[:400]) if (extra and not cond) else ''))


def _words(f):
    return ' '.join([f.get('description', ''), json.dumps(f.get('values') or {}), f.get('notes', '')])


def run():
    from board.objects.board.RegisterField import RegisterField
    check('RegisterField has the acts_on column (default blank)', inspect.signature(RegisterField.__init__).parameters.get('acts_on') is not None
          and inspect.signature(RegisterField.__init__).parameters['acts_on'].default == '')
    # ---- esp32c3
    from board.custom import registers_esp32c3 as RC
    regs = {r['register'] for r in RC.REGISTERS}
    aliases = [f for f in RC.FIELDS if f['access'] in ('w1-set', 'w1-clear')]
    check('C3: every set / clear alias field (%d) names the register it acts on; no other field does' % len(aliases),
          aliases and all(f.get('acts_on') for f in aliases) and not any(f.get('acts_on') for f in RC.FIELDS if f['access'] not in ('w1-set', 'w1-clear')),
          [f['register'] for f in aliases if not f.get('acts_on')][:3])
    pairs = sorted({(f['register'], f['acts_on']) for f in aliases})
    check('C3: the five alias registers and their targets', pairs == [('GPIO_ENABLE_W1TC_REG', 'GPIO_ENABLE_REG'), ('GPIO_ENABLE_W1TS_REG', 'GPIO_ENABLE_REG'),
                                                                       ('GPIO_OUT_W1TC_REG', 'GPIO_OUT_REG'), ('GPIO_OUT_W1TS_REG', 'GPIO_OUT_REG'),
                                                                       ('GPIO_STATUS_W1TC_REG', 'GPIO_STATUS_REG')], pairs)
    by_reg = {}
    for f in RC.FIELDS:
        by_reg.setdefault(f['register'], []).append(f)
    unsaid = []
    for f in aliases:
        t = f['acts_on']
        named = t in _words(f) or any(f['register'] in _words(g) for g in by_reg.get(t, []))
        if t not in regs or not named:
            unsaid.append((f['register'], f['field'], t))
    check('C3 CROSS-CHECK: each target is a C3 register, and the TRM words name it (the alias\'s own text: "set GPIO%d\'s bit of GPIO_OUT_REG"; or the target\'s: '
          'GPIO_STATUS_REG "clear it through GPIO_STATUS_W1TC_REG")', not unsaid, unsaid[:3])
    from board.custom import hardware_chain_c3 as HC
    rows = HC.register_fields()
    rr = {r['name'] for r in HC.registers()}
    ar = [r for r in rows if r.get('acts_on')]
    check('C3 ROWS: the RegisterField rows carry it as a Register row name (esp32c3:GPIO_OUT_REG), each one a Register row of the tables',
          len(ar) == len(aliases) and all(r['acts_on'] in rr and r['acts_on'].startswith('esp32c3:') for r in ar), [r['acts_on'] for r in ar if r['acts_on'] not in rr][:3])
    # ---- rp2350
    from board.custom import chipdesc_rp2350 as RP
    R, F, bases = RP.rows()
    rnames = {r['register'] for r in R}
    ra = sorted((f['register'], f['acts_on']) for f in F if f.get('acts_on'))
    check('RP2350: the four SIO SET / CLR aliases act on SIO_GPIO_OUT_REG / SIO_GPIO_OE_REG, both registers of the extract; nothing else names one',
          ra == [('SIO_GPIO_OE_CLR_REG', 'SIO_GPIO_OE_REG'), ('SIO_GPIO_OE_SET_REG', 'SIO_GPIO_OE_REG'), ('SIO_GPIO_OUT_CLR_REG', 'SIO_GPIO_OUT_REG'),
                ('SIO_GPIO_OUT_SET_REG', 'SIO_GPIO_OUT_REG')] and {t for _r, t in ra} <= rnames, ra)
    saved = dict(RP.ACTS_ON)
    try:
        RP.ACTS_ON[('SIO_GPIO_OUT_SET_REG', 'GPIO_OUT_SET')] = 'SIO_GPIO_OE_REG'
        try:
            RP.refine([f for f in F])
            refused = ''
        except RP.Rp2350Refused as e:
            refused = str(e)
    finally:
        RP.ACTS_ON.clear()
        RP.ACTS_ON.update(saved)
    check('RP2350 CROSS-CHECK: a target the alias\'s cited text does not name is refused, not guessed', 'does not name it' in refused, refused)
    # ---- the generic importers
    from board import board_chipdesc_provider_selftest as T
    _R1, F1 = T._rdl_rows()
    _R2, F2 = T._svd_rows()
    check('rdl / svd importers: the formats state no alias target, so every field\'s acts_on is blank (the key present, never guessed)',
          all('acts_on' in f and f['acts_on'] == '' for f in F1) and all(f.get('acts_on', '') == '' for f in F2), '')
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
