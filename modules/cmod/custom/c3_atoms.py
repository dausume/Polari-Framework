"""
@module cmod.custom.c3_atoms

THE ESP32-C3 FIRMWARE AS ATOMS (his ask 2026-10-29: "C3 firmware parsed into atoms, so its pins can show the code that uses them"). The C3 project
(board/custom/firmware/esp32c3) is ESP-IDF + FreeRTOS C - not a cmod TEMPLATE (cmod's UNO pipeline renders through board.custom.gen and measures with avr-gcc) - so
this module gives it its OWN path into the SAME manifest schema (`polari-firmware.json`, committed beside the sources) and the SAME rows (cmod.custom.rows.project_rows):

  render   board.custom.gen_c3 renders the esp32c3-light configuration with pin_shim=0 - the CHIP HAL (light_hal.h's gpio-driver half; the twin's RAM pin shim is
           not hardware and is left out, said) - so the generated board_config.h / board_pins.h / <class>_packets.h are the real ones
  parse    cmod.custom.preprocess with the C3's own fake headers (c3_fake_headers: ESP-IDF / FreeRTOS stand-ins, RV32 widths) + pycparser; cmod.custom.scan.BodyScan
           for globals and calls; c_types under the RV32 ABI (struct widths: padding not computed -> 0, never a wrong sum)
  registers  the C3 firmware NAMES no register - it calls the ESP-IDF drivers - so each driver call is mapped to the registers it reaches, every link CITED to
           ESP-IDF v5.5.5's own source in the prf-esp-engines image (file:line of the driver, the hal macro and the low-level line that touches the register;
           API_REGISTERS below). A pin-indexed register (GPIO_PINn, IO_MUX_GPIOn ...) takes n from the call's pin macro
  pins     the RAW body of each atom is read for the pin macros (LED_GPIO, BUTTON_GPIO, SENSE_GPIO, POLARI_FRAME_TX/RX_GPIO - board_config.h / board_pins.h): a
           macro the body names = `declared <HAL variable>` (LED_GPIO -> LED_PIN ...), the same resource the UNO's POLARI_NODE uses() gives (the preprocessor has
           already turned the macro into its number in the AST, so the raw text is the evidence; said per resource)
  cost     NOT measured (no riscv size / stack pass here): every atom says so - never a number
"""
import hashlib
import json
import os
import re
import shutil
import tempfile

from pycparser import c_ast, c_parser

from cmod.custom import c3_fake_headers as F
from cmod.custom.c_types import RV32_ABI, TypeTable, polari_type
from cmod.custom.preprocess import preprocess
from cmod.custom.scan import BodyScan

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.join(MODULES, 'board', 'custom', 'firmware', 'esp32c3')
ROOT_REL = 'board/custom/firmware/esp32c3'
MANIFEST = os.path.join(ROOT, 'polari-firmware.json')
PROJECT, VARIANT = 'c3', 'esp32c3-light'
IDF = 'ESP-IDF v5.5.5 (/opt/esp/idf in prf-esp-engines:noble)'

#: rendered file -> (module name, the source file it is copied from)
MODULE_OF = {'app.c': ('apps/light', 'apps/light.c'), 'light_hal.h': ('apps/light_hal', 'apps/light_hal.h'), 'polari_c3.c': ('main/polari_c3', 'main/polari_c3.c'),
             'polari_c3.h': ('main/polari_c3', 'main/polari_c3.h'), 'polari_trace.c': ('main/polari_trace', 'main/polari_trace.c'),
             'polari_trace.h': ('main/polari_trace', 'main/polari_trace.h')}
SOURCES = ('app.c', 'polari_c3.c', 'polari_trace.c')
#: the pin macros -> the HAL variable (cmod.custom.catom_variables esp32c3-light) the value IS
PIN_MACROS = {'LED_GPIO': 'LED_PIN', 'BUTTON_GPIO': 'BUTTON_PIN', 'SENSE_GPIO': 'SENSE_PIN', 'POLARI_FRAME_TX_GPIO': 'UART0_TX_PIN', 'POLARI_FRAME_RX_GPIO': 'UART0_RX_PIN'}

