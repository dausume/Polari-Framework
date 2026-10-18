"""
@module board.custom.soc_functions

c3pf: WHAT A FIRMWARE TASK KIND MEANS ON A SoC WHOSE FUNCTIONS ARE PinFunction ROWS (the ESP32-C3). The UNO's kinds are read off alternate-function NAMES (INT0, OC1A,
ADC3, RXD ...), hard-coded in target_compat / ladder / isotope_variants_eligibility / solve_needs. The ESP32-C3 names its functions after the GPIO matrix's
signals (U0TXD_out, ledc_ls_sig_out0, FSPID_out ...) and reaches almost any signal on almost any pad, so a kind is a PATTERN over the PinFunction function names:

  digital-in / digital-out   the pad's GPIO function (every pad: datasheet Table 2-4, F1 = GPIOn)
  interrupt-in               GPIO_INT: every pad can raise an edge/level interrupt (TRM Register 5.14 GPIO_PINn_INT_TYPE p.184; datasheet §4.1.3.1 p.36)
  analog-in                  an ADCx_CHy analog function - only GPIO0-5 (datasheet Table 2-6 p.21), fixed
  pwm-out                    an LEDC output signal ledc_ls_sig_out0..5 (TRM Table 5.11-1 signals 45-50, p.170-171), through the matrix - any pad
  uart-tx / uart-rx          U0TXD / U1TXD_out ... (the IO MUX pads GPIO21 / GPIO20, else the matrix)
  i2c-sda / i2c-scl          I2CEXT0_SDA / SCL (matrix, signals 53-54)
  spi-mosi / -miso / -sck / -ss   SPI2's FSPID / FSPIQ / FSPICLK / FSPICS0 (IO MUX on GPIO7/2/6/10, else the matrix; Table 2-7 note 2: any pad)

The comparator kind does not exist on the C3 (no analog comparator in the datasheet's peripheral list, p.4 and §4.2 pp.46-50): the route is BLOCKED by name there.
`compatible()` answers target_compat's question for such a SoC from the pad's function names (the PinFunction rows when the caller has them, else the same builders).
"""
import fnmatch
import json
import re

#: SoCs whose function vocabulary is the PinFunction rows' (the UNO keeps the alternate-function names in target_compat / ladder)
VOCAB = {
    'esp32c3': {
        'digital-in': ['GPIO'], 'digital-out': ['GPIO'], 'interrupt-in': ['GPIO_INT'], 'analog-in': ['ADC?_CH?'], 'pwm-out': ['ledc_ls_sig_out?'],
        'uart-rx': ['U?RXD', 'U?RXD_in'], 'uart-tx': ['U?TXD', 'U?TXD_out'], 'i2c-sda': ['I2CEXT0_SDA_in'], 'i2c-scl': ['I2CEXT0_SCL_in'],
        'spi-mosi': ['FSPID', 'FSPID_out'], 'spi-miso': ['FSPIQ', 'FSPIQ_in'], 'spi-sck': ['FSPICLK', 'FSPICLK_out_mux'], 'spi-ss': ['FSPICS0', 'FSPICS0_out']},
}
#: the order a function name is tried against the kinds (a name matches the first kind whose patterns it fits)
KIND_ORDER = ('digital-in', 'interrupt-in', 'analog-in', 'pwm-out', 'uart-tx', 'uart-rx', 'i2c-sda', 'i2c-scl', 'spi-mosi', 'spi-miso', 'spi-sck', 'spi-ss')
#: block kind a variant names -> the Peripheral.kind that satisfies it, per SoC (the C3's GPIO interrupt serves both the UNO's INT and PCINT blocks; LEDC is its timer-pwm)
PERIPHERAL_KIND = {'esp32c3': {'gpio-port': 'gpio-port', 'exint': 'gpio-int', 'pcint': 'gpio-int', 'adc': 'adc', 'comparator': 'comparator', 'spi': 'spi', 'twi': 'twi',
                               'timer-pwm': 'timer', 'usart': 'usart'}}
