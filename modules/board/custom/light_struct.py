"""
@module board.custom.light_struct

scl-2 (UNO_CORE_DEMO_PLAN.md, "the struct controls the light"): THE FROM-POLARI PROOF STARTS FROM THE STRUCT. His words: "The struct being altered by the polari side button, should be what is
triggering the tasks to turn off the light ... the whole point is for the struct to be what is controlling the light."

  1. A test manager holds the light's struct row (LightState `uno-light`; ButtonClockState for the sense configs).
  2. The screen's button is run through the backend's OWN solution: `light-toggle` (hwnocode.custom.light_solutions.toggle_definition, executed by the real engine). It commits ONE StateChangeCommit
     onto the row - that committed change is the only input to the next step.
  3. The command frame is DERIVED from that committed change with the contract encoder (pinned contract -> wire spec -> grpcbridge.custom.wire_ref.encode, presence-masked to the changed
     command field) - never a hand-built frame. A write that leaves the command field unchanged derives NO frame.
  4. The frames are fed to the simavr twin (--inject). Pass when the board's struct takes the value, D6 (PORTD bit 6, read from the twin) FOLLOWS it, and the next report carries led_on with
     source=command (LightState) / status=commanded (ButtonClockState).

What is NOT run: the relay itself (the Java bridge's encoder, grpc_server.notify_commands). The frame comes from the same pinned contract the relay's generated codec comes from, encoded by the
independent Python reference codec; the relay is proven separately (hwnocode_selftest _commands_leg, javabridge selftests).

Classes: LightState (command field led_on, the light-toggle solution as is) and ButtonClockState (command field set_led; there is no light-toggle for it, so the SAME-shaped solution is built by
light_solutions.toggle_definition(command_field='set_led', object_class='ButtonClockState')).
Negative controls (real twin runs through the same judge): a write that leaves the command field unchanged, and a write of a telemetry field only - each derives no frame, and the twin run
with nothing injected shows nothing changed (D6 low, the board's struct unchanged).
"""
from types import SimpleNamespace

CPS = 16000000
CLASSES = {'LightState': {'cmd': 'led_on', 'other': 'toggles'}, 'ButtonClockState': {'cmd': 'set_led', 'other': 'drift_ms'}}
NAME = 'uno-light'


class Session:
    """One test manager + one struct row; every call runs a REAL solution and returns (committed change, frames derived from it)."""

    def __init__(self, cls_name, name=NAME):
        from board import board_basis
        self.cls_name, self.cmd, self.other = cls_name, CLASSES[cls_name]['cmd'], CLASSES[cls_name]['other']
        self.mgr = SimpleNamespace(objectTables={'AnalysisDefinition': {}, 'SolutionDefinition': {}}, objectTypingDict={}, db=None, idList=[])
        self.row = getattr(board_basis, cls_name)(manager=self.mgr, name=name)
        self.mgr.objectTables[cls_name] = {self.row.id: self.row}
        self.name, self.seq = name, 0

    def _definition(self, kind):
        from hwnocode.custom import light_solutions as LS
        if kind == 'toggle':
            return LS.toggle_definition() if self.cls_name == 'LightState' else LS.toggle_definition(object_class=self.cls_name, command_field=self.cmd)
        from polariNoCode import graph_builder as GB
        field = self.cmd if kind == 'same' else self.other
        value = getattr(self.row, field)
        entry = GB.node('write-requested', 'BackendStateChange', {'displayName': 'write the struct', 'modelName': self.cls_name, 'fieldName': field, 'changeType': 'update',
                                                                  'description': 'entry marker (scl negative control)'}, outs=[['write']])
        write = GB.node('write', 'StateChangeCommit', {'changeType': 'update', 'targetClassName': self.cls_name, 'instanceRef': GB.var_src('object'),
                                                       'fields': {field: GB.lit_src(value)}}, outs=[[]])
        return GB.solution('scl-%s-write' % kind, entry, write)

    def run(self, kind):
        """kind: 'toggle' (the light-toggle solution) | 'same' (commit the command field's current value) | 'other' (commit a telemetry field only)
        -> {'status', 'committed' [..], 'before', 'after', 'frames' [bytes]}"""
        from polariNoCode.graph_builder import execute
        from polariNoCode.graph_compilers import final_context_of
        before = getattr(self.row, self.cmd)
        led_now = bool(before)     # the light as the struct holds it now (led_on; set_led for ButtonClockState, whose row the test never reports into)
        tr = execute(self._definition(kind), manager=self.mgr, params={'object': self.name, 'led_on': led_now})
        committed = final_context_of(tr).get('_committed_changes') or []
        after = getattr(self.row, self.cmd)
        return {'status': tr.status, 'committed': committed, 'before': before, 'after': after, 'frames': self.frames(committed, before)}

    def frames(self, committed, before):
        """The command frames DERIVED from a committed change: the command field, only when it differs from what the struct held; presence-masked to that field."""
        out = []
        for ch in committed:
            if ch.get('className') != self.cls_name:
                continue
            vals = {k: v for k, v in (ch.get('fields') or {}).items() if k == self.cmd and bool(v) != bool(before)}
            if vals:
                out.append(cmd_frame(self.cls_name, self.seq, **vals))
                self.seq += 1
        return out


def cmd_frame(cls_name, seq, **vals):
    from board.custom import gen, packet_ref
    from board.custom.compat import wire_spec
    from grpcbridge.custom import wire_ref
    fmap = gen.pinned_contract(cls_name)[0]['field_map']
    spec = wire_spec(None, cls_name, fmap)
    return packet_ref.frame(1, 0, seq, wire_ref.encode(spec, vals, present=list(vals)), version=spec['wire_version'])


