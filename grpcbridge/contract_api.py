"""
@module grpcbridge.contract_api

GrpcContractsAPI: the gRPC-exposure knob surface (grpc-1). Reads show
the catalogue (exposures + stabilized candidates + stale-regenerate
suggestions); the only writes are the explicit knob acts
(enable | disable | regenerate) — nothing auto-enables, and enabling
a non-stabilized class is refused naming the stabilization gate.

Thin falcon shell — all logic lives in grpcbridge.proto_gen so the
selftest exercises it directly.

@consumers
  - polariServer (instantiated next to the other APIs)
  - grpcbridge.selftest_contracts (function-level)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from grpcbridge.proto_gen import (
    exposure_action, exposure_catalogue, exposure_summary,
    get_exposure, get_versions,
)


class GrpcContractsAPI(treeObject):
    """gRPC exposure catalogue + knob endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/grpc/exposures'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/grpc/exposures', self, suffix='catalogue')
            add('/api/grpc/exposures/{class_name}', self,
                suffix='exposure')
            add('/api/grpc/exposures/{class_name}/proto', self,
                suffix='proto')
            add('/api/grpc/exposures/{class_name}/c-header', self,
                suffix='c_header')

    def _payload(self, request):
        try:
            raw = request.bounded_stream.read()
            return (json.loads(raw) if raw else {}), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def on_get_catalogue(self, request, response):
        response.media = exposure_catalogue(self.manager)

    def on_get_exposure(self, request, response, class_name):
        exposure = get_exposure(self.manager, class_name)
        if exposure is None:
            return self._refuse(
                response,
                f'no gRPC exposure for "{class_name}" — enable it '
                'with POST {"action": "enable"} (the class must be '
                'stabilized first)', '404 Not Found')
        media = exposure_summary(exposure)
        media['ok'] = True
        media['versions'] = [{
            'version': getattr(v, 'version', 0),
            'contractHash': getattr(v, 'contract_hash', ''),
            'reason': getattr(v, 'reason', ''),
            'generatedAt': getattr(v, 'generated_at', ''),
        } for v in get_versions(self.manager, class_name)]
        response.media = media

    def on_post_exposure(self, request, response, class_name):
        """Knob act: {action: enable | disable | regenerate}."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        report = exposure_action(self.manager, class_name,
                                 (payload or {}).get('action', ''),
                                 transport=(payload or {})
                                 .get('transport'))
        if not report.get('ok'):
            response.status = '400 Bad Request'
        # rows don't serialize — return summaries only
        report.pop('exposure', None)
        report.pop('versionRow', None)
        response.media = report

    def on_get_c_header(self, request, response, class_name):
        """grpc-j3: the firmware-side C twin of the CURRENT contract,
        generated from the SAME field_map as the .proto and the Java
        codec. Per-class on purpose — firmware only ever downloads
        the classes it needs to know (?msg_type=N matches the class's
        position in its bridge definition, default 1)."""
        exposure = get_exposure(self.manager, class_name)
        if exposure is None or not getattr(exposure, 'proto_version', 0):
            return self._refuse(
                response,
                f'no contract generated for "{class_name}" yet — '
                'enable the exposure first', '404 Not Found')
        wanted = int(getattr(exposure, 'proto_version', 0) or 0)
        field_map = None
        for row in get_versions(self.manager, class_name):
            if int(getattr(row, 'version', 0) or 0) == wanted:
                try:
                    field_map = json.loads(
                        getattr(row, 'field_map_json', '{}') or '{}')
                except Exception:
                    field_map = None
                break
        if not field_map:
            return self._refuse(
                response,
                f'contract v{wanted} ledger row for "{class_name}" '
                'is missing its field map', '404 Not Found')
        try:
            msg_type = int(request.params.get('msg_type', '1'))
        except (TypeError, ValueError):
            msg_type = 1
        from grpcbridge.c_twin import render_c_header
        response.content_type = 'text/plain; charset=utf-8'
        response.text = render_c_header(
            class_name, field_map, msg_type, version=wanted,
            contract_hash=getattr(exposure, 'contract_hash', ''))

    def on_get_proto(self, request, response, class_name):
        """The generated .proto, text/plain (download)."""
        exposure = get_exposure(self.manager, class_name)
        proto_text = getattr(exposure, 'proto_text', '') \
            if exposure is not None else ''
        if not proto_text:
            return self._refuse(
                response,
                f'no contract generated for "{class_name}" yet — '
                'enable the exposure first', '404 Not Found')
        response.content_type = 'text/plain; charset=utf-8'
        response.text = proto_text
