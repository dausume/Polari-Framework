"""@module mqttbridge.objects.mqtt._shared — what the mqtt row classes share (constants, seeds, helpers); split from mqtt_basis.py (sap-2c)."""

MESSAGE_LEDGER_CAP = 200
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