def _twin(variant, app, hex_bytes, frames, at_cycles, seconds):
    """-> (run, states, bad_crc, pin_d6_high): the derived frames injected at the cycles, D6 read from the twin."""
    from board.custom import variant_twin as VT
    from firmwarefaults.custom import harness
    files = {'f%d.bin' % i: f for i, f in enumerate(frames)}
    inj = []
    for i, c in enumerate(at_cycles[:len(frames)]):
        inj += ['--inject', 'f%d.bin@%d' % (i, c)]
    if app == 'light':
        argv = VT._argv(seconds, inj + VT._watch_portd())
    else:
        from board.custom import light_variant_twin as LVT
        argv = LVT._argv(variant, seconds, inj + VT._watch_portd())
    r = harness.run_files(argv, hex_bytes, files, timeout=120)
    if app == 'light':
        from board.custom import light_twin as LT
        states, bad = LT.decode(r['uart'])
    else:
        states, _ev, bad = LVT.decode(r['uart'])
    return r, states, bad, VT.led_pin_high(r)


def prove_polari(variant, app, hex_bytes):
    """-> (ok, words, frames_seen, controls [(label, judged_ok)]) - the struct-driven proof of `ensure-polari-can-control-light` on `variant`'s build (app 'light' | 'button_clock')."""
    from board.custom import light_twin as LT
    cls = 'LightState' if app == 'light' else 'ButtonClockState'
    judge = LT.judge_commands if app == 'light' else __import__('board.custom.light_variant_twin', fromlist=['x']).judge_commands
    cmd_on, cmd_off = LT.CMD_ON_CYCLE, LT.CMD_OFF_CYCLE
    ses = Session(cls)
    on = ses.run('toggle')
    off = ses.run('toggle')
    derived = on['frames'] + off['frames']
    solution_ok = (on['status'] == 'completed' and off['status'] == 'completed' and len(on['frames']) == 1 and len(off['frames']) == 1
                   and [c['fields'] for r in (on, off) for c in r['committed']] == [{ses.cmd: True}, {ses.cmd: False}])
    # run A: ON only - the board's struct takes it, D6 follows, the next report carries it
    ra, sa, bad_a, pin_a = _twin(variant, app, hex_bytes, on['frames'], [cmd_on], (cmd_on + 4 * LT.RUN_TAIL) / float(CPS))
    last_a = sa[-1] if sa else {}
    src = (last_a.get('source') == 'command' and last_a.get('toggles') == 1) if app == 'light' else (last_a.get('status') == 'commanded' and not last_a.get('button_presses'))
    a_ok = ra['ok'] and bad_a == 0 and bool(last_a.get('led_on')) and src and pin_a is True
    # run B: ON then OFF - the light goes back
    rb, sb, bad_b, pin_b = _twin(variant, app, hex_bytes, derived, [cmd_on, cmd_off], (cmd_off + 4 * LT.RUN_TAIL) / float(CPS))
    jb, wb = judge(sb)
    b_ok = rb['ok'] and bad_b == 0 and jb and pin_b is False
    # the old frame-level check, kept as the board-half check
    half = _board_half(variant, app, hex_bytes)
    # negative controls: a write that leaves the command field unchanged, and a telemetry-only write - no frame is derived and nothing changes on the twin
    rq, sq, bad_q, pin_q = _twin(variant, app, hex_bytes, [], [], (cmd_off + 4 * LT.RUN_TAIL) / float(CPS))
    lq = sq[-1] if sq else {}
    quiet = rq['ok'] and bad_q == 0 and bool(sq) and pin_q is False and not lq.get('led_on') and not (lq.get('toggles') or 0)
    ctl = []
    for kind, label in (('same', 'a write that leaves %s unchanged derives a frame' % ses.cmd), ('other', 'a write of %s only derives a frame' % ses.other)):
        w = Session(cls).run(kind)
        ctl.append((label, bool(w['frames']) or w['status'] != 'completed'))
    ctl.append(('the command judge passes a twin run with nothing injected', judge(sq)[0]))
    ok = solution_ok and a_ok and b_ok and half[0] and quiet
    words = ('the struct was altered through the backend solution light-toggle on a test manager (%d StateChangeCommit(s): %s); the command frames were DERIVED from those committed changes by the '
             'pinned-contract encoder (%d frames, none hand-built); ON: board struct led_on=%s %s, D6 %s; ON then OFF: %s, D6 %s; board-half (hand frames): %s; with nothing written the twin stays quiet (D6 low, struct unchanged): %s'
             % (len(on['committed']) + len(off['committed']), '/'.join('%s=%s' % (k, v) for r in (on, off) for c in r['committed'] for k, v in c['fields'].items()), len(derived),
                last_a.get('led_on'), ('source=%s toggles=%s' % (last_a.get('source'), last_a.get('toggles'))) if app == 'light' else ('status=%s' % last_a.get('status')),
                'high' if pin_a else 'low', wb, 'low' if pin_b is False else 'high', half[1], quiet))
    return ok, words, len(sa) + len(sb) + half[2], ctl


def _board_half(variant, app, hex_bytes):
    """The old frame-level check (hand-built SET_LED frames) - the board half only."""
    if app == 'light':
        from board.custom import light_twin as LT
        r, fr, bad = LT.run_commands(hex_bytes)
        ok, w = LT.judge_commands(fr)
    else:
        from board.custom import light_variant_twin as LVT
        r, fr, _ev, bad = LVT.run_commands(variant, hex_bytes)
        ok, w = LVT.judge_commands(fr)
    return (ok and r['ok'] and bad == 0), w, len(fr)
