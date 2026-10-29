"""
@module board.custom.hardware_chain_c3

c3pf (FIRMWARE_GENERATION_MODULE_PLAN.md section 11): THE ESP32-C3's HARDWARE CHAIN, following the UNO's (board.custom.hardware_chain):

    SocPin -> PinFunction -> PeripheralSignal -> Peripheral

  Peripheral        22 blocks (esp32c3_chain_meta.PERIPHERALS), each cited to the datasheet / TRM page that names it
  PeripheralSignal  one per VALID entry of TRM Table 5.11-1 (42 input + 78 output signals, p.169-173), the 4 JTAG signals (datasheet Table 2-3), the 6 ADC channels,
                    USB_D-/USB_D+ and the 2 XTAL_32K pads (Tables 2-5/2-6), and per pad a GPIO signal and a GPIO_INT signal
  PinFunction       (c3-derive: ONLY the ~72 'fixed' rows are stored; the 2 640 'matrix' rows are DERIVED on read by soc_functions.pin_functions - code-owned, deterministic,
                    no stored copy to drift. The text below says what each row is.) per SocPin: GPIO, GPIO_INT, its IO MUX functions F0/F2 and analog functions (routing 'fixed' - the pad has exactly these), and EVERY valid
                    Table 5.11-1 signal with routing 'matrix' ("peripheral input signals can be from any IO pins, and peripheral output signals can be routed to any
                    IO pins", TRM §5.1 p.159) - 22 pads x 120 signals

`exclusive_group` is set ONLY where a source says: one pad takes one of the three IO MUX functions F0/F1/F2 (datasheet §2.3.1 p.19), and the GPIO matrix
sends ONE output signal to a pad (GPIO_FUNCn_OUT_SEL is a single field, TRM §5.5.2 p.164) - so F0, F2, GPIO and every matrix OUTPUT signal of a pad share the
group `esp32c3:GPIOn:pad-output`. Matrix INPUT signals are not grouped: "one input pin can be connected to multiple peripheral input signals" (TRM §5.4.3 note 1,
p.163). The Table 2-7 priority (P1..P4) and the reason a pad is P3/P4 are in each matrix row's notes. Nothing else is guessed: where a source is silent the row says
`undetermined`.

rm-2b (2026-10-29): Register / RegisterField rows for the C3 DRAWING SET (board.custom.registers_esp32c3: 91 registers, 761 fields, TRM v1.4 cited, every bit position
and address checked against ESP-IDF v5.5.5's headers) - the peripherals that own them carry `registers_refs_json`; the rest of the map is documented, not ingested.
"""
import json

from board.custom import esp32c3_chain_meta as M
from board.custom import esp32c3_evidence as EV
from board.custom import esp32c3_tables as T

SOC = EV.SOC
_NO_REG = 'the ESP32-C3 register map is not ingested (no Register / RegisterField rows): this row stops at the peripheral'
_IFACE_OF = {pid: meta[4] for pid, meta in M.PERIPHERALS.items() if meta[4]}


def _ref(cls, name):
    return '%s:%s' % (cls, name)


def _gpio(sp):
    return int(sp['pin'][4:])


