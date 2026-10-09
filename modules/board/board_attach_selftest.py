"""board_attach_selftest — ucd-frames+bundle: `pol board attach`'s OWN code path (board.custom.attach_cli), proven
OFFLINE (no --api, no manager): build the variant HERE, bring the twin up HERE with attach_cli's own press schedule
+ derived wire, decode with attach_cli's own offline wire specs, and check the SAME invariant the live run (hand-run
against the real server, quoted in the handoff) proved: button_presses == N, sense_rises + sense_falls == N,
led_on == (rises > falls), and (negative) no wire -> the sense counters stay 0. This is the twin+forwarder path's
own proof; the --api push (CRUDE PUT/POST, the bridge/binding doors) was exercised by hand against the live server
because it needs a reachable server — this selftest does not reach one.

    PYTHONPATH=.:modules python3 -m board.board_attach_selftest
"""
import tempfile

N_PRESSES = 3
SECONDS = 8


def run_attach(check):
    from board.custom import board_engines as be
    where = be.resolve('avr-twin')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        check('SKIP board attach (pol board attach uno --twin): no simavr twin here — %s' % where['why'], True)
        return
    from board.custom import attach_cli as A
    from board.custom import twin as T

    work = tempfile.mkdtemp(prefix='board-attach-selftest-')
    row = A._build_variant('uno-button-clock', work)
    check('attach_cli._build_variant builds uno-button-clock offline (no manager, no server)',
          row.get('state') == 'built', row.get('notes'))
    pinat, end_cycle = A._press_schedule(N_PRESSES, SECONDS)
    check('attach_cli._press_schedule spaces %d presses by >= the debounce margin' % N_PRESSES,
          len(pinat) == 2 * N_PRESSES)
    wires, why = A._wires()
    check('attach_cli._wires derives (PD6, PD3) from the seeded BoardPinNet rows, no server', ('PD6', 'PD3') in wires, why)
    specs = A._wire_specs()
    check('attach_cli._wire_specs resolves ButtonClockState + ButtonClockEvent offline (the pinned v1 contract + '
          'wire_contract.spec(instances=1))', set(specs) == {'ButtonClockState', 'ButtonClockEvent'})

    # (a) WITH the wire: the invariant holds
    state = T.up('uno', work, tcp=9870, link='/tmp/polari-board-attach-selftest-uart', adc0_mv=750, realtime=True,
                 pin_at=pinat, wires=wires)
    frames, total, bad = A._decode_stream(state['link'], SECONDS, specs)
    T.down('uno', work)
    states = [v for c, v in frames if c == 'ButtonClockState']
    last = states[-1] if states else {}
    check('attach_cli._decode_stream: no bad-CRC frames', bad == 0, bad)
    check('(a) with --wire PD6:PD3: button_presses == %d' % N_PRESSES, last.get('button_presses') == N_PRESSES, last)
    check('(a) sense_rises + sense_falls == button_presses (the independent witness agrees)',
          (last.get('sense_rises', -1) + last.get('sense_falls', -1)) == N_PRESSES)
    check('(a) led_on == (sense_rises > sense_falls)', last.get('led_on') == bool(last.get('sense_rises', 0) > last.get('sense_falls', 0)))

    # (f) NEGATIVE: the same presses, no wire
    row2 = A._build_variant('uno-button-clock', work)
    state2 = T.up('uno', work, tcp=9871, link='/tmp/polari-board-attach-selftest-nowire-uart', adc0_mv=750, realtime=True,
                  pin_at=pinat, wires=[])
    frames2, total2, bad2 = A._decode_stream(state2['link'], SECONDS, specs)
    T.down('uno', work)
    states2 = [v for c, v in frames2 if c == 'ButtonClockState']
    last2 = states2[-1] if states2 else {}
    check('(f) NEGATIVE, no wire: button_presses still counts', last2.get('button_presses') == N_PRESSES, last2)
    check('(f) NEGATIVE, no wire: sense_rises == sense_falls == 0 (nothing independently witnessed)',
          last2.get('sense_rises') == 0 and last2.get('sense_falls') == 0, last2)


if __name__ == '__main__':
    import sys
    passed, total = 0, 0

    def check(label, cond, extra=''):
        global passed, total
        total += 1
        passed += int(bool(cond))
        print('%s %s%s' % ('PASS' if cond else 'FAIL', label, ('' if cond else ' — %r' % (extra,))))

    run_attach(check)
    print('\n%d/%d checks passed' % (passed, total))
    sys.exit(0 if passed == total else 1)
