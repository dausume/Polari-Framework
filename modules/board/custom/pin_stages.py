"""
@module board.custom.pin_stages

rm-1 (REGISTER_MAPPING_PLAN.md §1, his proposal P§5/P§8; D-rm-2 RULED 2026-10-28: "keep all phases, but define groupings of them so we can constrain what we
see to what is relevant per view"): the seven lifecycle PHASES stay the rows (PinLifecycleConstraint); a GROUPING names which phases a view shows and how it
groups them into STAGES. And the derived PinStageAssessment: pin x stage -> function, direction, owner, restrictions, register fields, verdict + reasons.

  GROUPINGS                     lifecycle-4 (the Registers view) | boot-safety (the boot-conflict list) | firmware (the trace, the Structs view) | all-7 (the pin view)
  assess(board, pin, claim, grouping, context) -> {stages[], boot_critical[], basis}
  stage rows: {stage, phases, function, direction, owner, restrictions, register_fields, verdict, reasons, boot_critical}

The verdict (P§8) - valid | warning | conflict | unknown:
  - a lifecycle row whose condition holds in `context` (default for the UNO: transport=usb-serial, dtr=resets-mcu - the bench's path; a row whose condition
    does not hold is listed as not applied): WITHOUT an application claim, prohibited / reserved = valid (the stage is owned - by the hardware, the boot
    firmware or the bridge - and said), conditional / preserve = warning; WITH a claim in that stage: prohibited = conflict, reserved = conflict unless the
    claim IS the reserving function (a uart-rx claim on D0: warning), conditional / preserve = warning
  - no row: valid ONLY when the board has a cited lifecycle table (the sources were read and give this pin no constraint in these phases: "free"), else unknown
  - RESET also reads the pin's cited reset-value fields (DDxn = 0, PORTxn = 0 -> input, tri-state); none cited = unknown for the function, never assumed
  - a conflict is BOOT-CRITICAL when it sits in a boot-safety phase, or the pin is the bootloader / programming link (a reserved bootloader or programming
    row: an application claim against it can cut the recovery path); boot-critical rows are listed first.
"""
#: D-rm-2: named groupings = data rows (name, stages [(stage, phases)], purpose); a new view adds a grouping, never a phase
GROUPINGS = {
    'lifecycle-4': {'purpose': 'the Registers view\'s pin-lifecycle panel (P§5)',
                    'stages': [('RESET', ('power-up', 'reset')), ('BOOTLOADER', ('bootloader', 'programming', 'debug')), ('INITIALIZATION', ('init',)),
                               ('ACTIVE', ('runtime',))]},
    'boot-safety': {'purpose': 'the boot-conflict list', 'stages': [('POWER-UP', ('power-up',)), ('RESET', ('reset',)), ('BOOTLOADER', ('bootloader',)),
                                                                  ('PROGRAMMING', ('programming',))]},
    'firmware': {'purpose': 'the firmware trace and the Structs view', 'stages': [('INITIALIZATION', ('init',)), ('ACTIVE', ('runtime',))]},
    'all-7': {'purpose': 'the pin view\'s phase mode (unchanged)', 'stages': [(p.upper(), (p,)) for p in
                                                                           ('power-up', 'reset', 'bootloader', 'init', 'runtime', 'programming', 'debug')]},
}
BOOT_SAFETY = ('power-up', 'reset', 'bootloader', 'programming')
VERDICTS = ('valid', 'warning', 'conflict', 'unknown')
#: an application claim -> the pin function that IS it (a reservation by that same function is not a conflict) + its direction
CLAIMS = {'gpio-out': ('GPIO', 'output'), 'gpio-in': ('GPIO', 'input'), 'uart-tx': ('TXD', 'output'), 'uart-rx': ('RXD', 'input'),
          'int-ext': ('INT', 'input'), 'pwm-out': ('OC', 'output'), 'adc-in': ('ADC', 'input')}
#: the context a lifecycle row's condition is judged in, per board (the bench's path: the UNO talks to the host over its 16U2; DTR resets it - the R3 circuit)
DEFAULT_CONTEXT = {'arduino-uno-r3': {'transport': 'usb-serial', 'dtr': 'resets-mcu'}, 'esp32-c3': {'transport': 'usb-serial'}}


