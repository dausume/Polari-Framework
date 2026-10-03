"""
@module board.custom.twin_pty

The HOST end of the UNO twin's UART (brd-1): a pty whose slave is symlinked at a stable path (default
/tmp/polari-uno-twin-uart), pumped both ways to the twin's TCP port (polari-avr-twin --tcp). The Java bridge then
attaches to the link with `source=serial, serialDevice=<link>` — exactly as it attaches to Renode's pty
(grpcbridge/custom/renode_twin/README.md) and to a real UNO's /dev/serial/by-id path. Baud settings on a pty are
ignored, as on Renode's. The slave fd stays open here, so a reader closing and reopening the link never hangs it up;
a dropped TCP connection is re-dialled. Stdlib only.

    python3 -m board.custom.twin_pty --tcp 127.0.0.1:9831 --link /tmp/polari-uno-twin-uart
"""
import argparse
import os
import select
import signal
import socket
import sys
import time
import tty


def open_link(link):
    master, slave = os.openpty()
    tty.setraw(slave)
    tty.setraw(master)
    os.set_blocking(master, False)   # a full pty (nobody reading the link) drops bytes instead of stalling the pump
    name = os.ttyname(slave)
    try:
        os.unlink(link)
    except FileNotFoundError:
        pass
    os.symlink(name, link)
    return master, slave, name


def dial(host, port, stop, give_up_s=30.0):
    t0 = time.time()
    while not stop['now']:
        try:
            s = socket.create_connection((host, port), timeout=2)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(5)   # select says when to read; a send never stalls the pump past 5 s
            return s
        except OSError:
            if time.time() - t0 > give_up_s:
                raise
            time.sleep(0.2)
    return None   # asked to stop while re-dialling (down stops the pump, then the twin)


def pump(master, host, port, stop):
    sock = dial(host, port, stop)
    while sock is not None and not stop['now']:
        r, _, _ = select.select([master, sock], [], [], 0.5)
        if sock in r:
            try:
                data = sock.recv(4096)
            except (BlockingIOError, socket.timeout):
                data = None
            except OSError:   # reset by the twin
                data = b''
            if data == b'':   # the twin went away: re-dial (it may be restarting)
                sock.close()
                sock = dial(host, port, stop)
                continue
            if data:
                try:
                    os.write(master, data)
                except OSError:   # EAGAIN: the slave's queue is full, nobody is reading — a UART with no listener
                    pass
        if master in r:
            try:
                data = os.read(master, 4096)
            except (BlockingIOError, OSError):
                data = b''
            if data:
                sock.sendall(data)
    if sock is not None:
        sock.close()


def main(argv):
    ap = argparse.ArgumentParser(prog='twin_pty')
    ap.add_argument('--tcp', default='127.0.0.1:9831')
    ap.add_argument('--link', default='/tmp/polari-uno-twin-uart')
    a = ap.parse_args(argv)
    host, port = a.tcp.rsplit(':', 1)
    master, slave, name = open_link(a.link)
    stop = {'now': False}

    def _stop(*_):
        stop['now'] = True
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    import faulthandler
    faulthandler.register(signal.SIGUSR1)   # `kill -USR1 <pid>` dumps where the pump is (to twin_pty.log)
    print('twin_pty: %s -> %s <-> tcp %s' % (a.link, name, a.tcp), flush=True)
    try:
        pump(master, host, int(port), stop)
    finally:
        try:
            if os.path.islink(a.link) and os.readlink(a.link) == name:
                os.unlink(a.link)
        except OSError:
            pass
        os.close(slave)
        os.close(master)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