# ---------------------------------------------------------------- the facts the rows cite
def facts():
    """DatasheetFact rows: one per valid matrix signal (Table 5.11-1), per peripheral with a chapter, the GPIO interrupt, and the Table 2-7 priority line of each pad."""
    out = []
    for no, inp, dflt, din, outp, oen, dout, page in T.SIGNALS:
        for name, side in ((inp, 'input'), (outp, 'output')):
            if not name:
                continue
            extra = ('default value %s, direct input via IO MUX: %s' % (dflt, din)) if side == 'input' else ('output enable when GPIO_FUNCn_OEN_SEL = 0: %s, direct output via IO MUX: %s' % (oen, dout))
            out.append(EV.fact('signal.%s' % name, 'signal no. %d, %s; %s' % (no, side, extra), 'Table 5.11-1 Peripheral Signals via GPIO Matrix, p.%d (signal no. %d)' % (page, no), 'trm'))
    for pid, (_k, title, (doc, where), _w, _i) in M.PERIPHERALS.items():
        out.append(EV.fact('peripheral.%s' % pid, title, where, doc))
    out.append(EV.fact('gpio.interrupt', 'every pad has GPIO_PINn_INT_TYPE: 0 disabled, 1 rising edge, 2 falling edge, 3 any edge, 4 low level, 5 high level',
                       'TRM Register 5.14 GPIO_PINn_REG (n: 0-21), p.184; datasheet §4.1.3.1: "Input GPIOs can also be set to generate edge-triggered or level-triggered CPU interrupts", p.36', 'trm'))
    out.append(EV.fact('peripherals.list', 'Programmable GPIOs; two UARTs; three SPI; I2C; I2S; full-speed USB Serial/JTAG; TWAI; LED PWM (6 channels); RMT (2 TX + 2 RX); two 12-bit SAR ADCs (6 channels); '
                       'temperature sensor; two 54-bit general-purpose timers; three digital watchdog timers; analog watchdog timer; 52-bit system timer; XTAL32K watchdog - no analog comparator is listed',
                       'Product Overview, Features: Peripherals, pp.4-5; §4.2 Peripherals, pp.46-50',
                       notes='the datasheet\'s own enumeration: the Peripheral rows are built from it, so a block missing here is absent from the datasheet\'s list (not proof about silicon the list omits)'))
    out.append(EV.fact('matrix.routing', 'peripheral input signals can be from any of the 22 pads; peripheral output signals can be routed to any pad; 42 input and 78 output signals',
                       'TRM §5.1 Overview p.159, §5.2 Features p.159', 'trm'))
    for g, (pin_no, name, lead, dig) in sorted(T.PRIORITY.items()):
        pr = sorted({p for _s, p in dig.values()})
        out.append(EV.fact('priority.GPIO%d' % g, 'package pin %d (%s): matrix-routed interfaces are priority %s%s' % (pin_no, name, '/'.join('P%d' % p for p in pr),
                                                                                                                   (' (%s)' % M.CAUTION[g]) if g in M.CAUTION else ''),
                           'Table 2-7 Peripheral Pin Assignment, p.24; §2.3.4 Peripheral Pin Assignment priorities, p.23'))
    return out


# ---------------------------------------------------------------- the rows
def peripherals():
    out = []
    from board.custom import registers_esp32c3 as RC
    regs_of = {}
    for r in RC.REGISTERS:
        regs_of.setdefault(RC.PERIPHERAL_OF[r['block']], []).append(_ref('Register', '%s:%s' % (SOC, r['register'])))
    for pid, (kind, title, (doc, where), words, _iface) in M.PERIPHERALS.items():
        refs = sorted(regs_of.get(pid, []))
        out.append({'name': '%s:%s' % (SOC, pid), 'soc': SOC, 'peripheral': pid, 'title': title, 'kind': kind, 'chapter': '%s: %s' % (EV.SHORT[doc], where),
                    'description': words, 'registers_refs_json': json.dumps(refs), 'signals_refs_json': '[]', 'pin_functions_refs_json': '[]', 'fact': '%s:peripheral.%s' % (SOC, pid),
                    'origin': 'cited:%s %s' % (EV.SHORT[doc], where),
                    'undetermined': '' if refs else 'no register of this block is in the rm-2b drawing set (documented in the TRM, not ingested)', 'notes': ''})
    return out


# ---------------------------------------------------------------- rm-2b: the registers of the drawing set
def _trm_cite(where):
    return {'document': EV.TRM_DOC, 'page_table': where, 'url': EV.TRM_URL}


