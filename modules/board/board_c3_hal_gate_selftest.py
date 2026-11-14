"""board_c3_hal_gate_selftest - hal-3b step 2 (econ): the C3 light's chip pins (apps/light_hal.h, PIN_SHIM 0) moved from ESP-IDF's gpio driver onto the
GENERATED HAL. QEMU's C3 GPIO is a register stub (writes dropped, GPIO_IN never moves), so a twin run of the chip half cannot see a pin: the gates are

  1  the header compiles standalone (riscv-gcc rv32imc -Werror; SKIP without the engine) and the PIN_SHIM 0 project built through idf-build
  2  TWO-SIDED MEASURED EQUIVALENCE (pol's ask): every GPIO / IO_MUX access of the light pins, measured in QEMU through memory_region_ops_write / _read on the
     real -O build, before (ESP-IDF v5.5.5) and after (the HAL) - evidence/c3_step2/light_pins_mmio.json. Each ESP-IDF access has a HAL match or a missing op
     named in words; each HAL access has an ESP-IDF match or a cited reason. Counts are the measured multisets, checked exactly.
     + statically: every read-modify-write the generated header emits leaves every bit outside its field mask unchanged.
  3  NO COLLATERAL CHANGE: the PIN_SHIM 1 (twin) app.bin differs only in its two hash fields
  4  said: the chip HAL is compiled and measured-equivalent; it has NOT run on a chip (no C3 on the bench); QEMU's GPIO is a stub

    PYTHONPATH=.:modules python3 -m board.board_c3_hal_gate_selftest
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = os.path.join(HERE, 'custom', 'evidence', 'c3_step2', 'light_pins_mmio.json')
_G, _GLL = 'esp_driver_gpio/src/gpio.c', 'hal/esp32c3/include/hal/gpio_ll.h'
TRM = 'ESP32-C3 TRM v1.4'

#: (pin, address, value, ESP-IDF count, HAL count, what, ESP-IDF source, verdict). verdict: 'same' | 'idf-only: <the missing op / why>' |
#: 'hal-only: <cited reason>' | 'differs: <cited reason>' | 'kept on ESP-IDF: <why>'. The LED is GPIO0, the sense line GPIO1, the button GPIO3 (LIGHT_KNOBS).
WRITES = [
    ('LED', 0x6000400c, 0x1, 1, 1, 'GPIO_OUT_W1TC bit 0: LED low at init', '%s gpio_set_level(0) -> %s gpio_ll_set_level' % (_G, _GLL), 'same'),
    ('LED', 0x60004024, 0x1, 1, 1, 'GPIO_ENABLE_W1TS bit 0: output enable', '%s gpio_output_enable -> gpio_ll_output_enable' % _G, 'same'),
    ('SENSE', 0x60004028, 0x2, 1, 1, 'GPIO_ENABLE_W1TC bit 1: output disabled', '%s gpio_output_disable -> gpio_ll_output_disable' % _G, 'same'),
    ('BUTTON', 0x60004028, 0x8, 1, 1, 'GPIO_ENABLE_W1TC bit 3: output disabled', '%s gpio_output_disable' % _G, 'same'),
    ('LED', 0x6000404c, 0x1, 1, 0, 'GPIO_STATUS_W1TC bit 0: pending interrupt cleared', '%s gpio_config -> gpio_intr_disable' % _G,
     'idf-only: the C3 has no int family in the HAL yet (int.edge_flag_clear); the LED never enables its interrupt (INT_ENA reset 0, %s Register 5.14 p.184)' % TRM),
    ('SENSE', 0x6000404c, 0x2, 1, 0, 'GPIO_STATUS_W1TC bit 1', '%s gpio_config -> gpio_intr_disable' % _G,
     'idf-only: no C3 int family in the HAL yet; the sense pin never enables its interrupt (INT_ENA reset 0)'),
    ('BUTTON', 0x6000404c, 0x8, 3, 3, 'GPIO_STATUS_W1TC bit 3', '%s gpio_set_intr_type / gpio_intr_enable / gpio_isr_handler_add' % _G,
     'kept on ESP-IDF: the button\'s interrupt (both builds call the same driver functions)'),
    ('LED', 0x60004074, 0x0, 1, 1, 'GPIO_PIN0.PAD_DRIVER = 0 (push-pull)', '%s gpio_od_disable -> gpio_ll_od_disable' % _G, 'same'),
    ('LED', 0x60004074, 0x0, 2, 0, 'GPIO_PIN0.INT_TYPE = 0, INT_ENA = 0', '%s gpio_set_intr_type(GPIO_INTR_DISABLE) + gpio_intr_disable' % _G,
     'idf-only: no C3 int family in the HAL yet (int.edge_disable); both fields reset to 0 (%s Register 5.14 p.184)' % TRM),
    ('SENSE', 0x60004078, 0x0, 1, 0, 'GPIO_PIN1.PAD_DRIVER = 0', '%s gpio_od_disable' % _G,
     'idf-only: gpio.input sets no output driver kind - the pad\'s output is disabled (ENABLE_W1TC), so PAD_DRIVER cannot act; gpio.output sets it when the pin drives'),
    ('SENSE', 0x60004078, 0x0, 2, 0, 'GPIO_PIN1.INT_TYPE = 0, INT_ENA = 0', '%s gpio_set_intr_type + gpio_intr_disable' % _G,
     'idf-only: no C3 int family in the HAL yet; reset 0'),
    ('BUTTON', 0x60004080, 0x0, 1, 0, 'GPIO_PIN3.PAD_DRIVER = 0', '%s gpio_od_disable' % _G, 'idf-only: as the sense pin - an input pin\'s output is disabled'),
    ('BUTTON', 0x60004080, 0x0, 1, 1, 'GPIO_PIN3 clear write of the interrupt setup', '%s gpio_set_intr_type / gpio_isr_handler_add' % _G, 'kept on ESP-IDF: the button interrupt'),
    ('BUTTON', 0x60004080, 0x100, 1, 1, 'GPIO_PIN3.INT_TYPE = 2 (falling edge)', '%s gpio_set_intr_type -> gpio_ll_set_intr_type' % _G, 'kept on ESP-IDF: the button interrupt'),
    ('BUTTON', 0x60004080, 0x2000, 2, 2, 'GPIO_PIN3.INT_ENA (CPU interrupt)', '%s gpio_intr_enable -> gpio_ll_intr_enable_on_core' % _G, 'kept on ESP-IDF: the button interrupt'),
    ('LED', 0x60004554, 0x80, 1, 1, 'GPIO_FUNC0_OUT_SEL_CFG: OUT_SEL = 128 (simple GPIO output)', '%s gpio_output_enable -> gpio_ll_matrix_out_default: REG_WRITE(.., SIG_GPIO_OUT_IDX)' % _G,
     'differs: ESP-IDF writes the whole word 0x80 (OUT_INV_SEL / OEN_SEL / OEN_INV_SEL = 0 at once); the HAL writes each field (OUT_SEL here, the three below)'),
    ('LED', 0x60004554, 0x0, 0, 2, 'GPIO_FUNC0_OUT_SEL_CFG: OUT_INV_SEL = 0, OEN_INV_SEL = 0 (field writes)', '(ESP-IDF: inside the whole-word 0x80 above)',
     'hal-only: the same two zeros ESP-IDF\'s whole-word write gives, field by field (%s Register 5.17 pp.185-186)' % TRM),
    ('LED', 0x60004554, 0x200, 0, 1, 'GPIO_FUNC0_OUT_SEL_CFG: OEN_SEL = 1', '(ESP-IDF leaves OEN_SEL 0 for an output)',
     'differs: the HAL takes the output enable from bit 0 of GPIO_ENABLE_REG (OEN_SEL 1 = "forced from bit n of GPIO_ENABLE_REG", %s Register 5.17), which gpio.output '
     'sets; ESP-IDF\'s 0 takes it from signal 128\'s own enable - not equated here, so the HAL uses the row-text meaning'),
    ('SENSE', 0x60004558, 0x0, 1, 1, 'GPIO_FUNC1_OUT_SEL_CFG: OEN_INV_SEL = 0', '%s gpio_output_disable -> gpio_hal_set_output_enable_ctrl(false, false)' % _G, 'same'),
    ('SENSE', 0x60004558, 0x200, 1, 1, 'GPIO_FUNC1_OUT_SEL_CFG: OEN_SEL = 1', '%s gpio_hal_set_output_enable_ctrl' % _G, 'same'),
    ('BUTTON', 0x60004560, 0x0, 1, 1, 'GPIO_FUNC3_OUT_SEL_CFG: OEN_INV_SEL = 0', '%s gpio_hal_set_output_enable_ctrl' % _G, 'same'),
    ('BUTTON', 0x60004560, 0x200, 1, 1, 'GPIO_FUNC3_OUT_SEL_CFG: OEN_SEL = 1', '%s gpio_hal_set_output_enable_ctrl' % _G, 'same'),
    ('LED', 0x60009004, 0x0, 2, 2, 'IO_MUX_GPIO0: FUN_WPU = 0, FUN_WPD = 0', '%s gpio_pullup_dis / gpio_pulldown_dis -> gpio_ll_pullup_dis / _pulldown_dis' % _G, 'same'),
    ('LED', 0x60009004, 0x0, 1, 0, 'IO_MUX_GPIO0: FUN_IE = 0 (input buffer off)', '%s gpio_input_disable -> gpio_ll_input_disable: PIN_INPUT_DISABLE' % _G,
     'idf-only: gpio.digital_input_off (queued C3 row, GPIO0..4: FUN_IE 0) - gpio.output leaves the input buffer as found, so the output\'s own level stays readable'),
    ('LED', 0x60009004, 0x1000, 2, 1, 'IO_MUX_GPIO0: MCU_SEL = 1 (GPIO function)', '%s gpio_output_enable + gpio_config\'s closing gpio_hal_func_sel' % _G,
     'differs: ESP-IDF selects the function twice (once per caller), the HAL once - the same value'),
    ('SENSE', 0x60009008, 0x0, 1, 2, 'IO_MUX_GPIO1: FUN_WPU = 0 (+ the HAL: FUN_WPD = 0 before setting it)', '%s gpio_pullup_dis' % _G,
     'differs: the HAL runs gpio.pull_none then gpio.pull_down (WPD cleared, then set); ESP-IDF clears WPU only - the same final bits'),
    ('SENSE', 0x60009008, 0x80, 1, 1, 'IO_MUX_GPIO1: FUN_WPD = 1', '%s gpio_pulldown_en' % _G, 'same'),
    ('SENSE', 0x60009008, 0x200, 1, 1, 'IO_MUX_GPIO1: FUN_IE = 1', '%s gpio_input_enable' % _G, 'same'),
    ('SENSE', 0x60009008, 0x1000, 2, 1, 'IO_MUX_GPIO1: MCU_SEL = 1', '%s gpio_output_disable + gpio_config\'s gpio_hal_func_sel' % _G, 'differs: twice vs once, the same value'),
    ('BUTTON', 0x60009010, 0x0, 1, 2, 'IO_MUX_GPIO3: FUN_WPD = 0 (+ the HAL: FUN_WPU = 0 before setting it)', '%s gpio_pulldown_dis' % _G,
     'differs: the HAL runs gpio.pull_none then gpio.pull_up; ESP-IDF clears WPD only - the same final bits'),
    ('BUTTON', 0x60009010, 0x100, 1, 1, 'IO_MUX_GPIO3: FUN_WPU = 1', '%s gpio_pullup_en' % _G, 'same'),
    ('BUTTON', 0x60009010, 0x200, 1, 1, 'IO_MUX_GPIO3: FUN_IE = 1', '%s gpio_input_enable' % _G, 'same'),
    ('BUTTON', 0x60009010, 0x1000, 2, 1, 'IO_MUX_GPIO3: MCU_SEL = 1', '%s gpio_output_disable + gpio_hal_func_sel' % _G, 'differs: twice vs once, the same value'),
]
#: (address, ESP-IDF reads, HAL reads, why) - 'poll' = GPIO_IN read by the sense task's loop, a count of virtual time not of code
READS = [
    (0x60004024, 1, 0, 'ESP-IDF stores into a bitfield of the write-1-to-set alias (hw->enable_w1ts.enable_w1ts = ..), which the compiler reads first; the HAL stores the word'),
    (0x60004028, 2, 0, 'the same for GPIO_ENABLE_W1TC (two input pins)'),
    (0x6000403c, 'poll', 'poll', 'GPIO_IN: the sense read, both builds (ESP-IDF gpio_get_level / HAL_SENSE_READ)'),
    (0x6000404c, 5, 3, 'GPIO_STATUS_W1TC bitfield stores: ESP-IDF\'s two extra interrupt disables (LED, sense) read before their store; the button\'s three are kept on ESP-IDF in both'),
    (0x60004074, 3, 1, 'GPIO_PIN0 read-modify-writes: ESP-IDF three (od / intr type / intr disable), the HAL one (PAD_DRIVER)'),
    (0x60004078, 3, 0, 'GPIO_PIN1: ESP-IDF\'s three for the sense pin; the HAL writes nothing there (see the writes)'),
    (0x60004080, 5, 4, 'GPIO_PIN3: ESP-IDF\'s od_disable read-modify-write is the one more; the interrupt setup is ESP-IDF in both'),
    (0x60004554, 0, 4, 'GPIO_FUNC0_OUT_SEL_CFG: the HAL\'s four field read-modify-writes; ESP-IDF writes the whole word without reading'),
    (0x60004558, 2, 2, 'GPIO_FUNC1_OUT_SEL_CFG: the output-enable-source read-modify-writes, both'),
    (0x60004560, 2, 2, 'GPIO_FUNC3_OUT_SEL_CFG: the same, both'),
    (0x60009004, 5, 3, 'IO_MUX_GPIO0: ESP-IDF five (FUN_IE off, two pull clears, MCU_SEL twice), the HAL three (two pull clears, MCU_SEL)'),
    (0x60009008, 5, 5, 'IO_MUX_GPIO1: five each (different mixes, see the writes)'),
    (0x60009010, 5, 5, 'IO_MUX_GPIO3: five each'),
]
VERDICTS = ('same', 'idf-only: ', 'hal-only: ', 'differs: ', 'kept on ESP-IDF: ')

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  <- ' + str(extra)[:400]) if (extra and not cond) else ''))


def _code_sha(text):
    """the header's C alone: comments (unit notes, trace digests, cites) removed, blank lines dropped"""
    import hashlib
    code = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return hashlib.sha256('\n'.join(l.rstrip() for l in code.splitlines() if l.strip()).encode()).hexdigest()


