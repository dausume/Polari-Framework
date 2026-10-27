"""
@module board.custom.signal_kinds

The analog / digital / differential AXIS of the pin view's one signal vocabulary (`board.custom.pv_families`, pv-0) - his ask 2026-10-27: "we should
have separation between digital, analog and differential type signals on the signals component". NOTHING here is a second vocabulary: a signal's
kind is DERIVED from the family pv_families already gives its function name (the same regex rules the pin view colours by), so the families
table, every per-pin signal row, the PeripheralSignal rows and an oscilloscope channel all say the same word for the same line.

  analog        the VALUE of a voltage carries the information (the `analog` family: ADC / AIN / AREF; a DAC pin, a TMP36 output): read in volts
                on an ANALOG channel; a logic input cannot take it.
  digital       the LEVEL of a voltage above / below a threshold carries the information (gpio, interrupt, pwm-timer, uart, spi, i2c, clock,
                reset-programming): read as 0 / 1 by a threshold with hysteresis; a LOGIC input reads only the level, an ANALOG channel reads it
                too and shows its edges, ringing and levels - so a spare analog channel counts for a digital signal, never the other way round.
  differential  the DIFFERENCE of two lines carries the information (the `usb` family: D+ / D-; CAN H / L, RS-485, LVDS on chips that have them):
                read as A - B; needs ONE differential input or TWO analog channels and the math A - B (common mode costs range, skew costs timing).
  undetermined  power and ground are rails, not signals; a function no family rule names.

The pin view already calls a usb-data leg's electrical role `differential-pair` (pin_view_model.drive_role); SystemLink.signal_kind (hsp-1) uses
link words (digital | analog | uart | usb | rpc | reset) - `kind_of_link` maps those onto this axis. `profile_overlap_kinds` / `target_compat`
task kinds (analog-in, digital-in, pwm-out, ...) map through `kind_of_task_kind`.
"""
from board.custom import pv_families as F

SIGNAL_KINDS = ('analog', 'digital', 'differential', 'undetermined')

#: family (pv_families.FAMILIES) -> kind. Every family is named here (the selftest wants no family unmapped).
KIND_OF_FAMILY = {'gpio': 'digital', 'interrupt': 'digital', 'pwm-timer': 'digital', 'analog': 'analog', 'uart': 'digital', 'spi': 'digital', 'i2c': 'digital',
                  'usb': 'differential', 'clock': 'digital', 'reset-programming': 'digital', 'power': 'undetermined', 'ground': 'undetermined'}
assert set(KIND_OF_FAMILY) == set(F.FAMILIES)

#: SystemLink.signal_kind (hsp-1 link words) -> kind
_OF_LINK = {'digital': 'digital', 'analog': 'analog', 'uart': 'digital', 'usb': 'differential', 'reset': 'digital', 'rpc': 'undetermined'}
#: profile_overlap_kinds / target_compat task kinds -> kind
_OF_TASK = {'analog-in': 'analog', 'comparator-in': 'analog'}


def kind_of_family(family):
    return KIND_OF_FAMILY.get(family, 'undetermined')


def kind_of(function):
    """(kind, why) for one pin function / signal name through the pin view's family rule: 'INT1' -> digital, 'ADC0' -> analog, 'USB_D+' -> differential."""
    fams = F.families_of_function(function or '')
    if not fams:
        return 'undetermined', 'no family rule names %r (pv_families._RULES)' % (function or '')
    kind = kind_of_family(fams[0])
    return kind, 'family %s -> %s (pv_families rule; the value of a voltage = analog, a level = digital, a pair\'s difference = differential)' % (fams[0], kind)


def kind_of_signal(signal, peripheral=''):
    """(kind, why) for a PeripheralSignal ROW: the name's family rule first; when no rule names it (a port bit 'PB5', the C3's matrix names 'U0RXD_in',
    'GPIO3_INT'), the row's PERIPHERAL decides - an ADC / comparator line is analog, any other peripheral line is a level (digital). A peripheral
    signal is a signal by construction, so 'undetermined' is left only for a row with no peripheral at all."""
    kind, why = kind_of(signal)
    if kind != 'undetermined' or not peripheral:
        return kind, why
    pid = (peripheral.split(':', 1)[-1] if ':' in peripheral else peripheral).upper()
    if pid.startswith('ADC') or pid in ('AC', 'COMP', 'ANALOG COMPARATOR') or pid.startswith('DAC'):
        return 'analog', 'no name rule; the peripheral %s is an analog block -> analog' % pid
    return 'digital', 'no name rule; a line of the peripheral %s is a level -> digital' % pid


def kind_of_link(link_signal_kind):
    """SystemLink.signal_kind -> kind ('rpc' is a message, not a line: undetermined)."""
    return _OF_LINK.get(link_signal_kind, 'undetermined')


def kind_of_task_kind(task_kind):
    """A target_compat / profile_overlap task kind (analog-in, pwm-out, uart-rx, ...) -> kind; 'transport' (a reservation) is undetermined."""
    if task_kind in _OF_TASK:
        return _OF_TASK[task_kind]
    return 'undetermined' if task_kind in ('transport', '') else 'digital'


def kind_rows():
    """The axis as table rows (the pin view's legend, the instruments page's Signals tab)."""
    fam = lambda k: ', '.join(f for f in F.FAMILIES if KIND_OF_FAMILY[f] == k)  # noqa: E731
    return [
        {'kind': 'analog', 'carries': 'the value of a voltage', 'read_as': 'volts', 'needs': 'an analog channel', 'also_reads_it': 'nothing else (a logic input loses the value)',
         'examples': 'ADC0..5, AIN0/1, AREF, a DAC pin, the TMP36 output', 'families': fam('analog')},
        {'kind': 'digital', 'carries': 'a level above / below a threshold', 'read_as': '0 / 1 by threshold + hysteresis', 'needs': 'a logic input',
         'also_reads_it': 'an analog channel (and shows edges, ringing, levels)', 'examples': 'GPIO, RXD / TXD, SCK / MOSI / MISO, SDA / SCL, INT0/1, PCINTn, OCnX (PWM)', 'families': fam('digital')},
        {'kind': 'differential', 'carries': 'the difference of two lines', 'read_as': 'A - B', 'needs': 'one differential input (a differential probe)',
         'also_reads_it': 'two analog channels + the math A - B (common mode costs range; channel skew costs timing)', 'examples': 'USB D+ / D-; CAN H / L, RS-485 A / B, LVDS where a chip has them',
         'families': fam('differential')},
        {'kind': 'undetermined', 'carries': 'not a signal, or not decided by the name', 'read_as': '-', 'needs': '-', 'also_reads_it': '-', 'examples': 'power / ground rails, unnamed functions',
         'families': fam('undetermined')},
    ]


def logic_levels(volts, threshold_v, hysteresis_v=0.0):
    """A digital reading of a voltage trace: 1 above threshold + h/2, 0 below threshold - h/2, else the previous level (starts 0). Plain lists, no numpy."""
    hi, lo = threshold_v + hysteresis_v / 2.0, threshold_v - hysteresis_v / 2.0
    out, level = [], 0
    for v in volts:
        if v >= hi:
            level = 1
        elif v <= lo:
            level = 0
        out.append(level)
    return out


def differential(a_volts, b_volts):
    """A differential reading from two single-ended traces: A - B, sample by sample (the two must share one time axis - the caller's job, said there)."""
    if len(a_volts) != len(b_volts):
        raise ValueError('A and B must have the same number of samples (one time axis): %d vs %d' % (len(a_volts), len(b_volts)))
    return [a - b for a, b in zip(a_volts, b_volts)]
