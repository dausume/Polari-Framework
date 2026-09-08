"""
@module computers.computers_ports_basis

cmp-c-6: interconnects as DATA. The composition_view hardcoded
its iface() pairs and the gates knew only ram-slots/slot-budget;
this module turns "what plugs into what" into rows + declared
part specs so the workbench frontend (cmp-c-7) and any new part
kind ride the same machinery without code.

Three layers:
- `InterconnectDefinition` rows — the port/connector VOCABULARY
  (DDR4 DIMM, PCIe x16, M.2 Key-E, USB-A/USB-C ports and the
  internal headers that enable them, ...). A row per matching
  token; adding a connector standard is a row, not code.
- Part declarations — a part's specs_json may declare
  `ports_provided` / `ports_required` as {token: count}. Undeclared
  stays HONESTLY UNVERIFIED — the matrix and gates name what
  declaring would unlock, never guess a count.
- Pure derivations — `interconnect_matrix` (nodes+edges shaped for
  the topology/no-code frontends), `viable_links` (one pair), and
  `port_budget_gates` (provided-vs-required totals per token; the
  generalization of ram-slots/slot-budget to EVERY declared port).

Comms parts land here as taxonomy: kind `comms` (WiFi/BT/cellular
modules, embedded via M.2 Key-E or attached via USB-A/USB-C) and
kind `usb-expansion` (the parts that ENABLE USB attachment at all
— PCIe USB controller cards, hubs, front-panel header adapters).

@consumers
  - computers.custom.computers_gates (port-budget gates in the report)
  - computers.computers_api (/api/computers/interconnects*)
  - computers.computers_selftest
  - polariServer (class registration + seed pass via
    computers_seed.seed_computers)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/computers_ports/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from computers.computers_basis import field_of

from computers.objects.computers_ports._shared import SEED_INTERCONNECTS, SEED_PORT_EXAMPLE_PARTS, SEED_PORT_PART_CLASSES, _example_part, _ic, _specs, interconnect_matrix, part_ports, port_budget_gates, viable_links  # noqa: F401
from computers.objects.computers_ports.InterconnectDefinition import InterconnectDefinition  # noqa: F401