def registers():
    from board.custom import registers_esp32c3 as RC
    from board.custom import register_taxonomy as TX
    fields_by = {}
    for f in RC.FIELDS:
        fields_by.setdefault(f['register'], []).append(_ref('RegisterField', '%s:%s.%s' % (SOC, f['register'], f['field'])))
    out = []
    for r in RC.REGISTERS:
        tax = TX.classify(SOC, r['register'])
        row = {'name': '%s:%s' % (SOC, r['register']), 'soc': SOC, 'register': r['register'], 'peripheral': '%s:%s' % (SOC, RC.PERIPHERAL_OF[r['block']]), 'block': '',
               'addr': RC.address(r).lower(), 'addr_mem': '', 'space': 'mem', 'width_bytes': 4, 'reset_value': r['reset'], 'description': r['title'],
               'fields_refs_json': json.dumps(fields_by.get(r['register'], [])), 'mappings_refs_json': '[]',
               'origin': 'cited:%s %s; address = the %s base (%s) + offset 0x%04X' % (EV.SHORT['trm'], r['where'], r['block'], RC.BASE_CITE, r['offset']),
               'undetermined': r['undetermined'], 'notes': 'bit positions + address checked against ESP-IDF v5.5.5 components/soc/esp32c3/register/soc/*.h (2026-10-29)',
               'domains_json': json.dumps(tax['domains']), 'roles_json': json.dumps(tax['roles'], sort_keys=True), 'taxonomy_cite': tax['cite']}
        row.update(_trm_cite(r['where']))
        out.append(row)
    return out


def register_fields():
    from board.custom import registers_esp32c3 as RC
    from board.custom import register_taxonomy as TX
    out = []
    for f in RC.FIELDS:
        sig = f['affects_signal']
        sig_ref = ''
        if sig.endswith('_INT') and sig.startswith('GPIO'):
            sig_ref = '%s:GPIO_INT:%s' % (SOC, sig)
        elif sig:
            sig_ref = '%s:%s:%s' % (SOC, M.peripheral_of_signal(sig), sig)
        out.append({'name': '%s:%s.%s' % (SOC, f['register'], f['field']), 'soc': SOC, 'register': '%s:%s' % (SOC, f['register']), 'field': f['field'],
                    'bit_hi': f['bit_hi'], 'bit_lo': f['bit_lo'], 'width': f['width'], 'access': f['access'], 'reset_value': f['reset_value'], 'description': f['description'],
                    'values_json': json.dumps(f['values']), 'affects_signal': sig_ref, 'affects_pin': ('%s:%s' % (SOC, f['affects_pin'])) if f['affects_pin'] else '',
                    'origin': 'cited', 'undetermined': '', 'notes': f['notes'], **_trm_cite(f['page_table']),
                    'roles_json': json.dumps(TX.field_roles(SOC, f['register'], f), sort_keys=True)})
    return out


def _sig(pid, signal, channel, direction, words, fact, origin, notes='', und=''):
    from board.custom import signal_kinds as SK
    kind, why = SK.kind_of_signal(signal, pid)
    return {'name': '%s:%s:%s' % (SOC, pid, signal), 'soc': SOC, 'peripheral': '%s:%s' % (SOC, pid), 'signal': signal, 'channel': channel, 'direction': direction,
            'description': words, 'pin_functions_refs_json': '[]', 'fact': fact, 'origin': origin, 'undetermined': und, 'notes': notes,
            'signal_kind': kind, 'signal_kind_why': why}


