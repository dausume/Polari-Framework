"""
@module board.custom.twin_c3

`pol board twin c3 up|down|status` (sc-3): the SAME merged flash image `pol board build c3` produced runs in Espressif's
QEMU fork (`qemu-system-riscv32 -machine esp32c3`, esp_develop_9.2.2_20260417, GPL-2.0) through `polari-c3-run --serve`:
UART0 — the SimRigState frames — on TCP, UART1 — the trace lines — to a file in the twin, `-icount 3` with sleep=on (virtual
time follows the wall clock while the firmware idles, so the bridge sees ≈ real time). The host end is the UNO twin's pty
pump (board.custom.twin_pty) at a stable link, so the Java bridge attaches with `source=serial, serialDevice=<link>`
exactly as at the UNO twin or a real board. BoardDefinition.twin = `qemu:esp32c3`.

What the QEMU fork does NOT emulate for the C3 (read from hw/riscv/esp32c3.c @ esp-develop-9.2.2-20260417): the USB
Serial/JTAG peripheral is a register stub with no character device — so the twin's host channel is UART0 (on silicon,
UART0 is GPIO21/20 through a dev board's USB-UART); no RTC watchdog; the docs: no free-running mode (-icount required).

Where it runs (engine `c3-run`, the esp family of the ladder): a local polari-c3-run → a container of the esp engines image
on THIS docker (`prf-board-twin-c3`, TCP published on 127.0.0.1 only) → refusal. A remote worker is not a rung: the twin
is a long-lived TCP port, not a /run request.

State lives in <work>/twin.json; the twin's ready line in <work>/twin.log; the trace lines stay in the twin
(`status` reads their tail).
"""
import datetime
import json
import os
import subprocess
import sys
import time

from board.custom import board_engines as be, gen, gen_c3
from board.custom import twin as T

DEFAULT_TCP = 9832
DEFAULT_LINK = '/tmp/polari-c3-twin-uart'
INNER_TCP = 9851
CONTAINER = 'prf-board-twin-c3'
TWIN = 'qemu:esp32c3'


class TwinRefused(RuntimeError):
    pass


def serve_args(image, tcp, trace):
    return [image, '--serve', str(int(tcp)), '--trace', trace]


