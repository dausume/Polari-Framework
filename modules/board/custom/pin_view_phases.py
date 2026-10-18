"""
@module board.custom.pin_view_phases

pv-4 (PIN_VIEW_PLAN.md 2.4 / 2.9): THE PHASES AND THE TWO BLANK BASELINES of the pin payload. A phase is a moment of the board's life (the lifecycle phases already in the
PinLifecycleConstraint rows); a pin's state at a phase is DERIVED on every read from the rows named in `phase_basis` — nothing here is stored.

  power-up · reset   every I/O pin is an input, tri-stated, its pull-up off: drive_status `high-impedance`, pull `none`, no signal activated.
                     CITED: ATmega48A/PA/88A/PA/168A/PA/328/P datasheet DS40002061B §14.2.1 p.85 ("The port pins are tri-stated when reset condition becomes active, even if no clocks
                     are running") and Table 14-1 p.86 (DDxn = 0, PORTxn = 0: input, no pull-up, Tri-state Hi-Z); the ports' DDRx / PORTx reset values are READ from the Register rows.
                     ATmega8U2/16U2/32U2 (doc7799) §2.2.4-2.2.6 p.4-5 and §12.2.1 p.68 say the same for the 16U2.
  bootloader         blank=board only (the board as delivered has the bootloader): the pins the PinLifecycleConstraint rows RESERVE at the bootloader phase serve it (D0/D1 = the USART0
                     link, RESET answering the host's DTR); every other pin stays blank. blank=chip has no bootloader: nothing runs, everything stays blank.
  init               the Initialization Purpose's claims applied = the existing `after-init` STAGE (effective_stage). Nothing extra is derived here.
  runtime            the requested stage's claims (unchanged).
  programming / debug  the lifecycle rows only (nothing else is drawn for them); the stage is base.

BLANK BASELINES   chip  = the silicon after reset with no program (no bootloader); board = the board as delivered (the bootloader is present, cited from the board's DatasheetFact rows;
                  whether a FACTORY DEMO SKETCH is present is `undetermined` unless a row cites it).
"""
import json
import re

PHASES = ('power-up', 'reset', 'bootloader', 'init', 'runtime', 'programming', 'debug')
BLANKS = ('chip', 'board')
DEFAULT_BLANK = 'board'
BLANK_PHASES = ('power-up', 'reset')
#: the stage each phase shows. init is the Initialization Purpose's claims; the phases before init carry no claims; runtime is the caller's stage.
STAGE_OF_PHASE = {'power-up': 'base', 'reset': 'base', 'bootloader': 'base', 'init': 'after-init', 'programming': 'base', 'debug': 'base'}
BANNER = 'after every reset the pins are blank until init runs'

DS328 = 'ATmega328P datasheet DS40002061B'
CITE_RESET = '%s §14.2.1 p.85: "The port pins are tri-stated when reset condition becomes active, even if no clocks are running"' % DS328
CITE_TABLE = '%s Table 14-1 p.86: DDxn = 0, PORTxn = 0 is an input, no pull-up, Tri-state (Hi-Z)' % DS328
CITE_16U2 = 'ATmega16U2 doc7799 §2.2.4-2.2.6 p.4-5 ("pins are tri-stated when a reset condition becomes active") and §12.2.1 p.68'
CITE_TXD = '%s §20.6 p.185: with the transmitter enabled the TxDn pin is overridden by the USART as its serial output' % DS328
CITE_RXD = '%s §20.7 p.188: with the receiver enabled the RxDn pin is overridden by the USART as its serial input' % DS328


class PhaseError(ValueError):
    pass


def check_params(phase, blank):
    phase = phase or 'runtime'
    blank = blank or DEFAULT_BLANK
    if phase not in PHASES:
        raise PhaseError('unknown phase %r (phases: %s)' % (phase, ', '.join(PHASES)))
    if blank not in BLANKS:
        raise PhaseError('unknown blank baseline %r (baselines: chip = no bootloader, board = as delivered)' % blank)
    return phase, blank


def effective_stage(phase, stage):
    """The stage a phase shows: init is after-init, the phases before it are base, runtime is the caller's choice."""
    return STAGE_OF_PHASE.get(phase, stage)


# ---------------------------------------------------------------- the blank block (cited facts)
def _fact(f):
    return {'fact': f['name'], 'value': f['value'], 'unit': f.get('unit', ''), 'document': f['document'], 'where': f['page_table'], 'url': f.get('url', '')}


