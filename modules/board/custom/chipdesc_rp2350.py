"""
@module board.custom.chipdesc_rp2350

hal-4 proof 2 (econ, plan §4d): the RP2350 (its Hazard3 RISC-V side) as a chip DESCRIPTION - Raspberry Pi's own CMSIS-SVD
(pico-sdk 2.2.0, BSD-3-Clause; the GPIO path cut out unchanged by tools/hal_evidence/rp2350_svd_extract.py into
evidence/rp2350/RP2350.gpio-extract.svd) -> svd_import -> access_overlay.apply_svd -> ONE cited refinement below -> chipdesc_provider.
Zero generator changes: the HAL learns the chip only through register().

The one refinement: CMSIS-SVD says only "write-only" for SIO's GPIO_OUT_SET / _CLR and GPIO_OE_SET / _CLR. Their own SVD
<description> states the behaviour ("Perform an atomic bit-set on GPIO_OUT, i.e. `GPIO_OUT |= wdata`"), so those four fields
get w1-set / w1-clear, cited with that text verbatim - matched exactly, refused if the text differs. The XOR aliases ("atomic
bitwise XOR") have no HAL access word yet (no w1-toggle in the agreed table), so they stay 'w' and are NOT in any role: a toggle
falls through to GPIO_OUT's read-modify-write - correct, not atomic across cores; said, not hidden.

Hand-written, cited facts (meta): arch riscv (the SVD's <description>: "Dual Cortex-M33 or Hazard3 processors" - the SIO / IO_BANK0
/ PADS_BANK0 map is the same for either core), the bases (from the SVD), pins GPIO0..31 (the SVD's GPIO_IN / GPIO_OUT descriptions:
"GPIO0...31"; which of them a package bonds is a board fact, not modelled here), setups FUNCSEL = 5 (the SVD's enumeratedValues:
5 = siob_proc_n, the SIO) and the pad's ISO / IE (the SVD's PADS_BANK0 descriptions). The RP2350 datasheet itself was NOT read
this session: every cite here is the vendor SVD.
"""
import os

from board.custom import access_overlay as O
from board.custom import svd_import as S

HERE = os.path.dirname(os.path.abspath(__file__))
SVD = os.path.join(HERE, 'evidence', 'rp2350', 'RP2350.gpio-extract.svd')
SVD_SOURCE = 'Raspberry Pi pico-sdk 2.2.0 src/rp2350/hardware_regs/RP2350.svd (sha256 f1180d39bbc0e7c0..., BSD-3-Clause), GPIO extract'
PINS = range(32)

#: field -> (access word, the SVD description text that says it, verbatim)
ALIASES = {
    ('SIO_GPIO_OUT_SET_REG', 'GPIO_OUT_SET'): ('w1-set', 'Perform an atomic bit-set on GPIO_OUT, i.e. `GPIO_OUT |= wdata`'),
    ('SIO_GPIO_OUT_CLR_REG', 'GPIO_OUT_CLR'): ('w1-clear', 'Perform an atomic bit-clear on GPIO_OUT, i.e. `GPIO_OUT &= ~wdata`'),
    ('SIO_GPIO_OE_SET_REG', 'GPIO_OE_SET'): ('w1-set', 'Perform an atomic bit-set on GPIO_OE, i.e. `GPIO_OE |= wdata`'),
    ('SIO_GPIO_OE_CLR_REG', 'GPIO_OE_CLR'): ('w1-clear', 'Perform an atomic bit-clear on GPIO_OE, i.e. `GPIO_OE &= ~wdata`'),
}
#: hal-3b (pin twin): the register each alias acts on - the one its cited text names (`GPIO_OUT |= wdata` -> SIO_GPIO_OUT_REG); refine() refuses a
#: target the text does not name
ACTS_ON = {('SIO_GPIO_OUT_SET_REG', 'GPIO_OUT_SET'): 'SIO_GPIO_OUT_REG', ('SIO_GPIO_OUT_CLR_REG', 'GPIO_OUT_CLR'): 'SIO_GPIO_OUT_REG',
           ('SIO_GPIO_OE_SET_REG', 'GPIO_OE_SET'): 'SIO_GPIO_OE_REG', ('SIO_GPIO_OE_CLR_REG', 'GPIO_OE_CLR'): 'SIO_GPIO_OE_REG'}


class Rp2350Refused(Exception):
    pass


def rows(path=SVD):
    """-> (REGISTERS, FIELDS, bases): the three blocks imported, apply_svd's words, the four aliases refined by their own text"""
    chip = S.load(path)
    R, F, bases = [], [], {}
    for p in ('SIO', 'IO_BANK0', 'PADS_BANK0'):
        r, f = S.rows(chip, p, block=p, name_prefix=p)
        bases[p] = S.address(chip, p, 0)
        R += [dict(x, base=bases[p]) for x in r]   # each register row carries its block's own base (chipdesc_provider reads it)
        F += f
    return R, refine(O.apply_svd(F)[0]), bases


