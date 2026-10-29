"""
@module cmod.custom.hal_electrical

hsp-3d's owed rule (HARDWARE_SYSTEM_PINS_PLAN.md §7 "Enforcement, not decoration: ... the electrical check must pass"): a HAL value judged against the BENCH
WIRING - the `BoardPinNet` rows (board.custom.board_pin_nets: which board pin sits on which net and whether it is that net's output or an input) and the
findings board.custom.electrical_check already derives for that net. Nothing new is measured here; this reads the wiring the bench has.

  role_check(var, pin, was_pin, others, net_rows, findings) -> {effect: '' | 'warning' | 'refused', lines[]}
    - an OUTPUT role (gpio.out, uart.tx, pwm.out) on a pin whose net already has ANOTHER pin as its output = REFUSED: two outputs fight on one net (rule b of
      electrical_check: current flows between them) - unless that other output is the variable's own old pin (the value is moving, the wire with it)
    - the pin is wired to the opposite direction (an output role on a pin the wiring has as an input, or an input role on the net's output) = a warning naming it
    - nothing is wired to the pin while the variable's CURRENT pin is wired = a warning: the firmware would move, the wire would not (move it, or record it)
    - the pin is on a net with the matching role = accepted, quoting electrical_check's findings for that net / pin (LED current, VOH under load ...)
    - the board has no wiring rows at all (the C3 today) = undetermined, said - never a pass
"""
OUTPUT_ROLES = ('gpio.out', 'uart.tx', 'pwm.out')
INPUT_ROLES = ('gpio.in', 'int.ext', 'uart.rx', 'adc.in')


def _get(o, k, d=''):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _net(row):
    return _get(row, 'name').rpartition(':')[2]


def seed_findings():
    """electrical_check's findings over the seeded bench circuit (cached per process)."""
    if '_f' not in _CACHE:
        try:
            from board.custom import electrical_check as E
            _CACHE['_f'] = E.check('uno-button-clock', 'arduino-uno-r3', E.tables_for(None))
        except Exception as e:  # noqa: BLE001 - the check is evidence, never a crash of the HAL check
            _CACHE['_f'] = [{'rule': 'electrical_check', 'status': 'undetermined', 'subject': '', 'detail': 'electrical_check could not run: %s' % e}]
    return _CACHE['_f']


_CACHE = {}


def role_check(var, pin, was_pin='', others=(), net_rows=None, findings=None):
    """`pin` / `was_pin` are BOARD pin names (D6, GPIO0) - the candidate and the variable's current one."""
    role, board, name = _get(var, 'role'), _get(var, 'board'), _get(var, 'variable')
    if role not in OUTPUT_ROLES + INPUT_ROLES:
        return {'effect': '', 'lines': []}
    if net_rows is None:
        from board.custom.board_pin_nets import SEED_BOARD_PIN_NETS
        net_rows = SEED_BOARD_PIN_NETS
    mine = [r for r in net_rows if _get(r, 'board_pin').partition(':')[0] == board]
    if not mine:
        return {'effect': '', 'lines': ['electrical check undetermined: %s has no bench wiring rows (BoardPinNet) - nothing to check %s = %s against' % (board, name, pin)]}
    at = lambda p: [r for r in mine if _get(r, 'board_pin') == '%s:%s' % (board, p)]   # noqa: E731
    here, was = at(pin), at(was_pin) if was_pin and was_pin != pin else []
    want = 'output' if role in OUTPUT_ROLES else 'input'
    if not here:
        if was:
            return {'effect': 'warning', 'lines': ['electrical: nothing is wired to %s on the bench, but %s is wired now (%s, %s): the firmware would move to %s and the wire '
                                                   'would not - move the wire too, or record the new wiring (a BoardPinNet row)'
                                                   % (pin, was_pin, ', '.join('%s as %s' % (_net(r), _get(r, 'role')) for r in was), name, pin)]}
        return {'effect': '', 'lines': ['electrical: %s is not on any bench net (no BoardPinNet row): nothing to check it against' % pin]}
    effect, lines = '', []
    for r in here:
        net, rrole = _net(r), _get(r, 'role')
        if want == 'output':
            fight = [o for o in mine if _net(o) == net and _get(o, 'role') in ('output', 'driver') and _get(o, 'board_pin') != _get(r, 'board_pin')
                     and _get(o, 'board_pin') != '%s:%s' % (board, was_pin)]
            if fight:
                return {'effect': 'refused', 'lines': ['electrical REFUSED: %s = %s would be a second output on %s, which %s already drives - two outputs fight on one net '
                                                       '(electrical_check rule b: current flows between them)' % (name, pin, net, ', '.join(_get(o, 'board_pin').partition(':')[2] for o in fight))]}
        if rrole in ('output', 'driver') and want == 'input' or rrole == 'input' and want == 'output':
            effect = 'warning'
            lines.append('electrical: the bench wires %s as the %s of %s, but %s is a %s role - check the wiring before using it' % (pin, rrole, net, role, want))
        elif rrole in ('output', 'driver', 'input'):
            lines.append('electrical: %s is on %s as its %s (BoardPinNet %s) - matches %s' % (pin, net, rrole, _get(r, 'name'), role))
        for f in [f for f in (findings if findings is not None else seed_findings()) if net in f.get('subject', '') or pin in f.get('subject', '').split()]:
            lines.append('  %s %s: %s' % (f['rule'], f['status'], f['detail'][:160]))
    return {'effect': effect, 'lines': lines}