def up(work=None, tcp=DEFAULT_TCP, link=DEFAULT_LINK, wait_s=30.0, build_dir=None, docker='docker'):
    work = work or gen_c3.default_work()
    st = T.read_state(work)
    if st and status(work)['alive']:
        raise TwinRefused('the C3 twin is already up (%s) — `pol board twin c3 down` first' % st.get('where'))
    row = gen.read_record(build_dir or work)
    img = row.get('image_path') or row.get('hex_path') or ''
    if row.get('board_definition') != gen_c3.BOARD or row.get('state') not in ('built', 'flashed') or not os.path.isfile(img):
        raise TwinRefused('no built C3 image in %s (state %r) — `pol board build c3` first; the twin boots the SAME merged image'
                          % (build_dir or work, row.get('state')))
    where = be.resolve('c3-run')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        raise TwinRefused('no C3 twin here: %s' % (where['why'] if where['how'] == 'refused' else
                                                  'c3-run resolves to a %s worker, but the twin is a long-lived TCP port on this device' % where['how']))
    os.makedirs(work, exist_ok=True)
    log_path = os.path.join(work, 'twin.log')
    log = open(log_path, 'w')
    state = {'board': gen_c3.BOARD, 'twin': TWIN, 'how': where['how'], 'where': where['where'], 'tcp': tcp, 'link': link, 'image': img,
             'image_sha256': row.get('artifact_sha256', ''), 'build': row['name'], 'variant': row.get('variant', ''),
             'started_at': datetime.datetime.now().isoformat(timespec='seconds'), 'log': log_path}
    if where['how'] == 'local-binary':
        trace = os.path.join(work, 'trace.log')
        p = subprocess.Popen([where['where']] + serve_args(img, tcp, trace), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        state.update(pid=p.pid, trace=trace)
    else:
        subprocess.run([docker, 'rm', '-f', CONTAINER], capture_output=True, timeout=30)
        argv = [docker, 'run', '-d', '--name', CONTAINER, '-p', '127.0.0.1:%d:%d' % (tcp, INNER_TCP), '-v', '%s:/fw:ro' % os.path.dirname(img),
                where['where'], 'polari-c3-run'] + serve_args('/fw/%s' % os.path.basename(img), INNER_TCP, '/tmp/trace.log')
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise TwinRefused('docker run failed: %s' % r.stderr.strip()[-500:])
        state.update(container=CONTAINER, docker_argv=argv, trace='container:/tmp/trace.log')
        state['log_pid'] = subprocess.Popen([docker, 'logs', '-f', CONTAINER], stdout=log, stderr=subprocess.STDOUT, start_new_session=True).pid
    fw = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    bridge = subprocess.Popen([sys.executable, '-m', 'board.custom.twin_pty', '--tcp', '127.0.0.1:%d' % tcp, '--link', link],
                              stdout=open(os.path.join(work, 'twin_pty.log'), 'w'), stderr=subprocess.STDOUT, start_new_session=True,
                              cwd=fw, env=dict(os.environ, PYTHONPATH='.:modules'))
    state['pty_pid'] = bridge.pid
    json.dump(state, open(os.path.join(work, 'twin.json'), 'w'), indent=1)
    t0 = time.time()
    while time.time() - t0 < wait_s:
        if os.path.islink(link) and T._ready(log_path):
            break
        time.sleep(0.1)
    s = status(work, docker=docker)
    if not s['alive']:
        down(work, docker=docker)
        raise TwinRefused('the C3 twin did not come up: %s' % open(log_path).read()[-800:])
    return s


def trace_tail(st, n=3, docker='docker'):
    try:
        if st.get('container'):
            r = subprocess.run([docker, 'exec', st['container'], 'tail', '-n', str(n), '/tmp/trace.log'], capture_output=True, text=True, timeout=15)
            return r.stdout.splitlines()
        return open(st['trace']).read().splitlines()[-n:]
    except Exception:
        return []


def status(work=None, docker='docker'):
    work = work or gen_c3.default_work()
    st = T.read_state(work)
    if not st:
        return {'board': gen_c3.BOARD, 'alive': False, 'state': 'down'}
    twin_alive = T._container_alive(st['container']) if st.get('container') else T._pid_alive(st.get('pid', 0))
    pty_alive = T._pid_alive(st.get('pty_pid', 0))
    return dict(st, alive=twin_alive and pty_alive, twin_alive=twin_alive, pty_alive=pty_alive, link_present=os.path.islink(st.get('link', '')),
                ready=T.ready_line(st.get('log', '')), trace_tail=trace_tail(st, docker=docker) if twin_alive else [],
                state='up' if twin_alive and pty_alive else 'degraded')


def down(work=None, docker='docker'):
    work = work or gen_c3.default_work()
    st = T.read_state(work)
    if not st:
        return {'board': gen_c3.BOARD, 'state': 'down', 'note': 'was not up'}
    tail = trace_tail(st, 5, docker=docker)
    T._kill(st.get('pty_pid', 0))
    if st.get('container'):
        subprocess.run([docker, 'stop', '-t', '3', st['container']], capture_output=True, timeout=60)
        subprocess.run([docker, 'rm', '-f', st['container']], capture_output=True, timeout=60)
        T._kill(st.get('log_pid', 0))
    else:
        T._kill(st.get('pid', 0))
    for _ in range(30):
        if not T._pid_alive(st.get('pty_pid', 0)) and not (st.get('pid') and T._pid_alive(st['pid'])):
            break
        time.sleep(0.1)
    if os.path.islink(st.get('link', '')):
        try:
            os.unlink(st['link'])
        except OSError:
            pass
    os.remove(os.path.join(work, 'twin.json'))
    return {'board': gen_c3.BOARD, 'state': 'down', 'trace_tail': tail}


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol board twin c3')
    ap.add_argument('board')
    ap.add_argument('verb', choices=('up', 'down', 'status'))
    ap.add_argument('--work')
    ap.add_argument('--tcp', type=int, default=DEFAULT_TCP)
    ap.add_argument('--link', default=DEFAULT_LINK)
    a = ap.parse_args(argv)
    try:
        if a.verb == 'up':
            s = up(a.work, a.tcp, a.link)
            print('[ OK ] the C3 twin is up (%s: %s), build %s (variant %s)' % (s['how'], s.get('container') or s.get('pid'), s['build'], s['variant']))
            print('       UART0 pty  %s   (bridge: source=serial, serialDevice=%s)' % (s['link'], s['link']))
            print('       UART1      the trace lines — `pol board twin c3 status` shows their tail')
        elif a.verb == 'down':
            s = down(a.work)
            print('[ OK ] C3 twin down%s' % (('; trace tail: ' + ' | '.join(s['trace_tail'])) if s.get('trace_tail') else ''))
        else:
            s = status(a.work)
            print(json.dumps({k: v for k, v in s.items() if k != 'docker_argv'}, indent=1))
    except (gen.GenRefused, TwinRefused) as e:
        print('[REFUSED] %s' % e)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
