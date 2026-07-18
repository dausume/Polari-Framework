"""
Selftest — acct-2: the STOMP transport, over the REAL wire.

Run from polari-framework/:
    python3 -m testing.selftest_stomp

Boots the actual StompWebSocketServer on a scratch port and drives
it with a real websocket client (the only prior coverage was the
FakeStomp publish seam in grpcbridge.selftest_serving — no test
ever opened a socket): CONNECT -> CONNECTED, SUBSCRIBE, then a
CRUDE-style publish through grpcbridge.transport_mux fan-out ->
MESSAGE frame received with the notification payload
({className, operation, timestamp, instanceIds, formatType}).
Pins the knobs: polariTreeWsEnabled=False publishes NOTHING (the
enabled publish that follows arrives first — no sleep-and-hope),
and a format-specific flag delivers on /topic/<Class>/<fmt>.
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from types import SimpleNamespace

from polariApiServer.stompWebSocketServer import (
    StompWebSocketServer, build_stomp_frame, parse_stomp_frame,
    set_stomp_server,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []
PORT = 3900 + (os.getpid() % 90)
CLASS_NAME = 'Acct2StompProbe'


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _manager(polari_tree_ws=True, flat_json_ws=False):
    """The minimal manager shape transport_mux fan-out reads."""
    config = SimpleNamespace(
        polariTreeWsEnabled=polari_tree_ws,
        flatJsonWsEnabled=flat_json_ws,
        d3ColumnWsEnabled=False, geoJsonWsEnabled=False)
    return SimpleNamespace(
        objectTypingDict={CLASS_NAME: SimpleNamespace(
            apiFormatConfig=config)},
        objectTables={})


def _start_server():
    server = StompWebSocketServer(port=PORT)
    server.start()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not server._running:
        time.sleep(0.1)
    return server


async def _recv_frame(ws, timeout=5):
    raw = await asyncio.wait_for(ws.recv(), timeout)
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')
    return parse_stomp_frame(raw)


async def _session(server):
    import websockets
    from grpcbridge.transport_mux import publish_crude_change
    async with websockets.connect(
            f'ws://127.0.0.1:{PORT}') as ws:
        await ws.send(build_stomp_frame(
            'CONNECT', {'accept-version': '1.2'}))
        command, headers, _ = await _recv_frame(ws)
        check('CONNECT -> CONNECTED over the wire',
              command == 'CONNECTED', command)

        for topic in (f'/topic/{CLASS_NAME}',
                      f'/topic/{CLASS_NAME}/flatJson'):
            await ws.send(build_stomp_frame(
                'SUBSCRIBE', {'id': f'sub-{topic}',
                              'destination': topic}))
        await asyncio.sleep(0.3)  # let SUBSCRIBE frames register

        loop = asyncio.get_running_loop()
        # Knob honesty first: a DISABLED class publishes nothing;
        # the ENABLED publish that follows must be the first frame
        # received (ordering proves the silent drop — no sleeps).
        await loop.run_in_executor(
            None, publish_crude_change,
            _manager(polari_tree_ws=False), CLASS_NAME, 'update',
            ['silent-1'])
        await loop.run_in_executor(
            None, publish_crude_change,
            _manager(polari_tree_ws=True), CLASS_NAME, 'create',
            ['loud-1'])
        command, headers, body = await _recv_frame(ws)
        payload = json.loads(body or '{}')
        check('MESSAGE frame delivered on /topic/<Class>',
              command == 'MESSAGE'
              and headers.get('destination')
              == f'/topic/{CLASS_NAME}')
        check('disabled-knob publish was silently dropped '
              '(enabled one arrived first)',
              payload.get('instanceIds') == ['loud-1'],
              str(payload.get('instanceIds')))
        check('notification payload golden shape',
              payload.get('className') == CLASS_NAME
              and payload.get('operation') == 'create'
              and payload.get('formatType') == 'crude'
              and 'timestamp' in payload)

        await loop.run_in_executor(
            None, publish_crude_change,
            _manager(polari_tree_ws=False, flat_json_ws=True),
            CLASS_NAME, 'update', ['fmt-1'])
        command, headers, body = await _recv_frame(ws)
        payload = json.loads(body or '{}')
        check('format-specific topic delivers with formatType',
              headers.get('destination')
              == f'/topic/{CLASS_NAME}/flatJson'
              and payload.get('formatType') == 'flatJson')

        await ws.send(build_stomp_frame('DISCONNECT', {}))


if __name__ == '__main__':
    server = _start_server()
    check('StompWebSocketServer running on a scratch port',
          server._running, f'port {PORT}')
    if server._running:
        set_stomp_server(server)
        try:
            asyncio.run(_session(server))
        finally:
            set_stomp_server(None)
            server.stop()
    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