_G, _U, _T = 'components/esp_driver_gpio/src/gpio.c', 'components/esp_driver_uart/src/uart.c', 'components/esp_timer/src/esp_timer_impl_systimer.c'
_GLL, _ULL, _SLL, _GHAL = 'components/hal/esp32c3/include/hal/gpio_ll.h', 'components/hal/esp32c3/include/hal/uart_ll.h', 'components/hal/esp32c3/include/hal/systimer_ll.h', 'components/hal/include/hal/gpio_hal.h'
#: driver call -> [(register (registers_esp32c3 name; '{n}' = the pad of the call's pin macro), access, the cited chain)]
API_REGISTERS = {
    'gpio_set_level': [('GPIO_OUT_W1TS_REG', 'w', '%s:245-248 gpio_set_level -> %s:225 gpio_hal_set_level -> %s:310 gpio_ll_set_level: hw->out_w1ts' % (_G, _GHAL, _GLL)),
                       ('GPIO_OUT_W1TC_REG', 'w', '%s:310 gpio_ll_set_level: hw->out_w1tc (level 0)' % _GLL)],
    'gpio_get_level': [('GPIO_IN_REG', 'r', '%s:252-254 gpio_get_level -> %s:239 gpio_hal_get_level -> %s:332 gpio_ll_get_level: hw->in.data' % (_G, _GHAL, _GLL))],
    'gpio_config': [('IO_MUX_GPIO{n}_REG', 'w', '%s:347 gpio_config -> gpio_input_enable / gpio_pullup_en / gpio_pulldown_en -> %s:199 / :46 / :75 '
                                                '(FUN_IE, FUN_PU, FUN_PD of IO_MUX_GPIOn); gpio_output_enable -> %s:293 gpio_ll_func_sel (MCU_SEL)' % (_G, _GLL, _GLL)),
                    ('GPIO_ENABLE_W1TS_REG', 'w', '%s:222-227 gpio_output_enable -> %s:245 gpio_ll_output_enable: hw->enable_w1ts' % (_G, _GLL)),
                    ('GPIO_FUNC{n}_OUT_SEL_CFG_REG', 'w', '%s:225 gpio_hal_matrix_out_default (no peripheral output routed: simple GPIO, 128)' % _G),
                    ('GPIO_PIN{n}_REG', 'w', '%s:414 gpio_set_intr_type -> %s:99 gpio_ll_set_intr_type: hw->pin[n].int_type; gpio_intr_enable -> %s:162 int_ena' % (_G, _GLL, _GLL))],
    'gpio_install_isr_service': [('INTERRUPT_CORE0_GPIO_INTERRUPT_PRO_MAP_REG', 'w', '%s:532-543 gpio_install_isr_service -> gpio_isr_register -> %s:612 esp_intr_alloc '
                                                                                 '(the GPIO interrupt source, mapped to a CPU interrupt by the interrupt matrix)' % (_G, _G))],
    'gpio_isr_handler_add': [('GPIO_PIN{n}_REG', 'w', '%s:559-569 gpio_isr_handler_add -> gpio_intr_enable_on_core -> %s:162 gpio_ll_intr_enable_on_core: pin[n].int_ena' % (_G, _GLL))],
    'uart_param_config': [('UART0_CLKDIV_REG', 'w', '%s:994-1035 uart_param_config -> uart_hal_set_baudrate (%s:223 uart_ll_set_baudrate)' % (_U, _ULL)),
                          ('UART0_CONF0_REG', 'w', '%s:1046-1048 uart_hal_set_parity / set_data_bit_num / set_stop_bits' % _U),
                          ('SYSTEM_PERIP_CLK_EN0_REG', 'w', '%s:1007 -> :213 uart_module_enable -> %s:88-92 uart_ll_enable_bus_clock: SYSTEM.perip_clk_en0.reg_uart_clk_en' % (_U, _ULL)),
                          ('SYSTEM_PERIP_RST_EN0_REG', 'w', '%s:213 uart_module_enable -> %s:109-114 uart_ll_reset_register: SYSTEM.perip_rst_en0.reg_uart_rst' % (_U, _ULL))],
    'uart_driver_install': [('INTERRUPT_CORE0_UART_INTR_MAP_REG', 'w', '%s:1935-1995 uart_driver_install -> esp_intr_alloc_intrstatus (the UART source)' % _U),
                            ('SYSTEM_PERIP_CLK_EN0_REG', 'w', '%s:1991 uart_module_enable -> %s:88-92 SYSTEM.perip_clk_en0.reg_uart_clk_en' % (_U, _ULL))],
    'uart_write_bytes': [('UART0_FIFO_REG', 'w', '%s:1629-1634 uart_write_bytes -> uart_tx_all -> %s:1142 uart_hal_write_txfifo -> %s:365-371 uart_ll_write_txfifo: hw->ahb_fifo' % (_U, _U, _ULL))],
    'uart_read_bytes': [('UART0_FIFO_REG', 'r', '%s:1665 uart_read_bytes reads the driver\'s RX ring, filled by its ISR: %s:1281 uart_hal_read_rxfifo -> %s:349-352 uart_ll_read_rxfifo: hw->ahb_fifo'
                         % (_U, _U, _ULL))],
    'uart_set_pin': [('GPIO_FUNC{tx}_OUT_SEL_CFG_REG', 'w', '%s:879 uart_set_pin -> esp_rom_gpio_connect_out_signal (the TX pad\'s output select)' % _U),
                     ('GPIO_FUNC6_IN_SEL_CFG_REG@rx', 'w', '%s:905 uart_set_pin -> esp_rom_gpio_connect_in_signal (U0RXD_in = signal 6)' % _U)],
    'esp_timer_get_time': [('SYSTIMER_UNIT0_OP_REG', 'w', '%s:68-75 esp_timer_get_time = esp_timer_impl_get_time -> systimer_hal_get_counter_value(SYSTIMER_COUNTER_ESPTIMER = 0, '
                                                          'esp_private/systimer.h:30) -> %s:88-90 systimer_ll_counter_snapshot: unit_op[0].timer_unit_update' % (_T, _SLL)),
                           ('SYSTIMER_UNIT0_VALUE_HI_REG', 'r', '%s:109 systimer_ll_get_counter_value_high (unit 0)' % _SLL),
                           ('SYSTIMER_UNIT0_VALUE_LO_REG', 'r', '%s systimer_ll_get_counter_value_low (unit 0)' % _SLL)],
}
#: the driver calls whose FIRST argument is a pin (gpio_num) - every other call's first argument is not read as one (gpio_install_isr_service's is a flag word)
PIN_ARG_CALLS = ('gpio_set_level', 'gpio_get_level', 'gpio_isr_handler_add', 'gpio_set_intr_type', 'gpio_intr_enable')
#: the ESP-IDF constants an argument may be (driver/uart.h): UART_PIN_NO_CHANGE = -1 - "leave this pin as it is"
CONSTANTS = {'UART_PIN_NO_CHANGE': -1}
#: FreeRTOS / ESP-IDF calls that touch a resource other than a register (by name prefix) -> the resource word
LIB_RESOURCES = {'xTaskCreate': 'FreeRTOS task', 'vTaskDelay': 'FreeRTOS scheduler', 'vTaskDelayUntil': 'FreeRTOS scheduler', 'xQueue': 'FreeRTOS queue',
                 'xSemaphore': 'FreeRTOS semaphore', 'ulTaskNotifyTake': 'FreeRTOS task notification', 'xTaskNotifyGive': 'FreeRTOS task notification',
                 'vTaskNotifyGiveFromISR': 'FreeRTOS task notification (ISR)', 'nvs_': 'NVS flash', 'esp_partition_': 'flash partition', 'esp_cpu_get_cycle_count': 'CPU cycle counter (mcycle)'}
