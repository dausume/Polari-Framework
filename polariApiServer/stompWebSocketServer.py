#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
STOMP-over-WebSocket Server

A lightweight sidecar STOMP server that runs alongside the Falcon WSGI backend.
Publishes change notifications when CRUDE operations modify data, so subscribed
frontends know to refetch.

Implements a minimal STOMP 1.2 subset:
- Client frames: CONNECT, SUBSCRIBE, UNSUBSCRIBE, DISCONNECT
- Server frames: CONNECTED, MESSAGE, ERROR

Topic pattern:
- /topic/{ClassName}              (default = CRUDE / polariTree changes)
- /topic/{ClassName}/{formatType} (specific format changes)

ct-6 (2026-09-19, his ruling 2026-09-18): SUBSCRIBE follows the CRUDE security
posture. Any socket used to be able to subscribe to any class; now a bearer on
the upgrade request or the CONNECT frame becomes the same `user_info` the API
resolves (`accessControl.stomp_identity`), and `accessControl.stomp_gate` asks
the SAME `permission_verdict` the CRUDE gate asks — for verb `read`, because
`events` is derived from it — under the SAME `POLARI_APP_PERMISSIONS` knob.
off = today's behavior; advisory = subscribe AND be told (a MESSAGE notice
frame carrying `X-Polari-Permission-Advisory`, plus that header on the RECEIPT
when one was asked for); enforce = an ERROR frame with the evidence and no
subscription. The gate lives in accessControl so this file stays transport.
"""

import asyncio
import json
import threading
import time
import uuid
from collections import defaultdict

try:
    import websockets
    import websockets.asyncio.server
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


def parse_stomp_frame(data):
    """Parse a raw STOMP frame string into (command, headers_dict, body)."""
    # STOMP frames: COMMAND\nheader1:value1\nheader2:value2\n\nbody\x00
    if '\x00' in data:
        data = data[:data.index('\x00')]
    lines = data.split('\n')
    command = lines[0].strip() if lines else ''
    headers = {}
    body = ''
    header_done = False
    body_lines = []
    for line in lines[1:]:
        if not header_done:
            if line.strip() == '':
                header_done = True
            elif ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
        else:
            body_lines.append(line)
    body = '\n'.join(body_lines)
    return command, headers, body


def build_stomp_frame(command, headers=None, body=''):
    """Build a STOMP frame string from command, headers dict, and body."""
    frame = command + '\n'
    if headers:
        for key, value in headers.items():
            frame += f'{key}:{value}\n'
    frame += '\n'
    frame += body
    frame += '\x00'
    return frame


# Module-level singleton reference — keeps the server out of treeObject __dict__
# so the tree serialization system never encounters it.
_stomp_instance = None


def get_stomp_server():
    """Get the module-level StompWebSocketServer singleton (or None)."""
    return _stomp_instance


def set_stomp_server(server):
    """Set the module-level StompWebSocketServer singleton."""
    global _stomp_instance
    _stomp_instance = server


class StompWebSocketServer:
    """
    Minimal STOMP-over-WebSocket server for push notifications.

    Runs an asyncio event loop in a daemon thread. CRUDE handlers call
    publish() from their own threads; the call is scheduled onto the
    asyncio loop via run_coroutine_threadsafe.
    """

    def __init__(self, port=3001, cors_origins=None, manager=None):
        self.port = port
        self.cors_origins = cors_origins or []
        # ct-6: the manager the subscribe gate resolves verdicts against.
        # A plain attribute reference on a module-level singleton — the STOMP
        # server is deliberately NOT on the tree, so nothing serializes this.
        # None (a sidecar started without one) degrades to today's behavior,
        # stated on the advisory, exactly as a missing profile table does.
        self.manager = manager
        # topic -> set of websocket connections
        self._subscriptions = defaultdict(set)
        # websocket -> set of (topic, subscription_id)
        self._client_subs = defaultdict(set)
        self._loop = None
        self._server = None
        self._running = False
        self._lock = threading.Lock()

    def set_manager(self, manager):
        """Hand the sidecar its manager after construction (lazy boot)."""
        self.manager = manager

    # ---- SUBSCRIBE: the sync half, so it is testable without a socket ----

    def handle_subscribe(self, connection, headers):
        """Gate, register and answer ONE SUBSCRIBE.

        Returns `(allowed, frames, topic)` where `frames` are ready-to-send
        STOMP frame strings; the asyncio handler does nothing but send them.
        Sync and socket-free on purpose: `selftest_stomp_gate.py` drives this
        directly with a fake connection.
        """
        from accessControl.stomp_gate import (class_of_topic, gate_subscribe,
                                              record_subscribe)
        topic = headers.get('destination', '')
        sub_id = headers.get('id', str(uuid.uuid4())[:8])
        receipt = headers.get('receipt', '')
        class_name = class_of_topic(topic)

        decision = gate_subscribe(self.manager, connection, class_name,
                                  receipt=receipt, sub_id=sub_id)
        frames = [build_stomp_frame(f['command'], f['headers'],
                                    f.get('body', ''))
                  for f in decision.get('frames', [])]
        if not decision.get('allowed'):
            return False, frames, topic

        websocket = getattr(connection, 'websocket', None)
        with self._lock:
            self._subscriptions[topic].add(websocket)
            self._client_subs[websocket].add((topic, sub_id))
        record_subscribe(self.manager, connection, class_name)
        return True, frames, topic

    async def _handler(self, websocket):
        """Handle a single WebSocket connection."""
        client_id = str(uuid.uuid4())[:8]
        print(f"[STOMP] Client {client_id} connected from {websocket.remote_address}", flush=True)
        # ct-6: identity before anything else. The upgrade request may already
        # carry the bearer (Authorization, or Sec-WebSocket-Protocol for a
        # browser); a CONNECT frame may carry it instead. Anonymous is a valid
        # answer, not an error — it is gated like an anonymous CRUDE caller.
        from accessControl.stomp_identity import StompConnection, adopt_identity
        connection = StompConnection(websocket=websocket, client_id=client_id)
        adopt_identity(connection)
        try:
            async for raw_message in websocket:
                if isinstance(raw_message, bytes):
                    raw_message = raw_message.decode('utf-8', errors='replace')
                command, headers, body = parse_stomp_frame(raw_message)

                if command == 'CONNECT' or command == 'STOMP':
                    adopt_identity(connection, headers)
                    response = build_stomp_frame('CONNECTED', {
                        'version': '1.2',
                        'server': 'polari-stomp/1.0',
                        'heart-beat': '0,0'
                    })
                    await websocket.send(response)
                    # Log the opaque `sub` and nothing else (D18-1).
                    who = connection.sub or ('auth-failed'
                                             if connection.auth_failed
                                             else 'anonymous')
                    print(f"[STOMP] Client {client_id} connected "
                          f"(STOMP protocol, identity {who})", flush=True)

                elif command == 'SUBSCRIBE':
                    allowed, frames, topic = self.handle_subscribe(
                        connection, headers)
                    for frame in frames:
                        await websocket.send(frame)
                    print(f"[STOMP] Client {client_id} "
                          f"{'subscribed to' if allowed else 'REFUSED'} "
                          f"{topic}", flush=True)

                elif command == 'UNSUBSCRIBE':
                    sub_id = headers.get('id', '')
                    with self._lock:
                        to_remove = []
                        for topic, sid in self._client_subs.get(websocket, set()):
                            if sid == sub_id:
                                to_remove.append((topic, sid))
                        for topic, sid in to_remove:
                            self._client_subs[websocket].discard((topic, sid))
                            self._subscriptions[topic].discard(websocket)
                            if not self._subscriptions[topic]:
                                del self._subscriptions[topic]
                    print(f"[STOMP] Client {client_id} unsubscribed (id={sub_id})", flush=True)

                elif command == 'DISCONNECT':
                    receipt = headers.get('receipt')
                    if receipt:
                        response = build_stomp_frame('RECEIPT', {'receipt-id': receipt})
                        await websocket.send(response)
                    break

                elif command == '':
                    # Heartbeat (empty frame), ignore
                    pass

                else:
                    error_frame = build_stomp_frame('ERROR', {
                        'message': f'Unsupported command: {command}'
                    })
                    await websocket.send(error_frame)

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[STOMP] Client {client_id} error: {e}", flush=True)
        finally:
            # Clean up subscriptions for this client
            with self._lock:
                for topic, sid in self._client_subs.pop(websocket, set()):
                    self._subscriptions[topic].discard(websocket)
                    if not self._subscriptions[topic]:
                        del self._subscriptions[topic]
            print(f"[STOMP] Client {client_id} disconnected", flush=True)

    async def _broadcast(self, topic, body_json):
        """Send a MESSAGE frame to all subscribers of a topic."""
        with self._lock:
            subscribers = set(self._subscriptions.get(topic, set()))
        if not subscribers:
            return 0

        message_id = str(uuid.uuid4())
        frame = build_stomp_frame('MESSAGE', {
            'destination': topic,
            'message-id': message_id,
            'content-type': 'application/json'
        }, body_json)

        sent = 0
        for ws in subscribers:
            try:
                await ws.send(frame)
                sent += 1
            except Exception:
                pass
        return sent

    def publish(self, topic, body_dict):
        """
        Publish a notification to a STOMP topic. Thread-safe.

        Called from CRUDE handler threads. Schedules the broadcast onto
        the asyncio event loop.

        Args:
            topic: STOMP destination string, e.g. '/topic/MyClass'
            body_dict: Dict to serialize as JSON in the MESSAGE body
        """
        if not self._running or not self._loop:
            return

        body_json = json.dumps(body_dict)

        async def _do_broadcast():
            sent = await self._broadcast(topic, body_json)
            if sent > 0:
                op = body_dict.get('operation', '?')
                print(f"[STOMP] Published to {topic}: {op} ({sent} subscriber(s))", flush=True)

        try:
            asyncio.run_coroutine_threadsafe(_do_broadcast(), self._loop)
        except Exception as e:
            print(f"[STOMP] Publish error: {e}", flush=True)

    async def _start_server(self):
        """Start the WebSocket server (runs in asyncio loop)."""
        self._server = await websockets.asyncio.server.serve(
            self._handler,
            "0.0.0.0",
            self.port,
        )
        self._running = True
        print(f"[STOMP] WebSocket server started on port {self.port}", flush=True)
        await self._server.serve_forever()

    def start(self):
        """Start the STOMP server in a daemon thread."""
        if not HAS_WEBSOCKETS:
            print("[STOMP] WARNING: 'websockets' package not installed. STOMP server disabled.", flush=True)
            return

        def _run():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._start_server())
            except Exception as e:
                print(f"[STOMP] Server error: {e}", flush=True)
                self._running = False

        thread = threading.Thread(target=_run, daemon=True, name='stomp-ws-server')
        thread.start()

    def stop(self):
        """Stop the STOMP server."""
        self._running = False
        if self._server:
            self._server.close()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

    def get_status(self):
        """Return server status dict for the /wsStatus endpoint."""
        with self._lock:
            topics = list(self._subscriptions.keys())
            total_subscribers = sum(len(subs) for subs in self._subscriptions.values())
        return {
            "running": self._running,
            "port": self.port,
            "topics": topics,
            "subscribers": total_subscribers
        }
