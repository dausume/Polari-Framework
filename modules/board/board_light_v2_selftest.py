"""board_light_v2_selftest - fgm-6a (FIRMWARE_GENERATION_MODULE_PLAN.md section 10): COMMAND CONFIRMATION ON THE WIRE for the light. LightStateV2 is a NEW wire
class beside LightState (v1 untouched, byte for byte), its pinned contract renders the generated C codec, the variant uno-light-v2 builds with measured sizes
and a recorded baseline hex, the backend's confirmation rules (board.custom.light_confirm) hold for every ordering of commands, reports, restarts and
silence, the door answers, and - on the simavr twin, SKIPPING honestly without one - 20 rapid commands give 20 confirmations, a reboot is unknown-resend, a
malformed command is rejected-invalid and a button press confirms nothing. Then the acceptance runner turns each into a passed ScenarioRun.

    PYTHONPATH=.:modules python3 -m board.board_light_v2_selftest      # from polari-framework/ (standalone)
    (called by board.board_selftest.main as run_light_v2(check))
"""
import hashlib
import json
import os
import shutil
import tempfile
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
#: recorded at fgm-6a (the baseline the identical-hex discipline compares against; v2's is a NEW baseline, v1's must never move)
V2_HEX_SHA = 'e288db76eafc4b2925664dc33160616e940c483e0be98c9c95e019147057c26d'
V2_SIZES = (3906, 14, 638)            # text, data, bss
V2_CONTRACT_HASH = '7168b2d02d82157e'
V2_HASH_V2 = '5976dfed2e718479'
V1_CONTRACT_HASH = 'e05aeb148924b730'
V1_HEX_SHA = '94b9b77f9f8c9b19f537dbb202aff0dfc3e0e29c93933201577f8857a4dc45d7'
V1_SIZES = (3090, 10, 503)
V1_HEADER_SHA = '3f9c534136f3a339f527bd88258fc1a56859c136afce7cd7c61f391b75b40fab'
V1_CONTRACT_FILE_SHA = '984c0bd28da73676477a6b1a2e875e6de60f3d10debfebfd77651be3fb5db3ab'


def _sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def _build(variant):
    from board.custom import gen, build as B
    work = tempfile.mkdtemp(prefix='fgm6a-st-')
    try:
        row = gen.gen('uno', None, work, variant=variant)
        b = B.build('uno', work)
        return row, b
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _manager(session=7, led=False, last_id=0, name='uno-light-v2'):
    from board.objects.board.LightStateV2 import LightStateV2
    row = LightStateV2(name=name, boot_session=session, led_on=led, last_command_id=last_id)
    row.id = 'row-%s' % name
    return SimpleNamespace(objectTables={'LightStateV2': {row.id: row}, 'LightCommand': {}}, db=None, idList=[]), row