LIB_MEMORY = ('memcpy', 'memset', 'memmove', 'memcmp', 'strcpy', 'strncpy', 'strlen', 'strcmp', 'strncmp', 'vsnprintf', 'snprintf')


def _sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def _render(work):
    from board.custom import gen_c3
    return gen_c3.gen_c3(VARIANT, work, pin_shim=0)['project_dir']


def _defines(main_dir):
    """{macro: int value}: the numeric #defines of the rendered headers and sources (LED_GPIO 0, POLARI_TRACE_TX_GPIO 4 ...) and the UART port aliases
    (FRAME_UART = UART_NUM_0 -> 0, TRACE_UART = UART_NUM_1 -> 1), resolved through UART_NUM_<n>."""
    out = {}
    for h in sorted(os.listdir(main_dir)):
        if h.endswith(('.h', '.c')):
            for m in re.finditer(r'^#define\s+(\w+)\s+(\S+)', open(os.path.join(main_dir, h)).read(), re.M):
                name, val = m.group(1), m.group(2)
                if re.fullmatch(r'\d+', val):
                    out.setdefault(name, int(val))
                elif re.fullmatch(r'UART_NUM_(\d)', val):
                    out.setdefault(name, int(val[-1]))
    return out


def _calls_in(raw, name):
    """[[arg text, ...], ...] for every call of `name` in the raw body (top-level commas split)."""
    out = []
    for m in re.finditer(r'\b%s\s*\(' % re.escape(name), raw):
        i, depth, cur, args = m.end(), 1, '', []
        while i < len(raw) and depth:
            ch = raw[i]
            if ch in '([{':
                depth += 1
            elif ch in ')]}':
                depth -= 1
            if depth == 1 and ch == ',':
                args.append(cur.strip())
                cur = ''
            elif depth:
                cur += ch
            i += 1
        args.append(cur.strip())
        out.append(args)
    return out


