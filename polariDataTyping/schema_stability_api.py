"""
@cross-cutting
@module polariDataTyping.schema_stability_api

SchemaStabilityAPI: the stabilization surface. Reads show every
class's learning state + the recorded OOPS events (with their
captured payloads); the only writes are the manual knobs
(stabilize / destabilize / set-threshold) — automatic stabilization
and destabilization happen inside the save path, StepCostProfile-
freeze style.

@consumers
  - polariServer (instantiated next to the other APIs)
  - polariDataTyping.selftest_schema_stability (handler-level)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from polariDataTyping.schema_stability import (
    field_snapshot, get_profile, set_status_knob,
    stabilization_report,
)


class SchemaStabilityAPI(treeObject):
    """Schema stabilization + deviation-event endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/schema/stability'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/schema/stability', self, suffix='report')
            add('/api/schema/stability/{class_name}', self,
                suffix='profile')
            add('/api/schema/deviations', self, suffix='deviations')

    def _payload(self, request):
        try:
            raw = request.bounded_stream.read()
            return (json.loads(raw) if raw else {}), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def on_get_report(self, request, response):
        response.media = stabilization_report(self.manager)

    def on_get_profile(self, request, response, class_name):
        profile = get_profile(self.manager, class_name)
        if profile is None:
            return self._refuse(
                response,
                f'no stability profile for "{class_name}" yet — it '
                'appears after the first save of that class',
                '404 Not Found')
        response.media = {
            'ok': True,
            'class': class_name,
            'status': getattr(profile, 'status', 'unstable'),
            'cleanSaves': getattr(profile, 'clean_saves', 0),
            'threshold': getattr(profile, 'stabilize_threshold', 0),
            'totalSaves': getattr(profile, 'total_saves', 0),
            'deviations': getattr(profile, 'deviation_count', 0),
            'destabilizations':
                getattr(profile, 'destabilize_count', 0),
            'skippedAnalyses': getattr(profile, 'skipped_analyses', 0),
            'stabilizedAt': getattr(profile, 'stabilized_at', ''),
            'trustedFieldSummary': json.loads(
                getattr(profile, 'field_summary_json', '{}') or '{}'),
            'liveFieldSnapshot': field_snapshot(self.manager,
                                                class_name),
        }

    def on_post_profile(self, request, response, class_name):
        """Manual knob: {action: stabilize|destabilize|set-threshold,
        threshold?}."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        report = set_status_knob(
            self.manager, class_name,
            (payload or {}).get('action', ''),
            threshold=(payload or {}).get('threshold'))
        if not report.get('ok'):
            response.status = '400 Bad Request'
        response.media = report

    def on_get_deviations(self, request, response):
        """Recorded OOPS events, newest first; ?class= filters."""
        wanted = request.params.get('class', '')
        tables = getattr(self.manager, 'objectTables', None) or {}
        rows = []
        for e in (tables.get('SchemaDeviationEvent') or {}).values():
            if wanted and getattr(e, 'subject_class', '') != wanted:
                continue
            rows.append({
                'name': getattr(e, 'name', ''),
                'class': getattr(e, 'subject_class', ''),
                'field': getattr(e, 'field', ''),
                'actualType': getattr(e, 'actual_type', ''),
                'action': getattr(e, 'action', ''),
                'resolved': getattr(e, 'resolved', False),
                'occurredAt': getattr(e, 'occurred_at', ''),
                'dbError': getattr(e, 'db_error', ''),
                'attemptedPayload': json.loads(
                    getattr(e, 'attempted_payload_json', '{}')
                    or '{}'),
            })
        rows.sort(key=lambda r: r['occurredAt'], reverse=True)
        response.media = {'ok': True, 'events': rows,
                          'unresolved': sum(1 for r in rows
                                            if not r['resolved'])}
