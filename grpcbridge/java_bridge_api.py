"""
@module grpcbridge.java_bridge_api

HardwareBridgeAPI: the Polari Hardware Bridge knob surface (grpc-j1).
Reads show every bridge definition + per-class contract readiness;
writes are the explicit acts: create a definition, generate (stamps
the manifest), and the tar.gz download (rebuilt deterministically
from the same contract rows — never stored).

Thin falcon shell — logic lives in grpcbridge.java_bridge.

@consumers
  - polariServer (instantiated next to the other APIs)
  - grpcbridge.selftest_javabridge (function-level)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from grpcbridge.java_bridge import (
    bridge_classes, class_readiness, generate_project, get_bridge,
    stamp_generation, tarball,
)
from grpcbridge.proto_gen import _rows


class HardwareBridgeAPI(treeObject):
    """Bridge-definition catalogue + generate/download endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/grpc/bridges'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/grpc/bridges', self, suffix='bridges')
            add('/api/grpc/bridges/{bridge_name}', self,
                suffix='bridge')
            add('/api/grpc/bridges/{bridge_name}/download', self,
                suffix='download')

    def _payload(self, request):
        try:
            raw = request.bounded_stream.read()
            return (json.loads(raw) if raw else {}), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _refuse(self, response, error, status='400 Bad Request',
                extra=None):
        response.status = status
        media = {'ok': False, 'error': error}
        if extra:
            media.update(extra)
        response.media = media

    def _summary(self, bridge):
        classes = bridge_classes(bridge)
        return {
            'bridgeName': getattr(bridge, 'bridge_name', ''),
            'source': getattr(bridge, 'source', 'simulated'),
            'serialDevice': getattr(bridge, 'serial_device', ''),
            'grpcEnabled': getattr(bridge, 'grpc_enabled', False),
            'grpcTarget': getattr(bridge, 'grpc_target', ''),
            'classes': [class_readiness(self.manager, c)
                        for c in classes],
            'lastGeneratedAt':
                getattr(bridge, 'last_generated_at', ''),
            'contractHashes': json.loads(
                getattr(bridge, 'contract_hashes_json', '{}')
                or '{}'),
        }

    def on_get_bridges(self, request, response):
        bridges = [self._summary(b) for b in
                   _rows(self.manager,
                         'HardwareBridgeDefinition').values()]
        bridges.sort(key=lambda b: b['bridgeName'])
        response.media = {'ok': True, 'bridges': bridges}

    def on_post_bridges(self, request, response):
        """Create a bridge definition: {bridgeName, classes: [...],
        source?, serialDevice?, baud?, simRateHz?, grpcEnabled?,
        grpcTarget?, deviceId?}."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        bridge_name = (payload or {}).get('bridgeName', '').strip()
        classes = (payload or {}).get('classes', [])
        if not bridge_name or not isinstance(classes, list):
            return self._refuse(
                response,
                'bridgeName and classes (ordered list — order '
                'defines msg_type) are required')
        if get_bridge(self.manager, bridge_name) is not None:
            return self._refuse(
                response,
                f'bridge "{bridge_name}" already exists',
                '409 Conflict')
        from grpcbridge.java_bridge_basis import (
            HardwareBridgeDefinition,
        )
        bridge = HardwareBridgeDefinition(
            name=f'{bridge_name}-hw-bridge',
            bridge_name=bridge_name,
            source=(payload.get('source') or 'simulated'),
            serial_device=(payload.get('serialDevice')
                           or '/dev/ttyACM0'),
            baud=int(payload.get('baud') or 115200),
            exposed_classes_json=json.dumps(classes),
            sim_rate_hz=int(payload.get('simRateHz') or 10),
            grpc_enabled=bool(payload.get('grpcEnabled', False)),
            grpc_target=(payload.get('grpcTarget')
                         or 'localhost:3002'),
            device_id=int(payload.get('deviceId') or 1),
            manager=self.manager)
        try:
            self.manager.db.saveInstanceInDB(bridge)
        except Exception:
            pass
        response.media = {'ok': True,
                          'bridge': self._summary(bridge)}

    def on_get_bridge(self, request, response, bridge_name):
        bridge = get_bridge(self.manager, bridge_name)
        if bridge is None:
            return self._refuse(
                response, f'no bridge "{bridge_name}"',
                '404 Not Found')
        media = self._summary(bridge)
        media['ok'] = True
        media['manifest'] = json.loads(
            getattr(bridge, 'manifest_json', '{}') or '[]')
        response.media = media

    def on_post_bridge(self, request, response, bridge_name):
        """Knob acts: {action: generate} | {action: configure, ...}.
        configure flips the run knobs on an existing row — THE
        sim->real transition (source: simulated->serial) and the
        gRPC leg (grpcEnabled/grpcTarget) are one configure away;
        the app is re-downloaded, nothing else changes."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        bridge = get_bridge(self.manager, bridge_name)
        if bridge is None:
            return self._refuse(
                response, f'no bridge "{bridge_name}"',
                '404 Not Found')
        action = (payload or {}).get('action', '')
        if action == 'configure':
            changed = {}
            if 'classes' in payload:
                classes = payload['classes']
                if (not isinstance(classes, list) or not classes
                        or not all(isinstance(c, str)
                                   for c in classes)):
                    return self._refuse(
                        response,
                        'classes must be a non-empty ordered list of '
                        'class names (order defines msg_type)')
                bridge.exposed_classes_json = json.dumps(classes)
                changed['classes'] = classes
            for key, attr, cast in (
                    ('source', 'source', str),
                    ('serialDevice', 'serial_device', str),
                    ('baud', 'baud', int),
                    ('simRateHz', 'sim_rate_hz', int),
                    ('grpcEnabled', 'grpc_enabled', bool),
                    ('grpcTarget', 'grpc_target', str),
                    ('deviceId', 'device_id', int),
                    # measured-run bookkeeping (res-3 idiom: numbers
                    # recorded on the knob row, labels travel)
                    ('notes', 'notes', str)):
                if key in payload:
                    if key == 'source' and payload[key] not in (
                            'simulated', 'serial'):
                        return self._refuse(
                            response,
                            'source must be simulated | serial')
                    setattr(bridge, attr, cast(payload[key]))
                    changed[key] = payload[key]
            try:
                self.manager.db.saveInstanceInDB(bridge)
            except Exception:
                pass
            media = self._summary(bridge)
            media.update({'ok': True, 'changed': changed})
            response.media = media
            return
        if action != 'generate':
            return self._refuse(
                response,
                f'unknown action "{action}" (generate | configure)')
        report = generate_project(self.manager, bridge)
        if not report.get('ok'):
            return self._refuse(response, report['error'],
                                extra={'blocked':
                                       report.get('blocked', [])})
        stamp_generation(self.manager, bridge, report)
        response.media = {'ok': True, 'bridge': bridge_name,
                          'classes': report['classes'],
                          'files': len(report['files']),
                          'manifest': report['manifest']}

    def on_get_download(self, request, response, bridge_name):
        """The generated project as tar.gz (rebuilt on demand)."""
        bridge = get_bridge(self.manager, bridge_name)
        if bridge is None:
            return self._refuse(
                response, f'no bridge "{bridge_name}"',
                '404 Not Found')
        report = generate_project(self.manager, bridge)
        if not report.get('ok'):
            return self._refuse(response, report['error'],
                                extra={'blocked':
                                       report.get('blocked', [])})
        stamp_generation(self.manager, bridge, report)
        response.content_type = 'application/gzip'
        response.downloadable_as = \
            f'polari-hw-bridge-{bridge_name}.tar.gz'
        response.data = tarball(report)