def _value(tok, defines):
    """An argument's value: a number, a #define, UART_NUM_<n>; else None."""
    tok = tok.strip().lstrip('(').rstrip(')')
    if tok in CONSTANTS:
        return CONSTANTS[tok]
    if re.fullmatch(r'-?\d+', tok):
        return int(tok)
    if re.fullmatch(r'UART_NUM_(\d)', tok):
        return int(tok[-1])
    return defines.get(tok)


def _raw_body(path, line):
    """The source text of the function starting at `line` (1-based) - from its line to the brace that closes it."""
    lines = open(path).read().split('\n')[line - 1:]
    depth, seen, out = 0, False, []
    for ln in lines:
        out.append(ln)
        depth += ln.count('{') - ln.count('}')
        seen = seen or '{' in ln
        if seen and depth <= 0:
            break
    return '\n'.join(out)


def _lib(name):
    if name in LIB_MEMORY:
        return ''
    return next((v for k, v in LIB_RESOURCES.items() if name == k or name.startswith(k)), '')


def _pads_of_config(var, raw, defines):
    """gpio_config(&var): the pin(s) and what the config sets, read from `var`'s initializer in the raw body."""
    m = re.search(r'gpio_config_t\s+%s\s*=\s*\{([^}]*)\}' % re.escape(var), raw)
    if not m:
        return [], set()
    init = m.group(1)
    pads = [defines[x] for x in re.findall(r'1ULL\s*<<\s*(\w+)', init) if x in defines]
    sets = {k for k, w in (('output', 'GPIO_MODE_OUTPUT'), ('pull', '_en ='), ('intr', '.intr_type')) if w in init}
    return pads, sets


