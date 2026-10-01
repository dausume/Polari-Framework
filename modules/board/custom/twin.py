"""
@module board.custom.twin

`pol board twin uno up|down|status` (brd-1, plan §5): the SAME .hex `pol board build` produced (the one `flash` would
write) runs in simavr as an ATmega328P at 16 MHz — `polari-avr-twin` (prf-board-engines: libsimavr with USART0↔TCP,
the ADC0 stimulus and the PORTB5 trace) — and the host end is a pty at a stable link (custom/twin_pty.py). The Java
bridge attaches there with `source=serial, serialDevice=<link>` exactly as at Renode's pty or a real UNO's by-id path.

Where the twin runs (the engines ladder, engine `avr-twin`): a local polari-avr-twin binary → a container of the
board engines image on THIS docker (`prf-board-twin-<board>`, TCP published on 127.0.0.1 only) → refusal. A remote
worker is not a rung: the twin is a long-lived TCP port, not a /run request.

The TMP36 is stimulated from OUTSIDE the firmware: simavr's ADC_IRQ_ADC0 carries millivolts — `--adc0-mv 750` (25 °C)
or `--adc0-ramp 700,800,20000` (a 20 s triangle, 20 → 30 °C). No build-time knob is needed.

State lives in <work>/twin.json; the twin's JSON lines (ready / status / pb5 edges) in <work>/twin.log.
"""
import datetime
import json
import os
import signal
import subprocess
import sys
import time

from board.custom import board_engines as be, gen

DEFAULT_TCP = 9831
DEFAULT_LINK = '/tmp/polari-uno-twin-uart'


class TwinRefused(RuntimeError):
    pass


def _state_path(work):
    return os.path.join(work, 'twin.json')


def read_state(work):
    try:
        return json.load(open(_state_path(work)))
    except Exception:
        return None


def _pid_alive(pid):
    try:   # our own child that exited is a zombie until reaped — reap it, it is not alive
        done, _ = os.waitpid(int(pid), os.WNOHANG)
        if done:
            return False
    except ChildProcessError:
        pass   # not our child (another `pol` invocation started it): fall through to the signal probe
    except Exception:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def _container_alive(name):
    try:
        p = subprocess.run(['docker', 'inspect', '-f', '{{.State.Running}}', name], capture_output=True, text=True, timeout=15)
        return p.stdout.strip() == 'true'
    except Exception:
        return False


def twin_args(hex_path, tcp, adc0_mv=750, adc0_ramp='', realtime=True, adc_mv=None):
    a = ['--hex', hex_path, '--mcu', 'atmega328p', '--freq', '16000000', '--tcp', str(tcp), '--status-ms', '1000']
    a += ['--adc0-ramp', adc0_ramp] if adc0_ramp else ['--adc0-mv', str(int(adc0_mv))]
    for ch, mv in sorted((adc_mv or {}).items()):   # brd-fi: A1..A5 held at fixed millivolts (uno-adc-sweep)
        a += ['--adc-mv', '%d=%d' % (int(ch), int(mv))]
    return a + ([] if realtime else ['--free'])


def hex_data_bytes(path):
    """The flash bytes an Intel HEX carries (data records only) — what a loader must report back."""
    n = 0
    for line in open(path):
        if line.startswith(':') and line[7:9] == '00':
            n += int(line[1:3], 16)
    return n