def _compile(header):
    try:
        from board.custom import engine_run as ER
        probe = '#include "polari_hal_esp32c3.h"\nvoid f(void) { HAL_LED_OUTPUT(); HAL_LED_SET_HIGH(); HAL_SENSE_INPUT(); HAL_SENSE_PULL_DOWN(); HAL_BUTTON_INPUT(); HAL_BUTTON_PULL_UP(); }\n' \
                'int g(void) { return HAL_SENSE_READ(); }\n'
        r = ER.run('riscv-gcc', ['-march=rv32imc', '-mabi=ilp32', '-Os', '-std=c11', '-ffreestanding', '-Wall', '-Wextra', '-Werror', '-S', '-o', 'p.s', 'p.c'],
                   files={'polari_hal_esp32c3.h': header.encode(), 'p.c': probe.encode()}, timeout=120)
    except Exception as e:  # noqa: BLE001
        return None, 'riscv-gcc refused: %s' % str(e)[:200]
    if r.get('returncode') != 0 or not (r.get('files') or {}).get('p.s'):
        return None, 'riscv-gcc ran but failed (rc %s): %s' % (r.get('returncode'), (r.get('stderr') or '')[:300])
    return r['files']['p.s'].decode(), '%s %s' % (r.get('how'), r.get('where'))


