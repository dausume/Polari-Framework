"""
@module mqttbridge.custom.mqtt_bridge

The bridge worker: connect explicitly, subscribe enabled ingest
bindings, map JSON payloads onto object rows, ledger everything.
Refusal discipline everywhere: no paho -> capability refusal; a
payload that is not JSON, lacks the key field, or names an
unregistered class is LEDGERED with the refusal reason — never
guessed into the tree.

The paho client is injected (client_factory) so selftests exercise
the full mapping path with a fake — the pinned dependency is only
touched at real connect time.

@consumers
  - mqttbridge.mqtt_api ({action: connect|disconnect|test-publish})
  - mqttbridge.mqttbridge_selftest (fake client)
"""

import json
from datetime import datetime, timezone

from mqttbridge.mqtt_basis import MESSAGE_LEDGER_CAP


def _now():
    return datetime.now(timezone.utc).isoformat()


def paho_available():
    try:
        import paho.mqtt.client  # noqa: F401
        return True, ''
    except Exception:
        return False, ('paho-mqtt not installed — pin '
                       'paho-mqtt==2.1.0 (EDL-1.0 edge of the '
                       'dual licence; GPLv3-compatible)')


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return (tables.get(class_name) or {}).values()


def _get(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _save(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass


def topic_matches(pattern, topic):
    """MQTT wildcard match: '+' one level, '#' remainder."""
    p_parts = pattern.split('/')
    t_parts = topic.split('/')
    for i, p in enumerate(p_parts):
        if p == '#':
            return True
        if i >= len(t_parts):
            return False
        if p != '+' and p != t_parts[i]:
            return False
    return len(p_parts) == len(t_parts)


def ingest_payload(manager, binding, topic, payload_bytes,
                   record_factory=None, row_factory=None):
    """One message through one binding. Returns the outcome
    string (also stamped on the binding + ledgered)."""
    outcome = ''
    try:
        payload = json.loads(payload_bytes.decode('utf-8'))
        if not isinstance(payload, dict):
            outcome = 'refused: payload JSON is not an object'
    except Exception:
        outcome = 'refused: payload is not JSON'
    if not outcome:
        key_field = getattr(binding, 'key_field', 'name') or 'name'
        row_name = payload.get(key_field)
        target = getattr(binding, 'target_class', '')
        tables = getattr(manager, 'objectTables', None) or {}
        if not row_name or not isinstance(row_name, str):
            outcome = (f'refused: payload lacks key field '
                       f'"{key_field}"')
        elif target not in tables:
            outcome = (f'refused: target class "{target}" not '
                       'registered on this instance')
        else:
            try:
                field_map = json.loads(
                    getattr(binding, 'field_map_json', '{}')
                    or '{}')
            except Exception:
                field_map = None
            if field_map is None:
                outcome = 'refused: field_map_json is not valid JSON'
            elif not field_map:
                outcome = 'refused: binding maps no fields'
            else:
                row = _get(manager, target, row_name)
                if row is None and row_factory is not None:
                    row = row_factory(target, row_name)
                if row is None:
                    outcome = (f'refused: no row "{row_name}" in '
                               f'{target} and no creator provided')
                else:
                    applied = []
                    for src, dst in field_map.items():
                        if src in payload:
                            setattr(row, dst or src, payload[src])
                            applied.append(dst or src)
                    _save(manager, row)
                    outcome = (f'applied {applied} -> {target}/'
                               f'{row_name}')
    binding.message_count = getattr(binding, 'message_count', 0) + 1
    binding.last_message_at = _now()
    if outcome.startswith('refused'):
        binding.last_refusal = outcome
    _save(manager, binding)
    _ledger(manager, binding, topic, payload_bytes, outcome,
            record_factory)
    return outcome


def _ledger(manager, binding, topic, payload_bytes, outcome,
            record_factory):
    if record_factory is None:
        from mqttbridge.mqtt_basis import MqttMessageRecord
        record_factory = lambda **kw: MqttMessageRecord(  # noqa: E731
            manager=manager, **kw)
    stamp = _now()
    preview = payload_bytes[:200].decode('utf-8', 'replace')
    record_factory(
        name=f'{binding.name}-{stamp[11:23].replace(":", "")}',
        broker=getattr(binding, 'broker', ''), topic=topic,
        binding=binding.name, payload_preview=preview,
        outcome=outcome, received_at=stamp)
    # prune the ledger oldest-first beyond the cap
    tables = getattr(manager, 'objectTables', None) or {}
    table = tables.get('MqttMessageRecord')
    if table and len(table) > MESSAGE_LEDGER_CAP:
        rows = sorted(table.items(),
                      key=lambda kv: getattr(kv[1], 'received_at',
                                             ''))
        for key, _row in rows[:len(table) - MESSAGE_LEDGER_CAP]:
            table.pop(key, None)


class BridgeWorker:
    """One live broker connection + its subscriptions. Constructed
    per connect act; client_factory injectable for tests."""

    def __init__(self, manager, broker, client_factory=None,
                 record_factory=None):
        self.manager = manager
        self.broker = broker
        self.client_factory = client_factory
        self.record_factory = record_factory
        self.client = None

    def bindings(self):
        from mqttbridge.mqtt_basis import MqttTopicBinding  # noqa
        return [b for b in _rows(self.manager, 'MqttTopicBinding')
                if getattr(b, 'broker', '') == self.broker.name
                and getattr(b, 'enabled', False)
                and getattr(b, 'direction', '') == 'ingest']

    def connect(self):
        if not getattr(self.broker, 'enabled', False):
            return {'ok': False,
                    'refusal': f'broker "{self.broker.name}" is '
                               'disabled — enable the row first '
                               '(connecting is an explicit act)'}
        active = self.bindings()
        if not active:
            return {'ok': False,
                    'refusal': 'no enabled ingest bindings for '
                               'this broker — nothing to '
                               'subscribe; enable a binding first'}
        if self.client_factory is None:
            available, why = paho_available()
            if not available:
                return {'ok': False, 'refusal': why}
            import paho.mqtt.client as mqtt
            import os

            def factory():
                client = mqtt.Client(
                    mqtt.CallbackAPIVersion.VERSION2,
                    client_id=self.broker.client_id or None)
                if self.broker.username:
                    client.username_pw_set(
                        self.broker.username,
                        os.environ.get(self.broker.password_env,
                                       None)
                        if self.broker.password_env else None)
                if self.broker.use_tls:
                    client.tls_set()
                return client
            self.client_factory = factory
        try:
            self.client = self.client_factory()
            self.client.on_message = self._on_message
            self.client.connect(self.broker.host,
                                int(self.broker.port))
            for binding in active:
                self.client.subscribe(binding.topic,
                                      qos=int(binding.qos))
            self.client.loop_start()
            self.broker.connected = True
            self.broker.last_error = ''
            self.broker.last_seen = _now()
            _save(self.manager, self.broker)
            return {'ok': True, 'broker': self.broker.name,
                    'subscribed': [b.topic for b in active]}
        except Exception as exc:
            self.broker.connected = False
            self.broker.last_error = str(exc)[:300]
            _save(self.manager, self.broker)
            return {'ok': False,
                    'error': f'connect failed: {exc}'}

    def disconnect(self):
        if self.client is not None:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except Exception:
                pass
        self.broker.connected = False
        _save(self.manager, self.broker)
        return {'ok': True, 'broker': self.broker.name}

    def _on_message(self, _client, _userdata, message):
        self.broker.last_seen = _now()
        for binding in self.bindings():
            if topic_matches(binding.topic, message.topic):
                ingest_payload(self.manager, binding,
                               message.topic, message.payload,
                               record_factory=self.record_factory)


#: live workers by broker name (module-level registry; the API acts
#: own the lifecycle — nothing connects at import or boot).
WORKERS = {}
