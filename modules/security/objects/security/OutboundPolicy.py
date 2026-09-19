"""
@module security.objects.security.OutboundPolicy

Row class OutboundPolicy of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class OutboundPolicy(treeObject):
    """WHAT MAY LEAVE THIS INSTANCE, and to which system by which wire (ct-9; design
    CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §5a).

    His ruling (2026-09-18): *"Outbound guard should be tracked in dev as well, and it should be closed by
    default; we should suggest outbound and inbounds based on our monitoring of traffic in and out of polari …
    we just know we cannot track objects outside of polari."*

    ONE row per (system kind, system name, wire) — `name` is exactly `kind|system|means`, so the same send
    seen a thousand times is one row with `count` 1000. The row is a POSTURE row, not a trace row: it is
    DERIVED in dev from what the outbound wrapper (`polariApiServer.outbound`) actually observed, CONFIRMED by
    a person, and ENFORCED in production. Production writes none of these — it carries the confirmed and
    denied ones like any other row and refuses whatever no confirmed row allows (closed by default).

        state = suggested   the monitoring proposed it; NOBODY has ruled. Not a grant: an unconfirmed send is
                            refused under `enforce` exactly as an unknown one is.
              = confirmed   a person said yes. `confirmed_by` is their Keycloak `sub` and nothing else (D18-1);
                            nothing confirms itself.
              = denied      a person said no, on the record, with the same evidence.

    `payload_classes_json` holds the Polari CLASS NAMES observed crossing this edge — never a payload, never a
    field value, never a URL (a URL can carry a key). `derived_from` says which observation proposed the row.
    """

    @treeObjectInit
    def __init__(self, name: str = '', system_kind: str = '', system_name: str = '', means: str = '',
                 payload_classes_json: str = '[]', state: str = 'suggested', derived_from: str = '',
                 confirmed_by: str = '', confirmed_at: str = '', count: int = 0,
                 first_seen: str = '', last_seen: str = ''):
        self.name = name                            # kind|system|means — the dedup key
        self.system_kind = system_kind               # outbound.SYSTEM_KINDS: keycloak, odoo, peer, s3, …
        self.system_name = system_name               # the CONFIGURED name of the system, never a host or a URL
        self.means = means                           # outbound.MEANS: rest, json-rpc, s3, grpc, mqtt, sdk, probe
        self.payload_classes_json = payload_classes_json   # the Polari classes seen crossing — never a payload
        self.state = state                           # suggested | confirmed | denied
        self.derived_from = derived_from             # what proposed it (the dev observation), for accountability
        self.confirmed_by = confirmed_by             # a Keycloak `sub` alone (D18-1); required for confirmed/denied
        self.confirmed_at = confirmed_at
        self.count = count                           # observed sends, counted (this IS the monitoring)
        self.first_seen = first_seen
        self.last_seen = last_seen