def run():
    from board.custom import gen_c3, variants_c3 as V
    ev = json.load(open(EVIDENCE))
    r = V.resolve(V.find('esp32c3-light'), {'pin_shim': 0})
    hdr = gen_c3.c3_hal_header(r)
    text = hdr['text']
    roles = {x['role']: x['pin'] for x in gen_c3.light_roles(r)}
    check('the light\'s roles are its knobs\' pins: LED GPIO0, SENSE GPIO1, BUTTON GPIO3 (variants_c3.LIGHT_KNOBS)', roles == {'LED': 'GPIO0', 'SENSE': 'GPIO1', 'BUTTON': 'GPIO3'}, roles)
    names = re.findall(r'^#define (HAL_(?:LED|SENSE|BUTTON)_\w+)\(\)', text, re.M)
    check('the header gives every role macro apps/light_hal.h calls', {'HAL_LED_OUTPUT', 'HAL_LED_PULL_NONE', 'HAL_LED_SET_HIGH', 'HAL_LED_SET_LOW', 'HAL_SENSE_INPUT',
                                                                          'HAL_SENSE_PULL_NONE', 'HAL_SENSE_PULL_DOWN', 'HAL_SENSE_READ', 'HAL_BUTTON_INPUT',
                                                                          'HAL_BUTTON_PULL_NONE', 'HAL_BUTTON_PULL_UP'} <= set(names), names)
    src = open(os.path.join(HERE, 'custom', 'firmware', 'esp32c3', 'apps', 'light_hal.h')).read()
    chip = src[src.index('#else /* the chip HAL */'):src.index('#endif /* PIN_SHIM */')]
    used = set(re.findall(r'\b(HAL_\w+)\s*\(', chip))
    check('the chip half calls only generated role macros, and no ESP-IDF pin call is left but the button interrupt\'s (gpio_set_intr_type / gpio_intr_enable / '
          'the ISR service)', used <= set(names) and not re.search(r'\bgpio_(config|set_level|get_level|set_direction|set_pull_mode)\s*\(', chip)
          and {'gpio_set_intr_type', 'gpio_intr_enable', 'gpio_install_isr_service', 'gpio_isr_handler_add'} <= set(re.findall(r'\b(gpio_\w+)\s*\(', chip)), sorted(used - set(names)))
    # ---- gate 1
    asm, how = _compile(text)
    if asm is None and 'refused' in how:
        print('  [SKIP] gate 1: riscv-gcc for the C3 header: %s' % how)
    else:
        check('gate 1: the generated header compiles standalone, rv32imc -Os -Werror (%s)' % how, asm is not None, how)
    # ---- gate 2: static - no read-modify-write touches a bit outside its field
    bad = []
    for m in re.finditer(r'\(\(\*\(volatile uint32_t \*\)(0x[0-9A-F]+)u\) & ~(0x[0-9A-F]+)UL\) \| \(\(uint32_t\)(\d+) << (\d+)\)', text):
        mask, val = int(m.group(2), 16), int(m.group(3)) << int(m.group(4))
        if val & ~mask:
            bad.append(m.group(0))
    rmws = len(re.findall(r'& ~0x[0-9A-F]+UL\) \|', text))
    check('gate 2 static: every field read-modify-write in the header (%d) writes its value inside its own mask, so every other bit is written back as read' % rmws,
          rmws >= 10 and not bad, bad[:2])
    # ---- gate 2: measured, both ways
    check('the evidence was measured with THIS header\'s C (code sha %s...; comments - cites, trace digests - may change): a changed RULES row or knob '
          'means re-measuring (tools/hal_evidence/c3_mmio_trace.sh), not a stale pass' % ev['builds']['hal']['hal_header_code_sha256'][:12],
          ev['builds']['hal']['hal_header_code_sha256'] == _code_sha(text), _code_sha(text))
    for row in WRITES:
        assert any(row[7] == v or row[7].startswith(v) for v in VERDICTS), row
    idf = {(int(a, 16), int(v, 16)): n for a, v, n in ev['builds']['idf']['writes']}
    hal = {(int(a, 16), int(v, 16)): n for a, v, n in ev['builds']['hal']['writes']}
    t_idf, t_hal = {}, {}
    for pin, a, v, ni, nh, *_ in WRITES:
        t_idf[(a, v)] = t_idf.get((a, v), 0) + ni
        t_hal[(a, v)] = t_hal.get((a, v), 0) + nh
    t_idf = {k: n for k, n in t_idf.items() if n}
    t_hal = {k: n for k, n in t_hal.items() if n}
    check('gate 2 ESP-IDF side: every measured write of the ESP-IDF build (%d kinds, %d writes) is a row of the table, counts exact' % (len(idf), sum(idf.values())),
          t_idf == idf, sorted(set(idf.items()) ^ set(t_idf.items())))
    check('gate 2 HAL side: every measured write of the HAL build (%d kinds, %d writes) is a row of the table, counts exact' % (len(hal), sum(hal.values())),
          t_hal == hal, sorted(set(hal.items()) ^ set(t_hal.items())))
    unexplained = [r for r in WRITES if r[3] != r[4] and r[7] == 'same']
    check('gate 2: a row whose two counts differ is never "same" - it names the missing op or the cited reason', not unexplained, unexplained)
    missing_ops = sorted({r[7].split(':', 1)[1].strip()[:40] for r in WRITES if r[7].startswith('idf-only')})
    check('gate 2: what the HAL does not do yet is named - the C3 int family (interrupt status / type / enable of the LED and sense pins), gpio.digital_input_off '
          '(FUN_IE 0 on the LED), and no driver kind on input pins', any('int family' in r[7] for r in WRITES) and any('digital_input_off' in r[7] for r in WRITES)
          and any('PAD_DRIVER cannot act' in r[7] for r in WRITES), missing_ops)
    ri = {int(a, 16): n for a, n in ev['builds']['idf']['reads']}
    rh = {int(a, 16): n for a, n in ev['builds']['hal']['reads']}
    check('gate 2 reads, both ways: every measured read of either build is a row, counts exact (GPIO_IN = the polling loop in both)',
          {a: ni for a, ni, nh, w in READS if ni} == ri and {a: nh for a, ni, nh, w in READS if nh} == rh,
          (sorted(set(ri.items()) ^ {(a, ni) for a, ni, nh, w in READS if ni}), sorted(set(rh.items()) ^ {(a, nh) for a, ni, nh, w in READS if nh})))
    led_matrix = [(r[2], r[4]) for r in WRITES if r[1] == 0x60004554]
    check('gate 2 (pol\'s pad-function point): the HAL\'s gpio.output selects the GPIO function (MCU_SEL 1) and routes the matrix (OUT_SEL 128) - measured, so a pad that '
          'resets to JTAG / USB-Serial-JTAG still becomes a GPIO', hal.get((0x60009004, 0x1000)) == 1 and (0x80, 1) in led_matrix, led_matrix)
    check('the measured caveat is kept with the evidence: the stub reads 0, so the clears come from the ESP-IDF source, not from values',
          'read returns 0' in ev['caveat'] and 'source' in ev['caveat'], ev['caveat'][:80])
    # ---- gate 3
    g3 = ev['shim1_app_bin']
    check('gate 3 NO COLLATERAL CHANGE: the PIN_SHIM 1 (twin) app.bin differs in %d bytes, all inside its hash fields (app_elf_sha256 177-208; the image\'s checksum byte '
          'and appended SHA-256) - every loaded byte identical' % g3['differing_bytes'], g3['differing_bytes'] == 64
          and all(177 <= a and b <= 208 or a >= g3['size'] - 32 for a, b in g3['ranges_1based']), g3['ranges_1based'])
    # ---- gate 4
    check('gate 4 SAID: the chip HAL has not run on a chip and QEMU\'s GPIO is a stub - the file says so', 'has NOT run on a chip' in src and 'register stub' in src)
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    import sys
    sys.exit(0 if run() else 1)
