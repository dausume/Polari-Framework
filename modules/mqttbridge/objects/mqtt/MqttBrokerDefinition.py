"""
@module mqttbridge.objects.mqtt.MqttBrokerDefinition

Row class MqttBrokerDefinition of the mqttbridge module — one class per file (design §7), split
from mqtt_basis.py (sap-2c). The class docstring below is the explanation.
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
