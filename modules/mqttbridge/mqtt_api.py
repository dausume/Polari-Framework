"""
@module mqttbridge.mqtt_api

Knob surface: GET /api/mqttbridge (status + capability), POST
/api/mqttbridge/brokers/{name} {action: connect | disconnect |
test-publish}. Rows are edited over CRUDE; the acts here only
manage live connections — explicitly, never at boot.

@consumers
  - polariServer (route registration, gated on feature presence)
  - mqttbridge.selftest_mqttbridge (function level)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from mqttbridge.mqtt_bridge import (
    WORKERS, BridgeWorker, paho_available,
)


class MqttBridgeAPI(treeObject):

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/mqttbridge'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/mqttbridge', self, suffix='status')
            add('/api/mqttbridge/brokers/{name}', self,
                suffix='broker')

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def _broker(self, name):
        tables = getattr(self.manager, 'objectTables', None) or {}
        for row in (tables.get('MqttBrokerDefinition')
                    or {}).values():
            if getattr(row, 'name', '') == name:
                return row
        return None

    def on_get_status(self, request, response):
        available, why = paho_available()
        tables = getattr(self.manager, 'objectTables', None) or {}
        brokers = [{
            'name': getattr(b, 'name', ''),
            'host': getattr(b, 'host', ''),
            'enabled': getattr(b, 'enabled', False),
            'connected': getattr(b, 'connected', False),
            'lastError': getattr(b, 'last_error', ''),
            'lastSeen': getattr(b, 'last_seen', ''),
        } for b in (tables.get('MqttBrokerDefinition')
                    or {}).values()]
        bindings = [{
            'name': getattr(b, 'name', ''),
            'broker': getattr(b, 'broker', ''),
            'topic': getattr(b, 'topic', ''),
            'direction': getattr(b, 'direction', ''),
            'enabled': getattr(b, 'enabled', False),
            'messageCount': getattr(b, 'message_count', 0),
            'lastRefusal': getattr(b, 'last_refusal', ''),
        } for b in (tables.get('MqttTopicBinding') or {}).values()]
        response.media = {
            'ok': True,
            'capability': {'paho': available,
                           'refusal': '' if available else why,
                           'autoPublish': 'OFF — mqtt-1 publishes '
                                          'only via the explicit '
                                          'test act'},
            'brokers': brokers, 'bindings': bindings}

    def on_post_broker(self, request, response, name):
        try:
            raw = request.bounded_stream.read()
            payload = json.loads(raw) if raw else {}
        except Exception as e:
            return self._refuse(response, f'bad JSON payload: {e}')
        broker = self._broker(name)
        if broker is None:
            return self._refuse(response, f'no broker "{name}"',
                                '404 Not Found')
        action = payload.get('action', '')
        if action == 'connect':
            worker = WORKERS.get(name) or BridgeWorker(
                self.manager, broker)
            report = worker.connect()
            if report.get('ok'):
                WORKERS[name] = worker
            else:
                response.status = ('503 Service Unavailable'
                                   if 'refusal' in report
                                   else '422 Unprocessable Entity')
            response.media = report
            return
        if action == 'disconnect':
            worker = WORKERS.pop(name, None)
            if worker is None:
                return self._refuse(response,
                                    'not connected', '409 Conflict')
            response.media = worker.disconnect()
            return
        if action == 'test-publish':
            worker = WORKERS.get(name)
            if worker is None or worker.client is None:
                return self._refuse(
                    response, 'not connected — POST '
                    '{"action": "connect"} first',
                    '409 Conflict')
            topic = payload.get('topic', '')
            body = payload.get('payload', '')
            if not topic:
                return self._refuse(response, 'topic required')
            worker.client.publish(topic,
                                  json.dumps(body)
                                  if isinstance(body, (dict, list))
                                  else str(body))
            response.media = {'ok': True, 'published': topic,
                              'note': 'explicit test publish — '
                                      'auto-publish stays OFF at '
                                      'mqtt-1'}
            return
        return self._refuse(
            response, f'unknown action "{action}" (connect | '
                      'disconnect | test-publish)')
