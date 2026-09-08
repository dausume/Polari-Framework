"""
@module mqttbridge.objects.mqtt.MqttTopicBinding

Row class MqttTopicBinding of the mqttbridge module — one class per file (design §7), split
from mqtt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