def signals(soc_pin_rows):
    out = []
    for no, inp, dflt, din, outp, oen, dout, page in T.SIGNALS:
        for name, direction in ((inp, 'in'), (outp, 'out')):
            if not name:
                continue
            pid = M.peripheral_of_signal(name)
            extra = ('default %s; direct via IO MUX: %s' % (dflt, din)) if direction == 'in' else ('enable: %s; direct via IO MUX: %s' % (oen, dout))
            out.append(_sig(pid, name, str(no), direction, '%s %s signal (GPIO matrix signal no. %d)' % (M.PERIPHERALS[pid][1], 'input' if direction == 'in' else 'output', no),
                            '%s:signal.%s' % (SOC, name), 'cited:TRM Table 5.11-1 p.%d signal no. %d; peripheral derived from the name prefix (esp32c3_chain_meta.PREFIX)' % (page, no), extra,
                            'which block a name belongs to is read from the name (the table has no peripheral column)' if pid in ('ADC1', 'COEX', 'ANT_SEL', 'CLK_OUT', 'CPU_GPIO', 'GPIO_LOOPBACK') else ''))
    for fn, (pid, dr) in sorted({k: ('JTAG', 'out' if k == 'MTDO' else 'in') for k in ('MTCK', 'MTDO', 'MTDI', 'MTMS')}.items()):
        out.append(_sig(pid, fn, '', dr, 'JTAG %s, routed by the IO MUX only' % fn, '%s:peripheral.JTAG' % SOC, 'cited:datasheet Table 2-3 p.19; type Table 2-4 p.20'))
    for fn, (pid, dr) in sorted(M.ANALOG.items()):
        out.append(_sig(pid, fn, fn[-1] if fn.startswith('ADC') else '', dr, 'analog function %s of the IO MUX pad' % fn, '%s:peripheral.%s' % (SOC, pid),
                        'cited:datasheet Table 2-5 p.21, Table 2-6 p.21'))
    for sp in soc_pin_rows:
        if sp['soc'] != SOC:
            continue
        out.append(_sig('GPIO', sp['pin'], str(_gpio(sp)), 'inout', 'general digital I/O of pad %s' % sp['pin'], sp['fact'], 'cited:datasheet Table 2-4 p.19-20 (F1 is GPIOn on every pad); TRM §5.1 p.159'))
        out.append(_sig('GPIO_INT', '%s_INT' % sp['pin'], str(_gpio(sp)), 'in', 'the interrupt of pad %s (edge or level)' % sp['pin'], '%s:gpio.interrupt' % SOC,
                        'cited:TRM Register 5.14 GPIO_PINn_REG p.184; datasheet §4.1.3.1 p.36'))
    return out


def _group(g):
    return '%s:GPIO%d:pad-output' % (SOC, g)


def _row(sp, fn, signal_row, routing, overrides, words, fact, origin, group='', und='', notes=''):
    return {'name': '%s:%s:%s' % (SOC, sp['pin'], fn), 'soc': SOC, 'soc_pin': sp['name'], 'function': fn, 'signal': signal_row['name'], 'peripheral': signal_row['peripheral'],
            'routing': routing, 'overrides_gpio': overrides, 'exclusive_group': group, 'description': words, 'board_pins_refs_json': '[]', 'fact': fact, 'origin': origin,
            'undetermined': und, 'notes': notes}


_GROUP_WHY = ('datasheet §2.3.1 p.19: each pad takes ONE of the IO MUX functions F0-F2; TRM §5.5.2 p.164: GPIO_FUNCn_OUT_SEL names ONE output signal per pad')
_ANALOG_UND = ('which digital uses may coexist with an analog function is not tabulated; TRM §5.7 p.166 requires the input enable, pulls and output enable cleared for analog use')


def _by_signal(signal_rows):
    return {s['signal']: s for s in signal_rows if s['peripheral'].split(':', 1)[1] not in ('GPIO', 'GPIO_INT') and s['name'].count(':') == 2}


def _caution(sp):
    g = _gpio(sp)
    _pn, _name, _lead, prio = T.PRIORITY[g]
    worst = max(p for _s, p in prio.values())
    return ('datasheet §2.3.3 p.22: %s is a %s - an IO pin "that require[s] extra caution when used as GPIO"; Table 2-7 p.24: matrix-routed interfaces on it are priority P%d (§2.3.4 p.23)'
            % (sp['pin'], M.CAUTION[g], worst)) if g in M.CAUTION else ''


def fixed_pin_functions(soc_pin_rows, signal_rows):
    """The STORED PinFunction rows: per pad GPIO, GPIO_INT, its IO MUX functions F0/F2 and analog functions (routing 'fixed') - about 72 rows."""
    S = {(s['peripheral'].split(':', 1)[1], s['signal']): s for s in signal_rows}
    by_signal = _by_signal(signal_rows)
    out = []
    for sp in soc_pin_rows:
        if sp['soc'] != SOC:
            continue
        out.extend(_fixed_for(sp, S, by_signal))
    return out