def up(board='uno', work=None, tcp=DEFAULT_TCP, link=DEFAULT_LINK, adc0_mv=750, adc0_ramp='', realtime=True, wait_s=10.0,
       build_dir=None, adc_mv=None):
    """build_dir (brd-fi): run THAT stored build (the installer's twin target); the twin's own state stays in work."""
    board = gen.board_name(board)
    work = work or gen.default_work(board)
    st = read_state(work)
    if st and status(board, work)['alive']:
        raise TwinRefused('the %s twin is already up (%s) — `pol board twin uno down` first' % (board, st.get('where')))
    row = gen.read_record(build_dir or work)
    if row.get('state') not in ('built', 'flashed') or not row.get('hex_path') or not os.path.isfile(row['hex_path']):
        raise TwinRefused('no built firmware in %s (state %r) — `pol board build uno` first; the twin runs the SAME .hex a board is flashed with'
                          % (work, row.get('state')))
    where = be.resolve('avr-twin')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        raise TwinRefused('no simavr twin here: %s' % (where['why'] if where['how'] == 'refused' else
                                                         '%s resolves to a %s worker, but the twin is a long-lived TCP port on this device, not a /run request' % ('avr-twin', where['how'])))
    os.makedirs(work, exist_ok=True)
    log_path = os.path.join(work, 'twin.log')
    log = open(log_path, 'w')
    state = {'board': board, 'how': where['how'], 'where': where['where'], 'tcp': tcp, 'link': link, 'hex': row['hex_path'],
             'hex_sha256': row['artifact_sha256'], 'build': row['name'], 'variant': row.get('variant', ''),
             'adc0': adc0_ramp or '%d mV' % int(adc0_mv), 'adc_mv': {str(k): int(v) for k, v in (adc_mv or {}).items()}, 'realtime': realtime,
             'started_at': datetime.datetime.now().isoformat(timespec='seconds'), 'log': log_path}
    if where['how'] == 'local-binary':
        p = subprocess.Popen([where['where']] + twin_args(row['hex_path'], tcp, adc0_mv, adc0_ramp, realtime, adc_mv), stdout=log, stderr=subprocess.STDOUT,
                             start_new_session=True)
        state['pid'] = p.pid
    else:
        name = 'prf-board-twin-%s' % board
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
        argv = ['docker', 'run', '-d', '--name', name, '-p', '127.0.0.1:%d:9831' % tcp, '-v', '%s:/fw:ro' % os.path.dirname(row['hex_path']),
                where['where'], 'polari-avr-twin'] + twin_args('/fw/firmware.hex', 9831, adc0_mv, adc0_ramp, realtime, adc_mv)
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise TwinRefused('docker run failed: %s' % r.stderr.strip()[-500:])
        state['container'] = name
        state['docker_argv'] = argv
        # the twin's JSON lines follow into twin.log
        state['log_pid'] = subprocess.Popen(['docker', 'logs', '-f', name], stdout=log, stderr=subprocess.STDOUT, start_new_session=True).pid
    bridge = subprocess.Popen([sys.executable, '-m', 'board.custom.twin_pty', '--tcp', '127.0.0.1:%d' % tcp, '--link', link],
                              stdout=open(os.path.join(work, 'twin_pty.log'), 'w'), stderr=subprocess.STDOUT, start_new_session=True,
                              cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                              env=dict(os.environ, PYTHONPATH='.:modules'))
    state['pty_pid'] = bridge.pid
    json.dump(state, open(_state_path(work), 'w'), indent=1)
    t0 = time.time()
    while time.time() - t0 < wait_s:
        if os.path.islink(link) and _ready(log_path):
            break
        time.sleep(0.1)
    s = status(board, work)
    if not s['alive']:
        down(board, work)
        raise TwinRefused('the twin did not come up: %s' % open(log_path).read()[-800:])
    return s


def ready_line(log_path):
    """The twin's {"t":"ready", …} line (flash_bytes_loaded = what simavr read from the .hex), or None."""
    try:
        for line in open(log_path):
            line = line.strip()
            if line.startswith('{') and '"ready"' in line:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get('t') == 'ready':
                    return d
    except Exception:
        pass
    return None


def _ready(log_path):
    try:
        return any('"t":"ready"' in line for line in open(log_path))
    except Exception:
        return False


def last_status(log_path):
    last = None
    try:
        for line in open(log_path):
            line = line.strip()
            if line.startswith('{'):
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get('t') in ('status', 'exit', 'ready'):
                    last = d
    except Exception:
        pass
    return last