def _tables(board):
    """(lifecycle rows, reset fields by soc pin, soc, canonical -> soc pin) for a board with a cited table; (None, ...) otherwise."""
    if board == 'arduino-uno-r3':
        from board.custom.lifecycle_uno import constraints
        from board.custom import register_fields_atmega328p as RF
        from board.custom.board_uno import D_PINS, A_PINS
        canon = {c: s for c, (s, _n) in list(D_PINS.items()) + list(A_PINS.items())}
        canon.update({'RESET': 'PC6', 'PB6': 'PB6', 'PB7': 'PB7', 'AREF': ''})
        fields = {}
        for f in RF.FIELDS:
            if f['affects_pin'] and f['register'][:3] in ('DDR', 'POR'):
                fields.setdefault(f['affects_pin'], []).append(f)
        return constraints(), fields, 'atmega328p', canon
    if board == 'esp32-c3':
        from board.custom.lifecycle_c3 import constraints
        return constraints(), C3_RESET, 'esp32c3', {'GPIO%d' % n: 'GPIO%d' % n for n in range(22)}
    return None, {}, '', {}


class _C3Reset(dict):
    """rm-2b: the C3's pad state after reset - Table 5.12-1 p.174 (the per-pad Reset code, legend p.175), as board.custom.registers_esp32c3 carries it."""
    def get(self, pin, default=None):
        from board.custom import registers_esp32c3 as RC
        if not pin.startswith('GPIO'):
            return default
        n = int(pin[4:])
        drv, code = RC.IOMUX_RESET[n]
        ie, wpu, wpd, oe = RC.RESET_CODE[code]
        return {'c3': True, 'code': code, 'ie': ie, 'wpu': wpu, 'wpd': wpd, 'oe': oe, 'drv': drv, 'note': RC.RESET_NOTE.get(code, '')}


C3_RESET = _C3Reset()


def _cond_holds(cond, ctx):
    if not cond:
        return True
    k, _, v = cond.partition('=')
    return ctx.get(k.strip()) == v.strip()


def _owner(row):
    r = row['reason'].lower()
    if row['phase'] in ('bootloader',) or 'bootloader' in r and row['phase'] != 'runtime':
        return 'boot-firmware'
    if 'usb-serial' in r or '16u2' in r or 'transport' in r:
        return 'bridge'
    if row['phase'] in ('programming', 'debug'):
        return 'programmer'
    return 'hardware'


#: words by which a lifecycle reason names the claim's OWN peripheral (USART0 / the serial transport on D0/D1): then the reservation is that peripheral's
CLAIM_KEYWORDS = {'uart-tx': ('TXD', 'USART0', 'UART0', 'serial'), 'uart-rx': ('RXD', 'USART0', 'UART0', 'serial'), 'int-ext': ('INT0', 'INT1', 'interrupt'),
                  'pwm-out': ('PWM', 'OC0', 'OC1', 'OC2'), 'adc-in': ('ADC',)}


def _same(claim, row):
    return any(w in row['reason'] for w in CLAIM_KEYWORDS.get(claim, ()))


