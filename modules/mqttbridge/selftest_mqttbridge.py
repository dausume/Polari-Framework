"""
Selftest for mqttbridge (mqtt-1).

Run from polari-framework/:
  PYTHONPATH=. python3 -m mqttbridge.selftest_mqttbridge

Fake manager + injected fake client — the full ingest path runs
without a broker or paho installed; live connection legs belong to
the deployment pass.
"""

import json
import sys
import types

from mqttbridge import mqtt_bridge as mb
from mqttbridge.mqtt_basis import (
    MESSAGE_LEDGER_CAP, SEED_MQTT_BINDINGS, SEED_MQTT_BROKERS,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    return types.SimpleNamespace(objectTables={
        'MqttBrokerDefinition': {}, 'MqttTopicBinding': {},
        'MqttMessageRecord': {}, 'SensorReading': {}}, db=None)


def _insert(mgr, table, **fields):
    row = types.SimpleNamespace(**fields)
    mgr.objectTables[table][id(row)] = row
    return row


class FakeClient:
    def __init__(self):
        self.subscribed = []
        self.published = []
        self.on_message = None
        self.connected_to = None

    def connect(self, host, port):
        self.connected_to = (host, port)

    def subscribe(self, topic, qos=0):
        self.subscribed.append(topic)

    def publish(self, topic, payload):
        self.published.append((topic, payload))

    def loop_start(self):
        pass

    def loop_stop(self):
        pass

    def disconnect(self):
        pass


def main():
    check('topic matching: MQTT wildcards behave (+ one level, '
          '# remainder, exact)',
          mb.topic_matches('a/+/c', 'a/b/c')
          and not mb.topic_matches('a/+/c', 'a/b/d')
          and mb.topic_matches('a/#', 'a/b/c/d')
          and mb.topic_matches('a/b', 'a/b')
          and not mb.topic_matches('a/b/c', 'a/b'))

    mgr = _mgr()
    broker = _insert(mgr, 'MqttBrokerDefinition',
                     **{**SEED_MQTT_BROKERS[0], 'enabled': False,
                        'connected': False, 'last_error': '',
                        'last_seen': '', 'use_tls': False,
                        'username': '', 'password_env': '',
                        'client_id': ''})
    binding = _insert(mgr, 'MqttTopicBinding',
                      name='sensor-ingest',
                      broker='local-broker-example',
                      topic='polari/sensors/+',
                      direction='ingest',
                      target_class='SensorReading',
                      key_field='name',
                      field_map_json=json.dumps(
                          {'temp': 'temperature_c',
                           'hum': 'humidity_pct'}),
                      qos=0, enabled=True, message_count=0,
                      last_message_at='', last_refusal='',
                      notes='')
    sensor = _insert(mgr, 'SensorReading', name='desk-sensor',
                     temperature_c=0.0, humidity_pct=0.0)

    def record_factory(**kw):
        return _insert(mgr, 'MqttMessageRecord', **kw)

    # ingest: applied path
    outcome = mb.ingest_payload(
        mgr, binding, 'polari/sensors/desk',
        json.dumps({'name': 'desk-sensor', 'temp': 21.5,
                    'hum': 40.0, 'ignored': 1}).encode(),
        record_factory=record_factory)
    check('ingest: JSON payload maps onto the target row via the '
          'field map (unmapped keys ignored, never guessed)',
          outcome.startswith('applied')
          and sensor.temperature_c == 21.5
          and sensor.humidity_pct == 40.0
          and not hasattr(sensor, 'ignored'))
    check('ingest: binding stamps count + timestamp; the message '
          'is ledgered with its outcome',
          binding.message_count == 1 and binding.last_message_at
          and len(mgr.objectTables['MqttMessageRecord']) == 1)

    # refusal paths — each named, each ledgered
    refusals = [
        mb.ingest_payload(mgr, binding, 't', b'not json',
                          record_factory=record_factory),
        mb.ingest_payload(mgr, binding, 't',
                          json.dumps({'temp': 1}).encode(),
                          record_factory=record_factory),
        mb.ingest_payload(
            mgr, types.SimpleNamespace(
                name='bad', broker='x', topic='t',
                direction='ingest', target_class='NoSuchClass',
                key_field='name', field_map_json='{"a": "b"}',
                message_count=0, last_message_at='',
                last_refusal=''),
            't', json.dumps({'name': 'x'}).encode(),
            record_factory=record_factory),
    ]
    check('ingest refusals: non-JSON, missing key field, and '
          'unregistered target class each refuse BY NAME and '
          'ledger the reason',
          all(r.startswith('refused') for r in refusals)
          and 'not JSON' in refusals[0]
          and 'key field' in refusals[1]
          and 'not registered' in refusals[2]
          and binding.last_refusal != '')

    # ledger cap
    for i in range(MESSAGE_LEDGER_CAP + 30):
        mb.ingest_payload(mgr, binding, 't', b'not json',
                          record_factory=record_factory)
    check('ledger: capped — oldest pruned beyond '
          f'{MESSAGE_LEDGER_CAP}',
          len(mgr.objectTables['MqttMessageRecord'])
          <= MESSAGE_LEDGER_CAP)

    # connect refusals + fake connect
    worker = mb.BridgeWorker(mgr, broker,
                             client_factory=FakeClient,
                             record_factory=record_factory)
    report = worker.connect()
    check('connect: DISABLED broker refuses (connecting is an '
          'explicit act, never a default)',
          not report['ok'] and 'disabled' in report['refusal'])
    broker.enabled = True
    binding.enabled = False
    report = worker.connect()
    check('connect: no enabled bindings refuses (nothing to '
          'subscribe = say so)',
          not report['ok'] and 'binding' in report['refusal'])
    binding.enabled = True
    report = worker.connect()
    check('connect: fake client connects, subscribes the enabled '
          'binding topics, broker row stamped connected',
          report['ok'] and report['subscribed'] == ['polari/sensors/+']
          and broker.connected is True)

    # dispatch through on_message
    before = binding.message_count
    msg = types.SimpleNamespace(
        topic='polari/sensors/desk',
        payload=json.dumps({'name': 'desk-sensor',
                            'temp': 25.0}).encode())
    worker._on_message(None, None, msg)
    check('dispatch: an arriving message routes to the matching '
          'binding and updates the row',
          binding.message_count == before + 1
          and sensor.temperature_c == 25.0)
    report = worker.disconnect()
    check('disconnect: clean, broker row stamped',
          report['ok'] and broker.connected is False)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