def _call_registers(call, raw, defines, params, callers):
    """[(register, access, cite, how)] for ONE driver call of an atom, judged on that call's own arguments; a port / pin that is a PARAMETER is resolved through
    the atom's callers (their raw calls); an unresolved one is said, never guessed."""
    out = []
    spec = API_REGISTERS.get(call)
    if not spec:
        return out
    occurrences = _calls_in(raw, call)
    if not occurrences:
        # the AST has the call but the raw text does not spell it (a macro expands to it): judged with no arguments, said
        occurrences = [None]
    for args in occurrences:
        if args is None:
            for reg, acc, cite in spec:
                if '{' not in reg and not reg.endswith('@rx'):
                    out.append((reg, acc, cite, 'through a macro the body uses (the raw text does not spell the call)'))
            continue
        if call.startswith('uart_'):
            # each binding = one way this call runs: its own constants, or (an argument that is a PARAMETER) ONE caller's values - port and pins from the SAME caller
            if any(a in params for a in args):
                binds = [({a: c[params.index(a)] for a in args if a in params}, 'via a caller passing %s' % ', '.join(c[params.index(a)] for a in args if a in params))
                         for c in callers]
                if not binds:
                    out.append(('(%s: its port / pin parameters have no caller to resolve them)' % call, '', '', ''))
            else:
                binds = [({}, '')]
            for env, how in binds:
                val = lambda a: _value(env.get(a, a), defines)   # noqa: E731
                port = val(args[0]) if args else None
                if port is None:
                    out.append(('(UART port not resolved)', '', 'the port argument %r is neither a constant nor a caller-fixed parameter' % (args[0] if args else ''), how))
                    continue
                if port != 0:
                    out.append(('(UART%s - its registers are not ingested)' % port, '', 'rm-2b ingested UART0 only', ('port %s %s' % (env.get(args[0], args[0]), how)).strip()))
                    continue
                if call == 'uart_set_pin':
                    tx, rx = (val(args[1]) if len(args) > 1 else None), (val(args[2]) if len(args) > 2 else None)
                    for reg, acc, cite in spec:
                        if '{tx}' in reg and tx is not None and tx >= 0:
                            out.append((reg.replace('{tx}', str(tx)), acc, cite, 'TX pin %s %s' % (tx, how)))
                        elif reg.endswith('@rx') and rx is not None and rx >= 0:
                            out.append((reg[:-3], acc, cite, 'RX pin %s %s' % (rx, how)))
                    continue
                for reg, acc, cite in spec:
                    out.append((reg, acc, cite, ('port %s %s' % (env.get(args[0], args[0]), how)).strip()))
            continue
        pads, sets = [], {'output', 'pull', 'intr'}
        if call == 'gpio_config' and args:
            pads, sets = _pads_of_config(args[0].lstrip('&').strip(), raw, defines)
        elif call in PIN_ARG_CALLS and args and _value(args[0], defines) is not None:
            pads = [_value(args[0], defines)]
        for reg, acc, cite in spec:
            if call == 'gpio_config':
                if 'ENABLE' in reg or 'OUT_SEL' in reg:
                    if 'output' not in sets:
                        continue
                if 'GPIO_PIN{n}' in reg and 'intr' not in sets:
                    continue
            if '{n}' in reg:
                for n in pads or []:
                    out.append((reg.replace('{n}', str(n)), acc, cite, 'pin %s' % n))
                if not pads:
                    out.append(('(%s: the pin argument is not resolved)' % reg.replace('{n}', 'n'), '', cite, ''))
            else:
                out.append((reg, acc, cite, ('pin %s' % pads[0]) if pads else ''))
    return out