#: how the SoC's scarce function families are told apart (spec cost = how many pads carry a family; the matrix families are on every pad, so not scarce)
FAMILIES = {'esp32c3': (('adc', re.compile(r'^ADC\d_CH\d$')), ('jtag', re.compile(r'^MT(MS|DI|CK|DO)$')), ('usb', re.compile(r'^USB_D[+-]$')),
                        ('uart0-iomux', re.compile(r'^U0(RXD|TXD)$')), ('spi2-iomux', re.compile(r'^FSPI(Q|D|HD|WP|CLK|CS0)$')),
                        ('flash-spi', re.compile(r'^SPI(Q|D|HD|WP|CLK|CS0)$')), ('xtal32k', re.compile(r'^XTAL_32K_[PN]$')),
                        ('strapping', re.compile(r'^@strapping$')))}   # '@strapping' is a tag the solver's pin universe adds to a pad with a `reset`-phase lifecycle row (lifecycle_c3), not a function
#: where each SoC says it has no comparator: the datasheet's own enumeration of the peripherals
NO_COMPARATOR = {'esp32c3': 'the ESP32-C3 datasheet lists its peripherals (Features, p.4: GPIOs, two UARTs, three SPI, I2C, I2S, USB Serial/JTAG, TWAI, LED PWM, RMT, two SAR ADCs, '
                            'temperature sensor, timers and watchdogs) and §4.2 Peripherals (pp.46-50) describes them: no analog comparator is among them (the "comparators" it names are '
                            'the system timer\'s alarm comparators, §4.1.3.5 p.38)'}
_CACHE = {}


def has_vocab(soc):
    return soc in VOCAB


def kind_patterns(soc, kind):
    """The function-name patterns a kind needs on `soc`, or None when the SoC keeps the UNO-style names."""
    v = VOCAB.get(soc)
    return None if v is None else v.get(kind)


def function_kind(soc, fn):
    """The task kind a function name serves on `soc` ('' = none)."""
    v = VOCAB.get(soc) or {}
    for kind in KIND_ORDER:
        if any(fnmatch.fnmatchcase(fn, p) for p in v.get(kind, ())):
            return kind
    return ''


def family(soc, fn):
    return next((name for name, rx in FAMILIES.get(soc, ()) if rx.match(fn)), None)


def _derived_c3():
    """The ESP32-C3's derived (matrix-routed) PinFunction rows, built ONCE per process from the same static builders the seed uses ({soc_pin name: [row]}, in pad order)."""
    if ('esp32c3', 'derived') not in _CACHE:
        from board.custom import board_c3 as C
        from board.custom import hardware_chain_c3 as H
        sps = C.soc_pins()
        sig = H.signals(sps)
        by = {}
        for f in H.matrix_pin_functions(sps, sig, C.board_pins()):
            by.setdefault(f['soc_pin'], []).append(f)
        _CACHE[('esp32c3', 'derived')] = by
    return _CACHE[('esp32c3', 'derived')]


def _fixed_c3():
    """The C3's stored (fixed) rows as the builders make them - the fallback of a caller that holds no tables ({soc_pin name: [row]})."""
    if ('esp32c3', 'fixed') not in _CACHE:
        from board.custom import board_c3 as C
        from board.custom import hardware_chain_c3 as H
        sps = C.soc_pins()
        by = {}
        for f in H.fixed_pin_functions(sps, H.signals(sps)):
            by.setdefault(f['soc_pin'], []).append(f)
        _CACHE[('esp32c3', 'fixed')] = by
    return _CACHE[('esp32c3', 'fixed')]


#: SoCs whose GPIO-matrix-routed PinFunction rows are DERIVED on read, not stored (soc -> builder of {soc_pin name: [row]})
DERIVED = {'esp32c3': _derived_c3}


def derived_names(soc=None):
    """The names of the rows `pin_functions` derives (for the retirement step and the proofs)."""
    return {f['name'] for s, fn in DERIVED.items() if soc in (None, s) for rows in fn().values() for f in rows}


def derived_row(soc, soc_pin, fn):
    """One derived PinFunction row of (SocPin name, function), or None (an indexed lookup: the ladder asks for one row at a time)."""
    if soc not in DERIVED:
        return None
    if (soc, 'index') not in _CACHE:
        _CACHE[(soc, 'index')] = {(f['soc_pin'], f['function']): f for rows in DERIVED[soc]().values() for f in rows}
    return _CACHE[(soc, 'index')].get((soc_pin, fn))


