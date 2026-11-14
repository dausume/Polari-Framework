"""board_sim_layout_selftest - pt-1a (PIN_TWIN_PLAN.md §2a / §3): the behaviour + simulation-binding rows and the device layout they export.
The gate:
  * every required role of an overlaid block resolves through hal soc_rules to a RegisterField row inside the device's spans, per pin; a role
    the rules lack, or mark missing, fails the export NAMED (negative controls on a copy of the rules);
  * every overlaid span's unmodelled offsets are listed as passthrough (map + passthrough tile the span exactly; GPIO_STRAP is passthrough);
  * the layout is deterministic: same rows -> same sha, whatever order the rows arrive in.

    PYTHONPATH=.:modules python3 -m board.board_sim_layout_selftest
"""
import copy
import json

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  <- ' + str(extra)[:400]) if (extra and not cond) else ''))


def _refused(fn):
    from board.custom import sim_layout as L
    try:
        fn()
    except L.LayoutRefused as e:
        return str(e)
    return ''


def run():
    from board.custom import sim_bindings as SB, sim_layout as L, registers_esp32c3 as R3
    from board import board_seed as S
    from hal.custom import soc_rules as SR

    # ---- the rows
    ovs = SB.overlays('esp32c3-qemu')
    blocks = sorted(o['name'].split(':', 1)[1] for o in ovs)
    check('rows: one pinbank BlockBehaviour, one SimulatedChip (the C3 in Espressif\'s QEMU fork), one SimOverlay per C3 register block (%d)' % len(R3.BASES),
          [b['name'] for b in SB.BLOCK_BEHAVIOURS] == ['pinbank'] and SB.chip('esp32c3-qemu')['simulator'] == 'qemu:esp32c3'
          and blocks == sorted(R3.BASES), blocks)
    check('rows: GPIO and IO_MUX are overlays of ONE pinbank device; every other block is vendor with its why and evidence',
          {o['name'].split(':')[1] for o in ovs if o['mode'] == 'overlay'} == {'GPIO', 'IO_MUX'}
          and {(o['behaviour'], o['device']) for o in ovs if o['mode'] == 'overlay'} == {('pinbank', 'pins')}
          and all(o['why'] and o['evidence'] for o in ovs) and all(o['behaviour'] == '' for o in ovs if o['mode'] == 'vendor'))
    check('rows: the vendor rows say where the fork has NO model (LEDC, ADC: the catch-all answers) - not claimed as modelled',
          all('NOT modelled' in o['why'] for o in ovs if o['name'].split(':')[1] in ('LEDC', 'APB_SARADC')))
    names = {r['name'] for r in S.SEED_BOARD_OBJECT['Peripheral']}
    check('rows: every SimOverlay names a seeded Peripheral row', all(o['peripheral'] in names for o in ovs), [o['peripheral'] for o in ovs if o['peripheral'] not in names])

    # ---- the export
    lay = L.layout('esp32c3-qemu')
    dev = lay['devices'][0]
    need = json.loads(SB.behaviour('pinbank')['roles_json'])
    pins = dev['params']['pins']
    nregs = {role: len(SR.RULES['esp32c3']['roles'][role]['registers']) for role in need['modelled']}
    check('export: ONE device (pins, pinbank, 22 pins) over the GPIO and IO_MUX spans',
          [d['name'] for d in lay['devices']] == ['pins'] and pins == 22 and [s['name'] for s in dev['spans']] == ['esp32c3-qemu:GPIO', 'esp32c3-qemu:IO_MUX'])
    check('export: every required role (%d) resolves on every pin to a field row inside the spans, from hal soc_rules (not re-typed)' % len(need['modelled']),
          sorted(dev['roles']) == sorted(need['modelled'])
          and all(len(dev['roles'][r]['per_pin']) == pins * nregs[r] for r in need['modelled'])
          and all(dev['roles'][r]['cite'] == SR.RULES['esp32c3']['roles'][r].get('cite', '') for r in need['modelled']),
          {r: len(dev['roles'][r]['per_pin']) for r in dev['roles']})
    check('export: interrupt_source = 16 (TRM Table 8.3-1, from the rules), the value role the vendor interrupt matrix takes',
          dev['values']['interrupt_source']['values'] == {'source': 16} and 'Table 8.3-1' in dev['values']['interrupt_source']['cite'])
    regs = {r['name']: r for s in dev['spans'] for r in s['registers']}
    check('export: the set / clear aliases carry their acts_on target, and the target is modelled by the same device',
          {(n, f['acts_on']) for n, r in regs.items() for f in r['fields'] if f['access'] in L.ALIASES} >=
          {('GPIO_OUT_W1TS_REG', 'GPIO_OUT_REG'), ('GPIO_STATUS_W1TC_REG', 'GPIO_STATUS_REG')}
          and all(f['acts_on'] in regs for r in regs.values() for f in r['fields'] if f['acts_on']))
    io4 = regs['IO_MUX_GPIO4_REG']
    check('export: resets - OUT_SEL 0x80 printed; IO_MUX_GPIO4 composed from its fields (printed in words): FUN_IE 1, FUN_DRV 2, MCU_SEL 0 (MTMS at reset)',
          regs['GPIO_FUNC4_OUT_SEL_CFG_REG']['reset'] == 0x80 and io4['reset_from'].startswith('composed')
          and io4['reset'] == (1 << 9) | (2 << 10), hex(io4['reset']))

    # ---- passthrough
    ok_tile, strap = True, R3.address(next(r for r in R3.REGISTERS if r['register'] == 'GPIO_STRAP_REG'))
    for s in dev['spans']:
        cover = sorted(s['map'] + s['passthrough'])
        at = 0
        for o, n in cover:
            ok_tile &= (o == at)
            at = o + n
        ok_tile &= (at == s['size'])
    gpio = dev['spans'][0]
    so = int(strap, 16) - gpio['base']
    check('passthrough: map + passthrough tile every overlaid span exactly; GPIO_STRAP (0x38) is passthrough, left to the vendor model',
          ok_tile and any(o <= so < o + n for o, n in gpio['passthrough']) and not any(o <= so < o + n for o, n in gpio['map'])
          and gpio['left_to_vendor'] == ['GPIO_STRAP_REG'] and 'GPIO_STRAP_REG' not in regs)

    # ---- determinism
    R, F = S.SEED_BOARD_OBJECT['Register'], S.SEED_BOARD_OBJECT['RegisterField']
    again = L.layout('esp32c3-qemu', registers=list(reversed(R)), fields=list(reversed(F)))
    check('deterministic: the same rows in reverse order give the same layout sha (%s)' % lay['sha256'][:12],
          again['sha256'] == lay['sha256'] == L.layout('esp32c3-qemu')['sha256'])

    # ---- negative controls (copies; the real rules and rows are never touched)
    rules = copy.deepcopy(SR.RULES['esp32c3']['roles'])
    del rules['pad_function']
    why = _refused(lambda: L.layout('esp32c3-qemu', rules=rules))
    check('control: a role the rules lack fails the export, named', 'pad_function' in why and 'RULES' in why, why)
    rules = copy.deepcopy(SR.RULES['esp32c3']['roles'])
    rules['output_driver'] = {'registers': [], 'missing': 'test: not cited'}
    why = _refused(lambda: L.layout('esp32c3-qemu', rules=rules))
    check('control: a role marked missing fails the export with the rules\' own words', 'output_driver' in why and 'test: not cited' in why, why)
    rules = copy.deepcopy(SR.RULES['esp32c3']['roles'])
    rules['pull_up'] = dict(rules['pull_up'], field='FUN_WPU_TYPO')
    why = _refused(lambda: L.layout('esp32c3-qemu', rules=rules))
    check('control: a role naming a field that is not a row fails, named (register + field + pin)', 'FUN_WPU_TYPO' in why and 'pin 0' in why, why)
    F2 = [dict(f, acts_on='') if f['name'] == 'esp32c3:GPIO_OUT_W1TS_REG.OUT_W1TS_3' else f for f in F]
    why = _refused(lambda: L.layout('esp32c3-qemu', registers=R, fields=F2))
    check('control: a set alias with no acts_on fails, named', 'OUT_W1TS_3' in why and 'acts_on' in why, why)
    F3 = [dict(f, reset_value='1') if f['name'] == 'esp32c3:GPIO_FUNC4_OUT_SEL_CFG_REG.OEN_SEL' else f for f in F]
    why = _refused(lambda: L.layout('esp32c3-qemu', registers=R, fields=F3))
    check('control: a field reset that contradicts its register\'s printed reset fails, named', 'GPIO_FUNC4_OUT_SEL_CFG_REG' in why, why)

    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