def assess(board, pin, claim='', grouping='lifecycle-4', context=None):
    """The pin's stage matrix. `claim` = an application claim (CLAIMS) laid over the INIT/ACTIVE-side stages; '' = what the hardware and boot do alone."""
    if grouping not in GROUPINGS:
        raise KeyError('grouping must be one of %s' % ', '.join(GROUPINGS))
    if claim and claim not in CLAIMS:
        raise KeyError('claim must be one of %s' % ', '.join(CLAIMS))
    rows, fields, soc, canon = _tables(board)
    ctx = dict(DEFAULT_CONTEXT.get(board, {}), **(context or {}))
    soc_pin = canon.get(pin, '') if rows is not None else ''
    stages, critical = [], []
    pin_rows = [r for r in (rows or []) if r['pin'] == pin]
    boot_link = any(r['phase'] in ('bootloader', 'programming') and r['policy'] == 'reserved' and _cond_holds(r['condition'], ctx) for r in pin_rows)
    for stage, phases in GROUPINGS[grouping]['stages']:
        applied = [r for r in pin_rows if r['phase'] in phases and _cond_holds(r['condition'], ctx)]
        skipped = [r for r in pin_rows if r['phase'] in phases and not _cond_holds(r['condition'], ctx)]
        claimed = bool(claim) and any(p in ('init', 'runtime') for p in phases)
        reasons, verdicts, owner, function, direction = [], [], '', '', ''
        regf = []
        if rows is None or (pin not in canon and not pin_rows):
            verdicts.append('unknown')
            reasons.append('no cited lifecycle table for %s / no pin %s on it: no evidence, never valid' % (board, pin))
        if 'reset' in phases or 'power-up' in phases:
            fs = fields.get(soc_pin, [])
            if isinstance(fs, dict) and fs.get('c3'):   # rm-2b: the C3's cited pad reset (Table 5.12-1)
                bits = ['IO_MUX_%s_REG.FUN_IE = %d' % (soc_pin, fs['ie']), 'FUN_WPU = %d' % fs['wpu'], 'FUN_WPD = %d' % fs['wpd'], 'FUN_DRV = %d' % fs['drv']]
                regf = bits
                function = 'GPIO' if not fs['oe'] else 'IO MUX function 0'
                direction = ('output' if fs['oe'] else 'input' if fs['ie'] else 'input disabled') + (', pull-up' if fs['wpu'] else ', pull-down' if fs['wpd'] else ', no pull')
                owner = 'hardware'
                reasons.append('reset (Table 5.12-1 p.174, Reset code %s, legend p.175): %s%s' % (fs['code'], direction, ('; ' + fs['note']) if fs['note'] else ''))
                fs = []
            else:
                regf = ['%s.%s = %s' % (f['register'], f['field'], f['reset_value']) for f in fs]
            if fs and all(f['reset_value'] == '0' for f in fs):
                function, direction, owner = 'GPIO', 'input, tri-state', 'hardware'
                reasons.append('reset values: %s (%s) -> input, no pull-up' % (', '.join(regf), fs[0]['page_table']))
            elif rows is not None and not pin_rows and not regf:
                verdicts.append('unknown')
                reasons.append('no cited reset-value fields for %s (%s): its state at reset is not on record' % (pin, soc_pin or 'no SoC pin'))
        for r in applied:
            who = _owner(r)
            cond = (' (when %s)' % r['condition']) if r['condition'] else ''
            text = '%s %s in %s%s: %s [%s]' % (pin, r['policy'], r['phase'].upper(), cond, r['reason'], r['page_table'])
            if claimed and r['phase'] in ('init', 'runtime', 'bootloader', 'programming', 'debug') and r['phase'] in phases:
                if r['policy'] == 'prohibited' or (r['policy'] == 'reserved' and not _same(claim, r)):
                    verdicts.append('conflict')
                    reasons.append('CONFLICT with the %s claim: %s' % (claim, text))
                    continue
            if r['policy'] in ('prohibited', 'reserved') and not claimed:
                verdicts.append('valid')
                owner = owner or who
                reasons.append('owned by the %s: %s' % (who, text))
            else:
                verdicts.append('warning')
                reasons.append('warning: ' + text)
        for r in skipped:
            reasons.append('not applied (condition %s does not hold here): %s %s in %s' % (r['condition'], pin, r['policy'], r['phase'].upper()))
        if claimed:
            function, direction = function or CLAIMS[claim][0], CLAIMS[claim][1]
            owner = 'application' if 'conflict' not in verdicts else (owner or 'application')
        if not verdicts:
            if rows is not None and (pin in canon or pin_rows):
                verdicts.append('valid')
                reasons.append('free: the cited lifecycle table gives %s no constraint in %s' % (pin, ', '.join(phases)))
            else:
                verdicts.append('unknown')
        verdict = next(v for v in ('conflict', 'unknown', 'warning', 'valid') if v in verdicts)
        boot_critical = verdict == 'conflict' and (any(p in BOOT_SAFETY for p in phases) or boot_link)
        row = {'board': board, 'pin': pin, 'soc_pin': soc_pin, 'stage': stage, 'phases': ', '.join(phases), 'function': function or ('-' if verdict != 'unknown' else 'unknown'),
               'direction': direction or '-', 'owner': owner or ('application' if claimed else '-'), 'restrictions': len(applied), 'register_fields': '; '.join(regf),
               'verdict': verdict, 'reasons': ' | '.join(reasons), 'boot_critical': boot_critical,
               'boot_why': ('the pin is the bootloader / programming link: an application claim against it can cut the recovery path' if boot_critical and boot_link
                            else 'a conflict in a boot-safety phase' if boot_critical else '')}
        stages.append(row)
        if boot_critical:
            critical.append(row)
    return {'ok': True, 'board': board, 'pin': pin, 'claim': claim, 'grouping': grouping, 'context': ctx, 'stages': stages,
            'boot_critical': critical, 'basis': 'PinLifecycleConstraint rows (cited) + the cited reset-value fields; nothing stored (rm-1)'}