def blank_block(tables, board, blank, phase):
    """What the chosen baseline is, with the facts behind it: the bootloader (present or not, cited), the factory sketch (undetermined unless cited), the port registers' reset values (from the rows)."""
    from board.custom import uno_facts as UF   # the UNO's cited facts are code-owned rows; a server that has not seeded them yet reads them from the same source
    facts = {f['fact_key']: f for f in (UF.SEED_UNO_FACTS if board == UF.BOARD else [])}
    facts.update({f['fact_key']: f for f in tables.get('DatasheetFact', []) if f.get('board') == board and f.get('fact_key')})
    boot = [facts[k] for k in ('bootloader.file', 'optiboot_size', 'upload.protocol', 'upload.speed') if k in facts]
    factory = facts.get('factory_sketch')
    regs = []
    for r in sorted(tables.get('Register', []), key=lambda x: x['name']):
        if r['register'] in ('DDRB', 'PORTB', 'DDRC', 'PORTC', 'DDRD', 'PORTD', 'MCUCR') and r['soc'] == 'atmega328p':
            regs.append({'register': r['name'], 'reset_value': r['reset_value'] or 'undetermined', 'cite': '%s (%s)' % (r['document'], r['page_table']) if r['reset_value'] else (r['undetermined'] or 'bits not captured in the rows')})
    chip = blank == 'chip'
    present = 'no' if chip else ('yes' if boot else 'undetermined')
    return {'baseline': blank, 'label': 'chip blank: the silicon after reset, no program' if chip else 'board as delivered: before any of our firmware',
            'bootloader': {'present': present, 'running_in_phase': bool(not chip and boot and phase == 'bootloader'),
                           'why': 'a blank chip has no bootloader' if chip else ('the board ships with the bootloader (flash minus %s bytes is the application area)' % (facts.get('optiboot_size') or {}).get('value', '?')) if boot
                           else 'no DatasheetFact row cites a bootloader for this board', 'cites': [_fact(f) for f in boot]},
            'factory_sketch': ({'status': 'cited', 'cite': _fact(factory)} if factory else
                               {'status': 'undetermined', 'why': 'no row cites whether the board ships with a demo sketch; nothing here assumes one'}),
            'registers': regs,
            'io_pin_state': {'direction': 'input', 'drive': 'high-impedance', 'pull': 'none', 'cites': [CITE_RESET, CITE_TABLE, CITE_16U2]}}


# ---------------------------------------------------------------- the per-pin overlay
def _port_registers(tables, soc, soc_pin_row):
    out = []
    port = (soc_pin_row or {}).get('port', '')
    for reg in ('DDR%s' % port, 'PORT%s' % port):
        row = next((r for r in tables.get('Register', []) if r['name'] == '%s:%s' % (soc, reg)), None)
        if row is None:
            out.append('%s: no Register row for this chip' % reg)
        elif row['reset_value']:
            out.append('Register %s reset_value %s' % (row['name'], row['reset_value']))
        else:
            out.append('Register %s reset_value not captured in the rows' % row['name'])
    return out


def _function_in(reason, capable, family):
    """The capable function of `family` whose name the lifecycle row's reason spells out (D0: 'talks over USART0 RXD')."""
    for c in capable:
        if c['family'] == family and re.search(r'(?<![A-Za-z0-9])%s(?![A-Za-z0-9])' % re.escape(c['function']), reason or ''):
            return c
    return None