def _fixed_for(sp, S, by_signal):
    out = []
    g = _gpio(sp)
    grp = _group(g)
    pin = sp['pin']
    caution = _caution(sp)
    out.append(_row(sp, 'GPIO', S[('GPIO', pin)], 'fixed', False, 'plain digital input/output of %s (IO MUX F1 = GPIO%d; simple output = matrix index 128)' % (pin, g), sp['fact'],
                    'cited:datasheet Table 2-4 pp.19-20; TRM §5.5.3 Simple GPIO Output p.165', group=grp, notes=_GROUP_WHY + ('; ' + caution if caution else '')))
    out.append(_row(sp, 'GPIO_INT', S[('GPIO_INT', '%s_INT' % pin)], 'fixed', False, 'interrupt on %s: rising, falling, any edge, low or high level' % pin, '%s:gpio.interrupt' % SOC,
                    'cited:TRM Register 5.14 p.184; datasheet §4.1.3.1 p.36',
                    notes='the pad input must be enabled to see the edge (IO_MUX_GPIOn_FUN_IE, TRM §5.4.3 step 4 p.163); the interrupt reaches the CPU through the interrupt matrix (datasheet §4.1.3.4 p.37)'
                          + ('; ' + caution if caution else '')))
    for fn in json.loads(sp['functions_json']):
        if fn == 'GPIO%d' % g:
            continue
        if fn in M.ANALOG:
            pid, _d = M.ANALOG[fn]
            out.append(_row(sp, fn, S[(pid, fn)], 'fixed', False, 'analog function %s of %s' % (fn, pin), sp['fact'], 'cited:datasheet Table 2-6 Analog Functions p.21', und=_ANALOG_UND))
            continue
        pid, inp, outp = M.IOMUX[fn]
        first = S.get((pid, inp)) or S.get((pid, outp)) or by_signal.get(inp or outp)
        typ = M.IOMUX_TYPE.get(fn, '')
        others = ', '.join(x for x in (inp, outp) if x and x != first['signal'])
        out.append(_row(sp, fn, first, 'fixed', True, 'IO MUX function %s of %s (type %s): the %s signal, bypassing the GPIO matrix' % (fn, pin, typ or '?', M.PERIPHERALS[pid][1]), sp['fact'],
                        'cited:datasheet Table 2-4 pp.19-20 (type %s); TRM Table 5.12-1 p.174' % typ, group=grp,
                        notes=_GROUP_WHY + ('; also carries %s' % others if others else '')))
    return out


def _matrix_for(sp, by_signal, bp_by_pad):
    """c3-derive: the 120 GPIO-matrix-routed rows of ONE pad - DERIVED on read (never stored); the same fields the stored rows had, plus provenance 'derived'."""
    out = []
    g = _gpio(sp)
    _pn, _name, _lead, prio = T.PRIORITY[g]
    grp = _group(g)
    pin = sp['pin']
    bp = bp_by_pad.get(sp['name'])
    refs = json.dumps([_ref('BoardPin', bp['name'])] if bp else [])
    for no, inp, dflt, din, outp, oen, dout, page in T.SIGNALS:
        for name, direction in ((inp, 'in'), (outp, 'out')):
            if not name:
                continue
            srow = by_signal[name]
            pid = srow['peripheral'].split(':', 1)[1]
            iface = _IFACE_OF.get(pid)
            pr = prio.get(iface) if iface else None
            pnote = ''
            if pr:
                pnote = 'Table 2-7 p.24: %s on %s is priority P%d%s' % (iface, pin, pr[1], (' (use with caution: %s, §2.3.4 p.23)' % M.CAUTION[g]) if pr[1] >= 3 and g in M.CAUTION else '')
            row = _row(sp, name, srow, 'matrix', direction == 'out', '%s on %s through the GPIO matrix (%s signal no. %d)' % (name, pin, 'input' if direction == 'in' else 'output', no),
                       srow['fact'], 'cited:TRM §5.1 p.159 (any pad) + Table 5.11-1 p.%d' % page, group=grp if direction == 'out' else '',
                       und='' if direction == 'out' else 'inputs are not grouped: one pad may feed several peripheral input signals (TRM §5.4.3 note 1, p.163)',
                       notes=pnote)
            row['board_pins_refs_json'] = refs
            row['provenance'] = 'derived'
            out.append(row)
    return out


def bound_pads(board_pin_rows):
    """{SocPin row name: BoardPin row} for the C3 board's pads that have a BoardPin."""
    bps = {}
    for bp in board_pin_rows:
        if bp.get('soc_pin', '').startswith('GPIO') and bp.get('board') == EV.BOARD:
            bps['%s:%s' % (SOC, bp['soc_pin'])] = bp
    return bps


