"""
@module mqttbridge.objects.mqtt.MqttMessageRecord

Row class MqttMessageRecord of the mqttbridge module — one class per file (design §7), split
from mqtt_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