def _atoms_of(path, main_dir, defines, params_of=None, raw_of=None):
    text, problems = preprocess(path, [main_dir], fake_dirs=[F.fake_dir()])
    ast = c_parser.CParser().parse(text, os.path.basename(path))
    types = TypeTable(ast, RV32_ABI)
    gl = {}
    for ext in ast.ext:
        if isinstance(ext, c_ast.Decl) and ext.name and not isinstance(ext.type, c_ast.FuncDecl):
            d = types.describe(ext.type)
            d['file'] = ext.coord.file if ext.coord else ''
            gl[ext.name] = d
    out = []
    for ext in ast.ext:
        if not isinstance(ext, c_ast.FuncDef):
            continue
        fname, file_ = ext.decl.name, os.path.basename(ext.coord.file)
        if file_ not in MODULE_OF:
            continue   # a generated header (<class>_packets.h) is library, as for the UNO
        s = BodyScan(ext, gl, {}, types)
        raw = (raw_of or {}).get((file_, fname)) or _raw_body(os.path.join(main_dir, file_), ext.coord.line)
        params_of = params_of or {}

        def callers_of(fn, here=(file_, fname)):
            return [args for other, body in (raw_of or {}).items() if other != here for args in _calls_in(body, fn)]
        macros = sorted({m for m in PIN_MACROS if re.search(r'\b%s\b' % m, raw)})
        res = []
        for g, a in sorted(s.g.items()):
            res.append({'kind': 'global', 'name': g, 'access': ('r' if a.get('r') else '') + ('w' if a.get('w') else ''), 'peripheral': '', 'detail': gl.get(g, {}).get('c', '')})
        for m in macros:
            res.append({'kind': 'declared', 'name': PIN_MACROS[m], 'access': '', 'peripheral': '',
                        'detail': 'the raw body names %s (= %s, the HAL value %s: board_config.h / board_pins.h) - read from the source text, the AST has its number'
                                  % (m, defines.get(m, '?'), PIN_MACROS[m])})
        seen = set()
        for call in dict.fromkeys(s.calls):
            for r, acc, cite, how in _call_registers(call, raw, defines, params_of.get((file_, fname), []), callers_of(fname)):
                if (r, acc) in seen:
                    continue
                seen.add((r, acc))
                res.append({'kind': 'register' if not r.startswith('(') else 'note', 'name': r, 'access': acc, 'peripheral': '',
                            'detail': 'through %s() %s: %s (%s)' % (call, how, cite, IDF)})
            lib = _lib(call)
            if lib and ('library', call) not in seen:
                seen.add(('library', call))
                res.append({'kind': 'library', 'name': call, 'access': 'call', 'peripheral': lib, 'detail': 'ESP-IDF / FreeRTOS'})
        ftype = ext.decl.type
        ports = []
        for p in (ftype.args.params if ftype.args else []):
            if isinstance(p, c_ast.Decl) and p.name:
                d = types.describe(p.type)
                ports.append({'name': p.name, 'direction': 'in', 'ctype': d['c'], 'width_bytes': d.get('width', 0), 'polari_type': polari_type(d), 'unit': '',
                              'meaning': '', 'source': 'derived: parameter'})
        ret = types.describe(ftype.type)
        if ret.get('kind') != 'void':
            ports.append({'name': 'return', 'direction': 'out', 'ctype': ret['c'], 'width_bytes': ret.get('width', 0), 'polari_type': polari_type(ret), 'unit': '',
                          'meaning': '', 'source': 'derived: return value'})
        touched = [r['name'] for r in res if r['kind'] in ('global', 'register', 'library')]
        module, src_rel = MODULE_OF[file_]
        out.append({'name': '%s.%s' % (module, fname), 'function': fname, 'module': src_rel, 'line': ext.coord.line, 'kind': 'function', 'isr_vector': '',
                    'signature': '%s %s(%s)' % (ret['c'], fname, ', '.join('%s %s' % (x['ctype'], x['name']) for x in ports if x['direction'] == 'in') or 'void'),
                    'static': 'static' in (ext.decl.storage or []), 'signature_varies': False, 'ports': ports, 'resources': res, 'calls': list(dict.fromkeys(s.calls)),
                    'pure': not touched and not s.calls, 'pure_why': ('touches %s' % ', '.join(touched[:6])) if touched else ('calls %s' % ', '.join(s.calls[:4]) if s.calls else ''),
                    'isr_safe': 'undetermined', 'isr_safe_why': 'cmod\'s ISR-safety rules are the AVR\'s (ATOMIC_BLOCK, one-byte reads); the FreeRTOS build\'s tasks / '
                                                                 'critical sections / ISR notifications are not analysed by them',
                    'atomic_block': False, 'configs': [VARIANT], 'annotation': None,
                    'cost': {'why': 'not measured: cmod measures avr-gcc builds; no riscv32-esp-elf size / stack pass for the C3 yet'}, 'title': '', 'notes': ''})
    return out, problems


