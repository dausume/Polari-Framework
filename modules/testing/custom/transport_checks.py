"""
@module testing.custom.transport_checks

acct-2: LIVE transport rows (callable-kind). The in-process
round-trip proofs live in selftest_stomp / selftest_formats /
grpcbridge.serving_selftest — these rows probe the REAL staging
sidecars (both daemon threads inside prf-backend: STOMP :3001,
gRPC :3002):

  stomp-live-connect        real websocket CONNECT -> CONNECTED
                            against the live STOMP sidecar.
  grpc-sidecar-reachability reflection list_services on :3002
                            (ServerReflection always present;
                            polari.sync.* only after a GrpcExposure
                            knob is enabled — count reported as
                            evidence, zero is honest, not red).

  grpc-parity-measurement / grpc-peer-watch
                            REGISTERED here, IMPLEMENTED by grpc-3
                            (GRPC_BRIDGE_PLAN.md PICK UP HERE — one
                            implementation, not two). skip-honest +
                            informational until grpc-3 lands; flip
                            criticality to blocking then.

Declared-vs-undeclared follows the substrate idiom: no prf-backend
container and no env knob -> skip-honest; declared-but-down -> RED.
"""

import asyncio
import os

from testing.custom.substrate_env import (
    classify_absence, container_ip, container_state,
)

BACKEND_CONTAINER = 'prf-backend'
BACKEND_SUGGESTION = (
    'Start staging (suite docker-compose.staging-nip.yml — service '
    'prf-backend runs both sidecars) or set POLARI_STOMP_WS_URL / '
    'POLARI_GRPC_TARGET.')


def _resolve_backend(env_key, port):
    """{host, port, declared, source, container_state} for one of
    prf-backend's sidecar ports, honoring an explicit env URL."""
    endpoint = {'host': None, 'port': port, 'declared': False,
                'source': '', 'container_state': None}
    explicit = (os.environ.get(env_key) or '').strip()
    if explicit:
        stripped = explicit.split('://')[-1].rstrip('/')
        host, _, maybe_port = stripped.partition(':')
        endpoint.update(host=host, declared=True,
                        source=f'env {env_key}')
        if maybe_port.isdigit():
            endpoint['port'] = int(maybe_port)
        return endpoint
    state = container_state(BACKEND_CONTAINER)
    endpoint['container_state'] = state
    if state is not None:
        endpoint['declared'] = True
        endpoint['source'] = (f'container {BACKEND_CONTAINER} '
                              f'({state})')
        if state == 'running':
            endpoint['host'] = container_ip(BACKEND_CONTAINER)
    return endpoint


async def _stomp_connect(host, port, timeout=8):
    import websockets

    from polariApiServer.stompWebSocketServer import (
        build_stomp_frame, parse_stomp_frame,
    )
    async with websockets.connect(f'ws://{host}:{port}',
                                  open_timeout=timeout) as ws:
        await ws.send(build_stomp_frame(
            'CONNECT', {'accept-version': '1.2'}))
        raw = await asyncio.wait_for(ws.recv(), timeout)
        if isinstance(raw, bytes):
            raw = raw.decode('utf-8', errors='replace')
        command, headers, _ = parse_stomp_frame(raw)
        await ws.send(build_stomp_frame('DISCONNECT', {}))
        return command, headers


def check_stomp_live_connect():
    endpoint = _resolve_backend('POLARI_STOMP_WS_URL', 3001)
    absent = classify_absence(endpoint, 'STOMP sidecar',
                              BACKEND_SUGGESTION)
    if absent:
        return absent
    try:
        command, headers = asyncio.run(
            _stomp_connect(endpoint['host'], endpoint['port']))
    except Exception as exc:
        return {'status': 'fail',
                'evidence': f'declared ({endpoint["source"]}) but '
                            f'the STOMP handshake failed: '
                            f'{type(exc).__name__}: {exc}'}
    if command == 'CONNECTED':
        return {'status': 'pass',
                'evidence': 'live CONNECT -> CONNECTED (STOMP '
                            f'{headers.get("version", "?")}) at '
                            f'{endpoint["host"]}:{endpoint["port"]}'}
    return {'status': 'fail',
            'evidence': f'expected CONNECTED, got {command!r}'}


def check_grpc_sidecar_reachability():
    endpoint = _resolve_backend('POLARI_GRPC_TARGET', 3002)
    absent = classify_absence(endpoint, 'gRPC sidecar',
                              BACKEND_SUGGESTION)
    if absent:
        return absent
    try:
        import grpc
        from grpc_reflection.v1alpha import (
            reflection_pb2, reflection_pb2_grpc,
        )
        target = f'{endpoint["host"]}:{endpoint["port"]}'
        with grpc.insecure_channel(target) as channel:
            grpc.channel_ready_future(channel).result(timeout=8)
            stub = reflection_pb2_grpc.ServerReflectionStub(channel)
            responses = stub.ServerReflectionInfo(iter([
                reflection_pb2.ServerReflectionRequest(
                    list_services='')]))
            services = [s.name for s in
                        next(responses).list_services_response.service]
    except Exception as exc:
        return {'status': 'fail',
                'evidence': f'declared ({endpoint["source"]}) but '
                            f'reflection failed: '
                            f'{type(exc).__name__}: {exc}'}
    synced = [s for s in services if s.startswith('polari.sync.')]
    if any('ServerReflection' in s for s in services):
        detail = (', '.join(synced) if synced
                  else 'none — no GrpcExposure knob enabled yet, '
                       'which is the honest default')
        return {'status': 'pass',
                'evidence': f'reflection live at {target}; '
                            f'{len(synced)} polari.sync.* services '
                            f'({detail})'}
    return {'status': 'fail',
            'evidence': f'reflection answered without the '
                        f'reflection service: {services}'}


def _awaiting_grpc3(behavior):
    return {'status': 'skip-honest',
            'evidence': f'{behavior} is implemented by grpc-3 '
                        '(GRPC_BRIDGE_PLAN.md PICK UP HERE) — '
                        'registered here so the debt is visible; '
                        'flip this row to blocking when grpc-3 '
                        'lands.'}


def check_grpc_parity_measurement():
    return _awaiting_grpc3(
        'STOMP<->gRPC parity measurement (bytes + wall time into '
        'GrpcExposure.efficiency_note_json)')


def check_grpc_peer_watch():
    return _awaiting_grpc3(
        'peer-to-peer Watch resolved via the class directory '
        'grpcTarget')
