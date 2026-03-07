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

    def __init__(self, port=3001, cors_origins=None):
        self.port = port
        self.cors_origins = cors_origins or []
        # topic -> set of websocket connections
        self._subscriptions = defaultdict(set)
        # websocket -> set of (topic, subscription_id)
        self._client_subs = defaultdict(set)
        self._loop = None
        self._server = None
        self._running = False
        self._lock = threading.Lock()

    async def _handler(self, websocket):
        """Handle a single WebSocket connection."""
        client_id = str(uuid.uuid4())[:8]
        print(f"[STOMP] Client {client_id} connected from {websocket.remote_address}", flush=True)
        try:
            async for raw_message in websocket:
                if isinstance(raw_message, bytes):
                    raw_message = raw_message.decode('utf-8', errors='replace')
                command, headers, body = parse_stomp_frame(raw_message)

                if command == 'CONNECT' or command == 'STOMP':
                    response = build_stomp_frame('CONNECTED', {
                        'version': '1.2',
                        'server': 'polari-stomp/1.0',
                        'heart-beat': '0,0'
                    })
                    await websocket.send(response)
                    print(f"[STOMP] Client {client_id} connected (STOMP protocol)", flush=True)

                elif command == 'SUBSCRIBE':
                    topic = headers.get('destination', '')
                    sub_id = headers.get('id', str(uuid.uuid4())[:8])
                    with self._lock:
                        self._subscriptions[topic].add(websocket)
                        self._client_subs[websocket].add((topic, sub_id))
                    print(f"[STOMP] Client {client_id} subscribed to {topic}", flush=True)

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