def matrix_pin_functions(soc_pin_rows, signal_rows, board_pin_rows):
    """The DERIVED PinFunction rows (routing 'matrix'): every valid Table 5.11-1 signal on every pad, in the order they used to be stored (pad by pad)."""
    by_signal = _by_signal(signal_rows)
    bps = bound_pads(board_pin_rows)
    out = []
    for sp in soc_pin_rows:
        if sp['soc'] == SOC:
            out.extend(_matrix_for(sp, by_signal, bps))
    return out


def pin_functions(soc_pin_rows, signal_rows, board_pin_rows=()):
    """The FULL set as it used to be stored: per pad the fixed rows then the matrix rows (kept for the equivalence proof; the seed stores fixed_pin_functions only)."""
    S = {(s['peripheral'].split(':', 1)[1], s['signal']): s for s in signal_rows}
    by_signal = _by_signal(signal_rows)
    bps = bound_pads(board_pin_rows)
    out = []
    for sp in soc_pin_rows:
        if sp['soc'] == SOC:
            out.extend(_fixed_for(sp, S, by_signal))
            out.extend(_matrix_for(sp, by_signal, bps))
    return out


def link(peripheral_rows, signal_rows, pf_rows, soc_pin_rows, board_pin_rows):
    """Fill the reverse `*_refs_json` columns IN PLACE (the generic object page walks them both ways)."""
    per_sig, per_pf, sig_pf, pin_pf = {}, {}, {}, {}
    for s in signal_rows:
        per_sig.setdefault(s['peripheral'], []).append(_ref('PeripheralSignal', s['name']))
    for f in pf_rows:
        per_pf.setdefault(f['peripheral'], []).append(_ref('PinFunction', f['name']))
        sig_pf.setdefault(f['signal'], []).append(_ref('PinFunction', f['name']))
        pin_pf.setdefault(f['soc_pin'], []).append(_ref('PinFunction', f['name']))
    for p in peripheral_rows:
        p['signals_refs_json'] = json.dumps(sorted(per_sig.get(p['name'], [])))
        p['pin_functions_refs_json'] = json.dumps(sorted(per_pf.get(p['name'], [])))
    for s in signal_rows:
        s['pin_functions_refs_json'] = json.dumps(sorted(sig_pf.get(s['name'], [])))
    bps = {}
    for bp in board_pin_rows:
        if bp.get('soc_pin', '').startswith('GPIO') and bp.get('board') == EV.BOARD:
            bps['%s:%s' % (SOC, bp['soc_pin'])] = bp
    for sp in soc_pin_rows:
        if sp['soc'] != SOC:
            continue
        bp = bps.get(sp['name'])
        sp['links_refs_json'] = json.dumps(([_ref('BoardPin', bp['name'])] if bp else []) + sorted(pin_pf.get(sp['name'], [])))
    for bp in bps.values():
        sp = '%s:%s' % (SOC, bp['soc_pin'])
        bp['links_refs_json'] = json.dumps([_ref('SocPin', sp)] + sorted(pin_pf.get(sp, [])))
    for f in pf_rows:
        bp = bps.get(f['soc_pin'])
        f['board_pins_refs_json'] = json.dumps([_ref('BoardPin', bp['name'])] if bp else [])


def build(soc_pin_rows, board_pin_rows):
    """{'Peripheral', 'PeripheralSignal', 'PinFunction' (the ~72 fixed rows only)} for the ESP32-C3 with reverse links (to the stored rows); the C3's SocPin / BoardPin rows gain their links in place."""
    per = peripherals()
    sig = signals(soc_pin_rows)
    pf = fixed_pin_functions(soc_pin_rows, sig)   # c3-derive: the matrix rows are derived on read (soc_functions.pin_functions), not stored
    link(per, sig, pf, soc_pin_rows, board_pin_rows)
    return {'Peripheral': per, 'PeripheralSignal': sig, 'PinFunction': pf, 'Register': registers(), 'RegisterField': register_fields()}   # rm-2b: + the drawing-set registers