def apply(model, tables, phase, blank, board):
    """Overlays the phase on the pins (after pin_view_modes.apply_pins). Sets `phase_basis` on every pin (the rows that decided its state at this phase) and returns the response's `phase_info`."""
    socpin = {r['name']: r for r in tables.get('SocPin', [])}
    life = [r for r in tables.get('PinLifecycleConstraint', []) if r['board'] == board]
    info = {'phase': phase, 'blank': blank, 'blank_label': 'chip blank (no bootloader)' if blank == 'chip' else 'board as delivered', 'banner': BANNER if phase in BLANK_PHASES else '',
            'decided_by': [], 'undetermined': [], 'notes': [], 'pins_blank': 0, 'pins_serving': 0}
    for p in model.pins.values():
        p['phase_basis'] = []
    chips = [p for p in model.pins.values() if p['level'] in ('die', 'package') and p['kind'] == 'io']
    leg_of = {}
    for c in model.connections:
        if c['kind'] == 'to-header':
            leg_of.setdefault(c['b'], c['a'])

    def blank_pin(p):
        who16 = p.get('soc') == 'atmega16u2'
        basis = [CITE_16U2 if who16 else CITE_RESET, CITE_TABLE] + ([] if who16 else _port_registers(tables, p['soc'], socpin.get(p['soc_pin'])))
        p.update({'drive_status': 'high-impedance', 'drive_why': 'blank: tri-stated, pull-up off (%s)' % ('ATmega16U2 doc7799 §12.2.1 p.68' if who16 else 'DS40002061B §14.2.1 p.85, Table 14-1 p.86'),
                  'pull': 'none', 'activated': None, 'phase_basis': basis, 'limit_class': 'unchecked', 'limit_basis': 'blank: the pad drives nothing, so no drive limit applies yet'})
        info['pins_blank'] += 1

    if phase in BLANK_PHASES:
        for p in chips:
            blank_pin(p)
        info['decided_by'] = [CITE_RESET, CITE_TABLE, CITE_16U2]
        info['notes'].append('every I/O pin of every chip is blank at %s; the drive glyph is high-impedance and no signal is activated' % phase)
    elif phase == 'bootloader':
        for p in chips:
            blank_pin(p)
        if blank == 'chip':
            info['notes'].append('a blank chip has no bootloader: nothing runs at this phase, every I/O pin stays blank')
        else:
            serving = _serve_bootloader(model, tables, life, board, info)
            info['notes'].append('the board as delivered runs its bootloader: the pins the lifecycle rows reserve for it serve its link, everything else stays blank until init runs')
            info['decided_by'] += sorted({r for p in serving for r in p['phase_basis'] if r.startswith(board + ':')})
            info['undetermined'] += [
                'Optiboot\'s start-up LED flashes on D13 are not in the rows (the Optiboot README is not re-fetched), so D13 is shown blank',
                'the 16U2 runs its own USB-serial firmware, which no row describes: its pins are shown as the chip after reset']
    elif phase == 'init':
        info['notes'].append('init: the Initialization Purpose\'s claims applied (the after-init stage); pins no init task claims are still blank')
        info['decided_by'] = ['Initialization Purpose tasks (cmod)']
    elif phase in ('programming', 'debug'):
        info['notes'].append('%s: the lifecycle rows are listed on the pins; no pin state is drawn for this phase' % phase)
    # header pins take the state of the leg they join
    for p in model.pins.values():
        if p['level'] == 'board' and p['id'] in leg_of:
            leg = model.pins[leg_of[p['id']]]
            if leg['phase_basis']:
                p.update({'drive_status': leg['drive_status'], 'drive_why': leg['drive_why'], 'pull': leg['pull'], 'activated': leg['activated'], 'phase_basis': list(leg['phase_basis'])})
                if leg['drive_status'] == 'high-impedance' and leg['limit_basis'].startswith('blank:'):
                    p.update({'limit_class': leg['limit_class'], 'limit_basis': leg['limit_basis']})
    info['decided_by'] = list(dict.fromkeys(info['decided_by']))
    return info


def _serve_bootloader(model, tables, life, board, info):
    """The pins the lifecycle rows RESERVE at the bootloader phase serve the bootloader's link: the USART function the row names (D0/D1), or the reset line (RESET). Derived from the rows."""
    rows = [r for r in life if r['phase'] == 'bootloader' and r['policy'] == 'reserved']
    served = []
    for p in model.pins.values():
        if p['level'] not in ('die', 'package', 'board'):
            continue
        mine = [r for r in rows if (p['soc_pin'] and r['soc_pin'] == p['soc_pin']) or (p['level'] == 'board' and p['canonical'] and r['pin'] == p['canonical'])]
        if not mine:
            continue
        r = mine[0]
        uart = _function_in(r['reason'], p['capable'], 'uart')
        if uart is not None:
            tx = uart['function'].upper().startswith('TX')
            p['activated'] = {'function': uart['function'], 'resource': uart['function'], 'family': 'uart', 'signal': next((s['signal'] for s in p['signals'] if s['function'] == uart['function']), ''),
                              'direction': uart['direction']}
            p['drive_status'] = 'sources-or-sinks' if tx else 'high-impedance'
            p['drive_why'] = ('the bootloader enables the USART transmitter, which takes the pad over (DS40002061B §20.6 p.185)' if tx
                              else 'the bootloader enables the USART receiver, which takes the pad over; leakage only (DS40002061B §20.7 p.188)')
            p['phase_basis'] = [r['name'], '%s (%s)' % (r['document'], r['page_table']), CITE_TXD if tx else CITE_RXD]
        else:   # the reset line: the host's DTR pulse through C5 resets the chip into the bootloader
            reset_fn = next((c for c in p['capable'] if c['function'] == 'RESET'), None)
            p['activated'] = {'function': 'RESET', 'resource': 'DTR pulse through C5', 'family': 'reset-programming', 'signal': 'RESET', 'direction': (reset_fn or {}).get('direction', 'inputs')}
            p['phase_basis'] = [r['name'], '%s (%s)' % (r['document'], r['page_table'])]
        served.append(p)
    info['pins_serving'] = sum(1 for p in served if p['level'] != 'board')
    return served