def refine(F):
    """the four SET / CLR alias fields get their word from their own SVD description text, matched exactly; anything else refused"""
    F = list(F)
    seen = set()
    for i, f in enumerate(F):
        k = (f['register'], f['field'])
        if k in ALIASES:
            word, text = ALIASES[k]
            if f.get('description', '').strip() != text:
                raise Rp2350Refused('%s.%s: the SVD description is %r, not the cited %r - refused, not guessed' % (k + (f.get('description'), text)))
            tgt = ACTS_ON[k]
            if '`%s ' % tgt[len('SIO_'):-len('_REG')] not in text:
                raise Rp2350Refused('%s.%s acts on %s, but its cited text does not name it - refused, not guessed' % (k + (tgt,)))
            F[i] = dict(f, access_word=word, access_source='svd-description', access_cite='SVD %s.%s <description>: "%s"' % (k + (text,)), acts_on=tgt)
            seen.add(k)
    if seen != set(ALIASES):
        raise Rp2350Refused('alias fields missing from the SVD: %s' % sorted(set(ALIASES) - seen))
    return F


def meta(bases):
    base = bases['SIO']
    regs = lambda *names: ['SIO_%s_REG' % n for n in names]
    pins = {'GPIO%d' % n: [('SIO_%s_REG' % r, r, n) for r in ('GPIO_OUT_SET', 'GPIO_OUT_CLR', 'GPIO_OUT', 'GPIO_OE_SET', 'GPIO_OE_CLR', 'GPIO_OE', 'GPIO_IN')]
            for n in PINS}
    svd = 'the SVD (%s)' % SVD_SOURCE
    return {
        'title': 'RP2350 (Hazard3 RISC-V side)', 'arch': 'riscv', 'reg_width': 32, 'base': base,
        'source': 'board.custom.svd_import(%s)' % SVD_SOURCE,
        'cite': 'SIO base 0x%08X, IO_BANK0 0x%08X, PADS_BANK0 0x%08X: <baseAddress> in %s; "Dual Cortex-M33 or Hazard3 processors" (<description>)'
                % (bases['SIO'], bases['IO_BANK0'], bases['PADS_BANK0'], svd),
        'pins': pins, 'pin_numbers': {'GPIO%d' % n: n for n in PINS},
        'pins_cite': 'GPIO0..31 = bit n of SIO GPIO_IN / GPIO_OUT / GPIO_OE and their aliases (the SVD descriptions: "GPIO0...31")',
        'roles': {
            'output': {'registers': regs('GPIO_OUT_SET', 'GPIO_OUT_CLR', 'GPIO_OUT'),
                       'cite': 'SVD SIO.GPIO_OUT and its SET / CLR aliases (atomic per their descriptions); the XOR alias has no HAL word yet'},
            'direction': {'registers': regs('GPIO_OE_SET', 'GPIO_OE_CLR', 'GPIO_OE'), 'cite': 'SVD SIO.GPIO_OE ("1/0 -> output/input") and its SET / CLR aliases'},
            'input': {'registers': regs('GPIO_IN'), 'cite': 'SVD SIO.GPIO_IN (read-only)'},
        },
        'setups': {
            'gpio-out': [
                {'register': 'IO_BANK0_GPIO{n}_CTRL_REG', 'field': 'FUNCSEL', 'value': 5, 'purpose': 'route the pad to the SIO (function 5)',
                 'cite': 'SVD IO_BANK0.GPIOn_CTRL.FUNCSEL enumeratedValues: 5 = siob_proc_n'},
                {'register': 'PADS_BANK0_GPIO{n}_REG', 'field': 'ISO', 'value': 0, 'purpose': 'release the pad isolation (resets to 1)',
                 'cite': 'SVD PADS_BANK0.GPIOn.ISO: "Pad isolation control. Remove this once the pad is configured by software." (reset 1)'},
            ],
            'gpio-in': [
                {'register': 'IO_BANK0_GPIO{n}_CTRL_REG', 'field': 'FUNCSEL', 'value': 5, 'purpose': 'route the pad to the SIO (function 5)',
                 'cite': 'SVD IO_BANK0.GPIOn_CTRL.FUNCSEL enumeratedValues: 5 = siob_proc_n'},
                {'register': 'PADS_BANK0_GPIO{n}_REG', 'field': 'IE', 'value': 1, 'purpose': 'enable the pad\'s input buffer (resets to 0)',
                 'cite': 'SVD PADS_BANK0.GPIOn.IE: "Input enable" (reset 0)'},
                {'register': 'PADS_BANK0_GPIO{n}_REG', 'field': 'ISO', 'value': 0, 'purpose': 'release the pad isolation (resets to 1)',
                 'cite': 'SVD PADS_BANK0.GPIOn.ISO: "Pad isolation control. Remove this once the pad is configured by software." (reset 1)'},
            ],
        },
        'c': {'ctype': 'uint32_t', 'mask': '(1UL << {bit})', 'field_forms': {'fmask': '0x{m:X}UL', 'fval': '((uint32_t){v} << {lo})'},
              'includes': ['<stdint.h>'], 'header_includes': [], 'access_style': 'address',
              'prelude': ['#ifndef POLARI_HAL_ATOMIC', '/* {guard_why} */', '#define POLARI_HAL_ATOMIC(stmt) do {{ stmt }} while (0)', '#endif'],
              'guard': 'POLARI_HAL_ATOMIC(%s);', 'guard_include': '',
              'guard_why': 'POLARI_HAL_ATOMIC defaults to the bare statement; a firmware whose ISR (or other core) shares the register defines it as a critical section',
              'init_rule': 'an _INIT form drops the guard', 'init_cite': 'the caller decides'},
    }
