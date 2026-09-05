"""
@module mqttbridge.mqtt_basis

MQTT bridge (mqtt-1, Dustin 2026-08-23): a FOUNDATIONAL module
built from our own stack + the MQTT protocol alone — brokers and
topic bindings as rows, ingest into the object tree, publish
behind an explicit knob. Nothing here references or derives from
any third-party gateway project.

Objects (knobs-and-suggestions discipline throughout):
  MqttBrokerDefinition   one broker; enabled=False by DEFAULT —
                         connecting is an explicit act, never a
                         boot side effect.
  MqttTopicBinding       one subscription -> object mapping:
                         payload JSON keys become row fields on
                         target_class, the row keyed by a payload
                         key (key_field). direction 'ingest' now;
                         'publish' bindings exist as rows but the
                         publisher only fires via the explicit
                         test act at mqtt-1 (auto-publish = a
                         later rung, knob stays OFF).
  MqttMessageRecord      a capped recent-messages ledger so what
                         arrived is inspectable data.

Client dependency: paho-mqtt (Eclipse Paho, DUAL EPL-2.0/EDL-1.0;
adopted under the EDL-1.0 = BSD-3-style, GPLv3-compatible; pin
paho-mqtt==2.1.0, licence pins never >=). Absent paho = honest
capability refusal; the module's rows and selftests never need it.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - mqttbridge.mqtt_bridge (the worker), mqtt_api (knob surface)
  - mqttbridge.selftest_mqttbridge
"""

from objectTreeDecorators import treeObject, treeObjectInit


class MqttBrokerDefinition(treeObject):
    """One MQTT broker this instance may talk to. enabled stays
    False until a human flips it — the bridge never dials out on
    boot by default."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        host: str = '',
        port: int = 1883,
        username: str = '',
        # password never lives on the row: name an env var instead
        # (the credentials pattern; empty = anonymous broker).
        password_env: str = '',
        use_tls: bool = False,
        client_id: str = '',
        enabled: bool = False,
        # status stamped by the worker (never hand-set):
        connected: bool = False,
        last_error: str = '',
        last_seen: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password_env = password_env
        self.use_tls = use_tls
        self.client_id = client_id
        self.enabled = enabled
        self.connected = connected
        self.last_error = last_error
        self.last_seen = last_seen
        self.notes = notes


class MqttTopicBinding(treeObject):
    """topic pattern -> object mapping. Ingest: JSON payload keys
    listed in field_map_json become fields on the target row; the
    row is found/created by key_field (a payload key whose value
    is the row name). Non-JSON or unmapped payloads land in the
    message ledger only — never guessed into rows."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        broker: str = '',
        topic: str = '',
        direction: str = 'ingest',
        target_class: str = '',
        key_field: str = 'name',
        # JSON dict payload-key -> row-field ('' = same name).
        field_map_json: str = '{}',
        qos: int = 0,
        enabled: bool = False,
        # status stamped by the worker:
        message_count: int = 0,
        last_message_at: str = '',
        last_refusal: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.broker = broker
        self.topic = topic
        self.direction = direction
        self.target_class = target_class
        self.key_field = key_field
        self.field_map_json = field_map_json
        self.qos = qos
        self.enabled = enabled
        self.message_count = message_count
        self.last_message_at = last_message_at
        self.last_refusal = last_refusal
        self.notes = notes


class MqttMessageRecord(treeObject):
    """One received message (capped ledger — the worker prunes
    beyond MESSAGE_LEDGER_CAP oldest-first)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        broker: str = '',
        topic: str = '',
        binding: str = '',
        payload_preview: str = '',
        outcome: str = '',
        received_at: str = '',
        manager=None,
    ):
        self.name = name
        self.broker = broker
        self.topic = topic
        self.binding = binding
        self.payload_preview = payload_preview
        self.outcome = outcome
        self.received_at = received_at


MESSAGE_LEDGER_CAP = 200

# Seeds: one DISABLED example of each so the CRUDE pages show the
# shape — nothing connects until a human flips enabled.
SEED_MQTT_BROKERS = [
    {'name': 'local-broker-example', 'host': '127.0.0.1',
     'port': 1883, 'enabled': False,
     'notes': 'EXAMPLE row, disabled. Point at a real broker '
              '(e.g. a mosquitto container) and set '
              'enabled=true, then POST {"action": "connect"}.'},
]

SEED_MQTT_BINDINGS = [
    {'name': 'example-sensor-ingest',
     'broker': 'local-broker-example',
     'topic': 'polari/sensors/+', 'direction': 'ingest',
     'target_class': '', 'key_field': 'name',
     'field_map_json': '{}', 'enabled': False,
     'notes': 'EXAMPLE row, disabled: set target_class to a '
              'registered class, field_map_json to '
              '{"payloadKey": "rowField"}, and enable.'},
]