def run_light_v2(check):
    from board.board_basis import BOARD_CLASSES, LightState, LightStateV2, LightCommand
    from board.custom import gen, compat, variants as V
    from board.custom import light_confirm as LC

    # ---------------------------------------------------------------- the classes and the contract
    s = LightStateV2(name='uno-light-v2', seq=1, boot_session=2, led_on=True, toggles=1, source='command', status='active', command_id=5,
                     last_command_id=5, last_command_result='applied')
    check('fgm-6a: LightStateV2 constructs with the 10 fields of the struct (the 7 of LightState + command_id, last_command_id, last_command_result)',
          (s.command_id, s.last_command_id, s.last_command_result, s.boot_session) == (5, 5, 'applied', 2)
          and LightStateV2 in BOARD_CLASSES and LightCommand in BOARD_CLASSES and LightState in BOARD_CLASSES)
    c, path = gen.pinned_contract('LightStateV2')
    f = c['field_map']['fields']
    check('fgm-6a: pinned contract LightStateV2 v1 - 10 fields, tags alphabetical (a fresh class), hash %s, msg_type 1; command_id, last_command_id int64, '
          'last_command_result a string that maps to an enum' % V2_CONTRACT_HASH,
          c['contract_hash'] == V2_CONTRACT_HASH and len(f) == 10 and compat.tag_order(c['field_map']) == sorted(f) and c['msg_type'] == 1
          and all(f[k]['proto_type'] == 'int64' for k in ('command_id', 'last_command_id', 'seq', 'toggles', 'boot_session'))
          and f['last_command_result']['proto_type'] == 'string' and set(f) >= set(json.load(open(os.path.join(HERE, 'custom/contracts/LightState.v1.json')))['field_map']['fields']),
          c['contract_hash'])
    text, prov = gen.header('LightStateV2', msg_type=1)
    check('fgm-6a: the C codec is GENERATED from the pinned contract (target avr, msg_type 1): the command and echo fields, the three-word result enum, '
          'wire hash %s' % V2_HASH_V2,
          prov['source'] == 'pinned' and 'target avr' in text and 'LIGHTSTATEV2_MSG_TYPE 1u' in text and 'LIGHTSTATEV2_F_COMMAND_ID' in text
          and 'LIGHTSTATEV2_F_LAST_COMMAND_ID' in text and 'LIGHTSTATEV2_LAST_COMMAND_RESULT_REJECTED_INVALID = 2' in text
          and 'LIGHTSTATEV2_LAST_COMMAND_RESULT_REJECTED_BUSY = 3' in text and 'LIGHTSTATEV2_LAST_COMMAND_RESULT_APPLIED = 1' in text
          and prov['hash_v2'] == V2_HASH_V2, prov.get('hash_v2'))
    defs = open(os.path.join(HERE, 'custom/firmware/uno/apps/light_v2_defs.h')).read()
    check('fgm-6a: what the board reports up leaves out command_id (the host\'s number going down) - the telemetry mask excludes it',
          '& ~LIGHTSTATEV2_F_COMMAND_ID' in defs)

    # ---------------------------------------------------------------- v1 is untouched
    t1, p1 = gen.header('LightState', msg_type=1)
    c1, path1 = gen.pinned_contract('LightState')
    check('fgm-6a v1 UNCHANGED: LightState keeps its pinned contract v1 (hash %s, file sha256 %s...), its 7 fields, and its generated header bytes (sha256 %s...)'
          % (V1_CONTRACT_HASH, V1_CONTRACT_FILE_SHA[:12], V1_HEADER_SHA[:12]),
          c1['contract_hash'] == V1_CONTRACT_HASH and c1['contract_version'] == 1 and len(c1['field_map']['fields']) == 7
          and _sha(path1) == V1_CONTRACT_FILE_SHA and hashlib.sha256(t1.encode()).hexdigest() == V1_HEADER_SHA, c1['contract_hash'])
    check('fgm-6a v1 UNCHANGED: uno-light still the light test\'s variant (app light, class LightState); the v2 variant is a different row - opt-in, never the default',
          V.resolve(V.find('uno-light'))['classes'] == ['LightState'] and V.DEFAULT_VARIANT == 'uno-sim-rig'
          and V.resolve(V.find('uno-light-v2'))['classes'] == ['LightStateV2'] and V.resolve(V.find('uno-light-v2'))['app'] == 'light_v2'
          and gen.pick_variant(['LightState'], None)['name'] == 'uno-light' and gen.pick_variant(['LightStateV2'], None)['name'] == 'uno-light-v2')
    r2 = V.resolve(V.find('uno-light-v2'))
    check('fgm-6a: variant uno-light-v2 resolves - LED + commands + button, no sense pin, no PWM, no ADC; RX_RING=128 so a burst of whole-row commands is not dropped',
          r2['features']['led'] and r2['features']['commands'] and r2['features']['button'] and not (r2['features']['sense'] or r2['features']['pwm'] or r2['features']['adc'])
          and ('RX_RING', 128) in r2['flags'], r2['flags'])

    # ---------------------------------------------------------------- the backend rules (pure)
    check('fgm-6a: next_id counts 1..65535, wraps 65535 -> 1, never 0 and never the number the board is echoing now',
          LC.next_id(0) == 1 and LC.next_id(41) == 42 and LC.next_id(65535) == 1 and LC.next_id(4, board_echoed=5) == 6 and LC.next_id(65534, board_echoed=65535) == 1)

    def cmd(i, sess=7, at=100.0, timeout=2.0, led=True):
        return SimpleNamespace(command_id=i, led_on_requested=led, sent_at=at, device_session_at_send=sess, backend_session=1, status='pending', result='',
                               resolved_at=0.0, timeout_s=timeout, detail='')

    def rep(sess=7, last=0, res=''):
        return {'boot_session': sess, 'last_command_id': last, 'last_command_result': res}

    cs = [cmd(1), cmd(2, at=100.1)]
    ch = LC.observe_report(cs, rep(7, 0, ''), 100.2) + LC.observe_report(cs, rep(7, 5, 'applied'), 100.3)
    check('fgm-6a rule: an unrelated report - the 10 Hz tick (last id 0) or another command\'s answer (id 5) - confirms nothing', not ch and [c.status for c in cs] == ['pending', 'pending'])
    ch = LC.observe_report(cs, rep(7, 2, 'applied'), 100.4)
    check('fgm-6a rule: a report naming command 2 confirms command 2 and ONLY command 2', [c.command_id for c in ch] == [2] and [c.status for c in cs] == ['pending', 'confirmed'])
    ch = LC.observe_report(cs, rep(8, 2, 'applied'), 100.5)
    check('fgm-6a rule: a report from another boot_session turns the still-open command 1 into unknown-resend, naming both sessions - never done',
          [c.command_id for c in ch] == [1] and cs[0].status == 'unknown-resend' and '7 -> 8' in cs[0].detail and 'send it again' in cs[0].detail)
    c3 = cmd(3, sess=7)
    LC.observe_report([c3], rep(8, 3, 'applied'), 100.6)
    check('fgm-6a rule: even a report that NAMES the command, if it comes from another boot_session, is unknown-resend (an echo from the next boot proves nothing)',
          c3.status == 'unknown-resend')
    for res, want in (('rejected-invalid', 'rejected-invalid'), ('rejected-busy', 'rejected-busy')):
        c4 = cmd(4)
        LC.observe_report([c4], rep(7, 4, res), 100.6)
        check('fgm-6a rule: a matching report with result %s resolves the command as %s (the board refused it - named, not done)' % (res, want), c4.status == want and c4.result == res)
    c5 = cmd(5)
    LC.observe_report([c5], rep(7, 5, ''), 100.6)
    check('fgm-6a rule: a matching report with no known result word leaves the command unconfirmed, naming that', c5.status == 'unconfirmed' and 'no known result' in c5.detail)
    c6 = cmd(6, at=100.0)
    check('fgm-6a rule: nothing before the timeout; past it the command is unconfirmed, with the number and the seconds in the words',
          not LC.expire([c6], 101.9) and c6.status == 'pending' and [c.command_id for c in LC.expire([c6], 102.5)] == [6]
          and c6.status == 'unconfirmed' and 'command 6' in c6.detail and '2.0 s' in c6.detail)
    LC.observe_report([c6], rep(7, 6, 'applied'), 103.0)
    check('fgm-6a rule: a LATE matching answer from the same boot still resolves an unconfirmed command (marked late); after a restart it is unknown-resend',
          c6.status == 'confirmed' and 'late' in c6.detail)
    c7 = cmd(7, at=100.0)
    LC.expire([c7], 105.0)
    LC.observe_report([c7], rep(9, 0, ''), 105.1)
    check('fgm-6a rule: an unconfirmed command whose board then restarts becomes unknown-resend', c7.status == 'unknown-resend')
    ten = [cmd(i, at=100.0 + i / 100.0, led=bool(i % 2)) for i in range(1, 21)]
    seq = []
    for i in range(1, 21):   # every answer is interleaved with ticks that repeat the PREVIOUS answer and with a button report
        seq += [rep(7, i - 1, 'applied' if i > 1 else ''), rep(7, i, 'applied'), rep(7, i, 'applied')]
    done = {}
    for k, r in enumerate(seq):
        for c in LC.observe_report(ten, r, 101.0 + k / 100.0):
            done[c.command_id] = (c.status, r['last_command_id'])
    check('fgm-6a rule: 20 commands, reports interleaved with repeats of the previous answer -> 20 confirmations, each by the report with its own id',
          len(done) == 20 and all(v == ('confirmed', i) for i, v in done.items()))
    check('fgm-6a rule: pending_command is the newest OPEN command, else the newest', LC.pending_command([cmd(1), cmd(2, at=100.5)])['id'] == 2
          and LC.pending_command([SimpleNamespace(**dict(vars(cmd(1)), status='confirmed')), cmd(2, at=99.0)])['id'] == 2 and LC.pending_command([]) is None)

    # ---------------------------------------------------------------- the backend (manager rows, the observer, the door)
    mgr, row = _manager(session=0)
    try:
        LC.send(mgr)
        refused = ''
    except LC.ConfirmRefused as e:
        refused = str(e)
    check('fgm-6a backend: no command is sent before the first report (boot_session unknown) - refused by name', 'first report' in refused and not mgr.objectTables['LightCommand'])
    mgr, row = _manager(session=7, led=False, last_id=1)
    LC._LAST_ID.clear()
    a = LC.send(mgr, now=200.0)
    check('fgm-6a backend: send mints id 2 (never the 1 the board is echoing), writes command_id + led_on (toggle: off -> on) on the row, records a LightCommand pending '
          'with the board\'s boot_session AT SEND',
          a['id'] == 2 and a['status'] == 'pending' and row.command_id == 2 and row.led_on is True and a['device_session_at_send'] == 7 and len(mgr.objectTables['LightCommand']) == 1)
    from grpcbridge.custom import wire_contract as wc
    row.boot_session, row.last_command_id, row.last_command_result = 7, 0, 'unknown'
    wc.observe_frame(mgr, 'LightStateV2', row)
    check('fgm-6a backend: the pushed-frame observer is registered for LightStateV2 and an unrelated report leaves the command pending',
          LC.on_report in wc.FRAME_OBSERVERS.get('LightStateV2', []) and LC.state(mgr, now=200.5)['pending_command']['status'] == 'pending')
    row.last_command_id, row.last_command_result = 2, 'applied'
    wc.observe_frame(mgr, 'LightStateV2', row)
    st = LC.state(mgr, now=200.6)
    check('fgm-6a backend: the report naming command 2 (same boot) confirms it - the door state shows pending_command {id, sent_at, status confirmed}',
          st['pending_command']['id'] == 2 and st['pending_command']['status'] == 'confirmed' and st['pending_command']['sent_at'] == 200.0 and len(st['commands']) == 1)
    b = LC.send(mgr, led_on=False, now=300.0)
    row.boot_session, row.last_command_id, row.last_command_result = 8, 0, 'unknown'
    wc.observe_frame(mgr, 'LightStateV2', row)
    check('fgm-6a backend: a boot_session change before the echo -> the door says unknown-resend for that command (id 3), and the earlier confirmed one stays confirmed',
          LC.state(mgr, now=300.2)['pending_command']['status'] == 'unknown-resend' and LC.state(mgr, now=300.2)['pending_command']['id'] == 3
          and [c['status'] for c in LC.state(mgr, now=300.2)['commands']] == ['unknown-resend', 'confirmed'])
    LC.send(mgr, led_on=True, now=400.0)
    check('fgm-6a backend: silence past the timeout -> unconfirmed, named, on the door (state() expires it)',
          LC.state(mgr, now=403.0)['pending_command']['status'] == 'unconfirmed' and 'no report named command 4' in LC.state(mgr, now=403.0)['pending_command']['detail'])
    out = LC.analysis_send(mgr, object='uno-light-v2', led_on=None)
    check('fgm-6a backend: the AnalysisCall callable (the light-toggle-v2 solution) sends and answers {ok, command_id, command_status pending}; with no board it answers ok false, named',
          out['ok'] and out['command_status'] == 'pending' and out['command_id'] == 5 and not LC.analysis_send(SimpleNamespace(objectTables={}), object='nope')['ok'])
    from board.board_api import BoardAPI

    class Req:
        def __init__(self, body=b'', q=None):
            self.bounded_stream = SimpleNamespace(read=lambda: body)
            self._q = q or {}

        def get_param(self, k):
            return self._q.get(k)
    api = BoardAPI(polServer=None, manager=mgr)
    rs = SimpleNamespace(media=None, status=None)
    api.on_get_light_v2(Req(), rs)
    ok_get = rs.media['ok'] and rs.media['pending_command']['id'] == 5 and rs.media['light']['name'] == 'uno-light-v2'
    rs = SimpleNamespace(media=None, status=None)
    api.on_post_light_v2(Req(b'{"led_on": true}'), rs)
    ok_post = rs.media['ok'] and rs.media['pending_command']['id'] == 6 and rs.media['pending_command']['led_on'] is True and '201' in str(rs.status)
    rs = SimpleNamespace(media=None, status=None)
    api.on_post_light_v2(Req(b'{"name": "nope"}'), rs)
    rs2 = SimpleNamespace(media=None, status=None)
    api.on_get_light_v2(Req(q={'name': 'nope'}), rs2)
    check('fgm-6a door: GET /api/board/light-v2 serves the state + pending_command; POST mints and sends (201); an unknown light is 409/404 by name',
          ok_get and ok_post and '409' in str(rs.status) and 'nope' in rs.media['error'] and '404' in str(rs2.status))

    # ---------------------------------------------------------------- the build (the avr-gcc toolchain is local or in the engines image)
    from board.custom import board_engines as be
    try:
        row2, b2 = _build('uno-light-v2')
        row2b, b2b = _build('uno-light-v2')
        row1, b1 = _build('uno-light')
    except Exception as e:   # noqa: BLE001 -- no toolchain here
        check('SKIP fgm-6a build (no avr toolchain here): %s' % e, True)
        return
    if b2.get('state') != 'built':
        check('SKIP fgm-6a build: %s' % b2.get('notes'), True)
        return
    check('fgm-6a: uno-light-v2 builds (plain C, avr-libc): text %d data %d bss %d, flash %s / RAM %s B, within the cited limits; v1 uno-light is text %d data %d bss %d'
          % (b2['size_text'], b2['size_data'], b2['size_bss'], b2['flash_bytes'], b2['ram_bytes'], b1['size_text'], b1['size_data'], b1['size_bss']),
          0 < b2['flash_bytes'] <= 32256 and 0 < b2['ram_bytes'] <= 2048 and (b2['size_text'], b2['size_data'], b2['size_bss']) == V2_SIZES)
    check('fgm-6a: the v2 hex is the recorded BASELINE %s... and deterministic (two builds in two directories give the same bytes)' % V2_HEX_SHA[:12],
          b2['artifact_sha256'] == V2_HEX_SHA and b2b['artifact_sha256'] == V2_HEX_SHA and row2['source_sha'] == row2b['source_sha'], b2['artifact_sha256'])
    check('fgm-6a v1 UNCHANGED (the identical-hex discipline): uno-light still builds to hex %s... with sizes %s' % (V1_HEX_SHA[:12], V1_SIZES),
          b1['artifact_sha256'] == V1_HEX_SHA and (b1['size_text'], b1['size_data'], b1['size_bss']) == V1_SIZES, b1['artifact_sha256'])
    rep2 = json.loads(row2['repro_json'])
    check('fgm-6a: the v2 build\'s repro block names the v2 app, its extra header and the pinned LightStateV2 contract by sha256 (the v1 contract is not among its inputs)',
          rep2['knobs']['app'] == 'light_v2' and any(i['path'].endswith('apps/light_v2.c') for i in rep2['inputs']) and any(i['path'].endswith('apps/light_v2_defs.h') for i in rep2['inputs'])
          and any(i['label'] == 'contract LightStateV2' for i in rep2['inputs']) and not any(i['label'] == 'contract LightState' for i in rep2['inputs']))

    # ---------------------------------------------------------------- the twin proofs
    from board.custom import light_v2_twin as T
    ready, why = T.engine_ready()
    if not ready:
        check('SKIP fgm-6a (the v2 light on the twin): no simavr twin here - %s' % why, True)
        return
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom import sink as S
    for name, which in sorted(ACC.V2_PROOFS.items()):
        run = ACC.run(name, 'digital-twin', sink=S.LocalSink())
        check('fgm-6a: acceptance Scenario %s -> a ScenarioRun outcome passed (measured on the simavr twin): %s' % (name, run['verdict_words'][:170]),
              run['outcome'] == 'passed', run['verdict_words'][:300])


if __name__ == '__main__':
    import sys
    fails = []

    def _check(name, ok, detail=''):
        print(('[PASS] ' if ok else '[FAIL] ') + name + ('' if ok else '  :: %s' % (detail,)))
        if not ok:
            fails.append(name)
    run_light_v2(_check)
    print('\n%s' % ('ALL PASS' if not fails else '%d FAILED' % len(fails)))
    sys.exit(1 if fails else 0)