def pin_functions(tables, soc=None):
    """THE ONE ACCESSOR for PinFunction rows (c3-derive): the stored rows of `tables` PLUS, for a SoC whose matrix-routed functions are derived (the ESP32-C3), the derived rows of each of
    its pads that `tables` knows (a SocPin row of the SoC; `tables` without a 'SocPin' list, or None, means every pad). Derived rows carry `provenance: 'derived'`, are inserted right
    after the last stored row of their pad (the order the stored set used to have) and never repeat a stored name (a live server still holding the old stored copy answers from it - they
    are identical). `soc` limits the answer to one SoC. Rows are SHARED (the derived ones from a per-process cache): treat them as read-only."""
    tables = tables or {}
    stored = [f for f in (tables.get('PinFunction') or []) if soc is None or f.get('soc') == soc]
    want = [s for s in DERIVED if soc in (None, s)]
    if not want:
        return stored
    have = {f['name'] for f in stored}
    pads = None
    if tables.get('SocPin') is not None:
        pads = {sp['name'] for sp in tables['SocPin']}
    add = {}
    for s in want:
        for pad, rows in DERIVED[s]().items():
            if pads is not None and pad not in pads:
                continue
            fresh = [r for r in rows if r['name'] not in have]
            if fresh:
                add[pad] = fresh
    if not add:
        return stored
    last = {}
    for i, f in enumerate(stored):
        last[f['soc_pin']] = i
    out, done = [], set()
    for i, f in enumerate(stored):
        out.append(f)
        if last[f['soc_pin']] == i and f['soc_pin'] in add:
            out.extend(add[f['soc_pin']])
            done.add(f['soc_pin'])
    for pad, rows in add.items():   # a pad with no stored row at all
        if pad not in done:
            out.extend(rows)
    return out


def pad_functions(soc_pin, tables=None):
    """The function names of one SocPin row: its stored PinFunction rows then its derived ones (a pad with neither keeps the SocPin's own list), in row order, 'GPIO' first."""
    soc = soc_pin['soc']
    names = [f['function'] for f in ((tables or {}).get('PinFunction') or []) if f['soc_pin'] == soc_pin['name']]
    if soc in DERIVED:
        if not names:   # a caller with no tables: the stored (fixed) rows from the builders
            names = [f['function'] for f in _fixed_c3().get(soc_pin['name'], ())]
        seen = set(names)
        names += [f['function'] for f in DERIVED[soc]().get(soc_pin['name'], ()) if f['function'] not in seen]
    return names or (['GPIO'] + json.loads(soc_pin.get('functions_json') or '[]') if soc not in DERIVED else [])


def matches(soc, kind, fns):
    pats = kind_patterns(soc, kind) or []
    return [f for p in pats for f in fns if fnmatch.fnmatchcase(f, p)]


def compatible(kind, pin, soc_pin, fns, cite):
    """(verdict, reason) for a kind on a pad of a vocabulary SoC. `cite` is the 'datasheet fact ...' string the caller builds."""
    canonical = pin.get('canonical', '?')
    soc = soc_pin['soc']
    pats = kind_patterns(soc, kind)
    if pats is None:
        return 'undetermined', '%s: no rule written for kind %r on the %s (%s)' % (canonical, kind, soc, cite)
    hit = matches(soc, kind, fns)
    if kind == 'analog-in':
        return (('ok', '%s: has the analog function %s (datasheet Table 2-6 p.21, %s)' % (canonical, hit[0], cite)) if hit else
                ('no', '%s: no ADC channel - only GPIO0-GPIO5 have one (datasheet Table 2-6 p.21, %s)' % (canonical, cite)))
    if not hit:
        return 'no', '%s: none of %s among its functions (%s)' % (canonical, ' / '.join(pats), cite)
    via = 'the IO MUX' if not hit[0].endswith(('_in', '_out', '_out_mux')) and kind not in ('digital-in', 'digital-out', 'interrupt-in', 'pwm-out', 'i2c-sda', 'i2c-scl') else 'the GPIO matrix'
    why = {'digital-in': 'every pad is a GPIO (datasheet Table 2-4)', 'digital-out': 'every pad is a GPIO (datasheet Table 2-4)',
           'interrupt-in': 'every pad can interrupt on an edge or a level (TRM Register 5.14 p.184; datasheet §4.1.3.1 p.36)'}.get(kind)
    src = 'datasheet Table 2-4 pp.19-20 and Table 2-7 p.24' if via == 'the IO MUX' else 'TRM §5.1 p.159 and Table 5.11-1; datasheet Table 2-7 p.24'
    return 'ok', '%s: %s' % (canonical, why or 'reaches %s through %s (%s; %s)' % (hit[0], via, src, cite))