def _funcdefs(path, main_dir):
    text, _p = preprocess(path, [main_dir], fake_dirs=[F.fake_dir()])
    ast = c_parser.CParser().parse(text, os.path.basename(path))
    out = []
    for ext in ast.ext:
        if isinstance(ext, c_ast.FuncDef) and os.path.basename(ext.coord.file) in MODULE_OF:
            ps = [p.name for p in (ext.decl.type.args.params if ext.decl.type.args else []) if isinstance(p, c_ast.Decl) and p.name]
            out.append({'name': ext.decl.name, 'file': os.path.basename(ext.coord.file), 'line': ext.coord.line, 'params': ps})
    return out


def generate():
    """-> the manifest dict (deterministic: no timestamp - regenerating unchanged sources gives the same bytes)."""
    work = tempfile.mkdtemp(prefix='cmod-c3-')
    try:
        main_dir = os.path.join(_render(work), 'main')
        defines = _defines(main_dir)
        raw_of, params_of = {}, {}
        for f in SOURCES:
            for fd in _funcdefs(os.path.join(main_dir, f), main_dir):
                # keyed by (file, name): two TUs may each define a static function of one name (telemetry_task in app.c AND polari_c3.c)
                raw_of.setdefault((fd['file'], fd['name']), _raw_body(os.path.join(main_dir, fd['file']), fd['line']))
                params_of.setdefault((fd['file'], fd['name']), fd['params'])
        atoms, problems = [], []
        for f in SOURCES:
            a, p = _atoms_of(os.path.join(main_dir, f), main_dir, defines, params_of, raw_of)
            atoms += a
            problems += ['%s: %s' % (f, x) for x in p]
        atoms.sort(key=lambda a: a['name'])
        mods = {}
        for a in atoms:
            mods.setdefault(a['name'].rsplit('.', 1)[0], []).append(a['name'])
        modules = []
        for name, names in sorted(mods.items()):
            srcs = sorted({src for _r, (m, src) in MODULE_OF.items() if m == name})
            modules.append({'name': name, 'role': 'hal' if name == 'apps/light_hal' else 'app' if name.startswith('apps/') else 'runtime',
                            'files': [{'path': s, 'sha256': _sha(os.path.join(ROOT, s))} for s in srcs], 'atoms': names})
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {'schema': 'polari-firmware/1', 'project': PROJECT, 'kind': 'idf', 'title': 'ESP32-C3 firmware (board module, ESP-IDF + FreeRTOS)', 'description': '',
            'notes': 'parsed by cmod.custom.c3_atoms (the chip HAL: pin_shim=0); registers through the ESP-IDF drivers, cited; cost not measured',
            'root': ROOT_REL, 'board': 'esp32-c3', 'mcu': 'esp32c3',
            'parser': {'engine': 'pycparser + cmod.custom.c3_fake_headers', 'version': __import__('pycparser').__version__, 'fake_headers_sha256': F.sha(), 'abi': RV32_ABI['name']},
            'build': {'cc': 'riscv32-esp-elf-gcc (ESP-IDF, prf-esp-engines)', 'cc_version': '', 'cflags': []},
            'configurations': [{'name': VARIANT, 'flags': ['PIN_SHIM=0']}], 'modules': modules, 'atoms': atoms,
            'counts': {'atoms': len(atoms), 'annotated': 0, 'isr': 0, 'pure': sum(a['pure'] for a in atoms), 'not_isr_safe': 0},
            'problems': problems, 'annotated_not_compiled': [], 'derived_by': 'cmod.custom.c3_atoms generate - never edit by hand', 'conformed_at': ''}


def conform(write=True):
    m = generate()
    if write:
        with open(MANIFEST, 'w') as fh:
            json.dump(m, fh, indent=1, sort_keys=False)
            fh.write('\n')
    return m


def rows():
    """The C3's CProject / CModule / CFunctionAtom / CPort rows from the COMMITTED manifest ({} of empty lists when it is absent)."""
    from cmod.custom import rows as RW
    if not os.path.isfile(MANIFEST):
        return {'CProject': [], 'CModule': [], 'CFunctionAtom': [], 'CPort': []}
    return RW.project_rows(json.load(open(MANIFEST)), MANIFEST)


if __name__ == '__main__':
    m = conform()
    print('%d atoms -> %s' % (len(m['atoms']), MANIFEST))
