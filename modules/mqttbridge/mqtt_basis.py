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
  - mqttbridge.custom.mqtt_bridge (the worker), mqtt_api (knob surface)
  - mqttbridge.mqttbridge_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/mqtt/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mqttbridge.objects.mqtt._shared import MESSAGE_LEDGER_CAP, SEED_MQTT_BINDINGS, SEED_MQTT_BROKERS  # noqa: F401
from mqttbridge.objects.mqtt.MqttBrokerDefinition import MqttBrokerDefinition  # noqa: F401
from mqttbridge.objects.mqtt.MqttTopicBinding import MqttTopicBinding  # noqa: F401
from mqttbridge.objects.mqtt.MqttMessageRecord import MqttMessageRecord  # noqa: F401
