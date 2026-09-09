# Mqttbridge (`mqttbridge`)

MQTT bridge: brokers + topic->object bindings as rows, explicit connect, ingest with refusal ledger; publish knob OFF at mqtt-1. paho-mqtt==2.1.0 (EDL-1.0 edge).

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`MqttBridgeAPI`, `MqttBrokerDefinition`, `MqttMessageRecord`, `MqttTopicBinding`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/mqtt/MqttBrokerDefinition.py`, `objects/mqtt/MqttMessageRecord.py`, `objects/mqtt/MqttTopicBinding.py`, `objects/mqtt/_shared.py`
- **basis** — `mqtt_basis.py`
- **api** — `mqtt_api.py`
- **custom** — `custom/mqtt_bridge.py`
- **selftests** — `mqttbridge_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest mqttbridge        # in the running backend
PYTHONPATH=.:modules python3 -m mqttbridge.mqttbridge_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform mqttbridge`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