def status(board='uno', work=None):
    board = gen.board_name(board)
    work = work or gen.default_work(board)
    st = read_state(work)
    if not st:
        return {'board': board, 'alive': False, 'state': 'down'}
    twin_alive = _container_alive(st['container']) if st.get('container') else _pid_alive(st.get('pid', 0))
    pty_alive = _pid_alive(st.get('pty_pid', 0))
    return dict(st, alive=twin_alive and pty_alive, twin_alive=twin_alive, pty_alive=pty_alive,
                link_present=os.path.islink(st.get('link', '')), last=last_status(st.get('log', '')),
                state='up' if twin_alive and pty_alive else 'degraded')


def _kill(pid):
    try:
        os.killpg(int(pid), signal.SIGTERM)
    except Exception:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except Exception:
            pass


def down(board='uno', work=None):
    board = gen.board_name(board)
    work = work or gen.default_work(board)
    st = read_state(work)
    if not st:
        return {'board': board, 'state': 'down', 'note': 'was not up'}
    _kill(st.get('pty_pid', 0))
    if st.get('container'):
        subprocess.run(['docker', 'stop', '-t', '3', st['container']], capture_output=True, timeout=60)
        subprocess.run(['docker', 'rm', '-f', st['container']], capture_output=True, timeout=60)
        _kill(st.get('log_pid', 0))
    else:
        _kill(st.get('pid', 0))
    for _ in range(30):
        if not _pid_alive(st.get('pty_pid', 0)) and not (st.get('pid') and _pid_alive(st['pid'])):
            break
        time.sleep(0.1)
    for pid in (st.get('pty_pid', 0), st.get('pid', 0)):   # a process that ignored SIGTERM for 3 s is killed
        if pid and _pid_alive(pid):
            try:
                os.killpg(int(pid), signal.SIGKILL)
            except Exception:
                pass
    if os.path.islink(st.get('link', '')):
        try:
            os.unlink(st['link'])
        except OSError:
            pass
    last = last_status(st.get('log', ''))
    os.remove(_state_path(work))
    return {'board': board, 'state': 'down', 'last': last}


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol board twin')
    ap.add_argument('board')
    ap.add_argument('verb', choices=('up', 'down', 'status'))
    ap.add_argument('--work')
    ap.add_argument('--tcp', type=int, default=DEFAULT_TCP)
    ap.add_argument('--link', default=DEFAULT_LINK)
    ap.add_argument('--adc0-mv', type=int, default=750)
    ap.add_argument('--adc0-ramp', default='')
    ap.add_argument('--adc-mv', action='append', default=[], help='CH=MV for A1..A5 (repeatable; uno-adc-sweep)')
    ap.add_argument('--free', action='store_true', help='no real-time pacing (as fast as simavr runs)')
    a = ap.parse_args(argv)
    try:
        if a.verb == 'up':
            s = up(a.board, a.work, a.tcp, a.link, a.adc0_mv, a.adc0_ramp, not a.free,
                   adc_mv={int(x.split('=')[0]): int(x.split('=')[1]) for x in a.adc_mv})
            print('[ OK ] the %s twin is up (%s: %s), build %s' % (s['board'], s['how'], s.get('container') or s.get('pid'), s['build']))
            print('       UART pty  %s   (bridge: source=serial, serialDevice=%s)' % (s['link'], s['link']))
            print('       ADC0      %s (TMP36: 750 mV = 25 °C)   ·   log %s' % (s['adc0'], s['log']))
        elif a.verb == 'down':
            s = down(a.board, a.work)
            print('[ OK ] %s twin down%s' % (s['board'], ('; last: ' + json.dumps(s['last'])) if s.get('last') else ''))
        else:
            s = status(a.board, a.work)
            print(json.dumps({k: v for k, v in s.items() if k != 'docker_argv'}, indent=1))
    except (gen.GenRefused, TwinRefused) as e:
        print('[REFUSED] %s' % e)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
