"""
@module security.objects.security.InboundPolicy

Row class InboundPolicy of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit

#: the source kinds a row may name (design §5a). A raw address is NEVER one of them. A MODULE constant, not a
#: class attribute: the tree's identifier scan walks a treeObject's attributes and logs anything it cannot type
#: as an invalid instance value (the same reason `security_api.HOW_CLOSURE` sits outside its class).
SOURCE_KINDS = ('peer', 'origin', 'anonymous', 'external')


class InboundPolicy(treeObject):
    """WHO MAY CALL THIS INSTANCE, and which doors they were seen at (ct-9; design
    CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §5a).

    The mirror of `OutboundPolicy`, and the same ladder: derived in dev from what the request middleware
    actually saw, confirmed by a person, enforced in production, closed by default.

    ONE row per (source kind, source) — `name` is exactly `source_kind|source`:

        peer        `source` is a `PeerNode` NAME (the peer is recognised by its `X-Polari-Trace` header or by
                    its registered `base_url`), never the address it dialled from
        origin      `source` is the browser Origin as scheme + host ONLY (`https://app.example`) — no path, no
                    query, no port-bearing address of a person. An Origin whose host is an IP LITERAL is
                    recorded as the class `ip-literal`, because Polari does not store a raw address in a row
        anonymous   no Origin, no peer header — a class, not an identity
        external    a CONFIGURED external caller's name (nothing configures one yet; reserved, stated)

    `paths_json` holds the endpoint TEMPLATES this source was seen at (`GET /api/MealEntry/{id}`), capped at 50
    — a template, never a real path, so an instance id can never land here. NEVER a raw IP, never a bearer,
    never a header value.

    `state` is suggested | confirmed | denied exactly as on `OutboundPolicy`; `confirmed_by` is a Keycloak
    `sub` and nothing else (D18-1); nothing confirms itself. ct-8's per-app decision ledger
    (`polariapps.custom.security_subjects.inbound_subjects`) reads these rows as its `inbound` subjects.
    """

    @treeObjectInit
    def __init__(self, name: str = '', source_kind: str = '', source: str = '', paths_json: str = '[]',
                 state: str = 'suggested', derived_from: str = '', confirmed_by: str = '',
                 confirmed_at: str = '', count: int = 0, first_seen: str = '', last_seen: str = ''):
        self.name = name                            # source_kind|source — the dedup key
        self.source_kind = source_kind               # peer | origin | anonymous | external
        self.source = source                         # a PeerNode name, scheme://host, 'anonymous', 'ip-literal'
        self.paths_json = paths_json                 # endpoint TEMPLATES observed, capped at 50
        self.state = state                           # suggested | confirmed | denied
        self.derived_from = derived_from
        self.confirmed_by = confirmed_by             # a Keycloak `sub` alone (D18-1)
        self.confirmed_at = confirmed_at
        self.count = count                           # observed requests, counted (this IS the monitoring)
        self.first_seen = first_seen
        self.last_seen = last_seen
