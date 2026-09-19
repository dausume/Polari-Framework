"""
@module polariapps.objects.apps_security.SecurityDecision

Row class SecurityDecision of the polariapps module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SecurityDecision(treeObject):
    """ONE RULING AN APP VERSION OWES (ct-8; design CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §6).

    His rulings 2026-09-18: *"track how many objects have any kind of security coverage and how much if any"*
    and *"track security policy decisions of different types and how many have been covered per app, since
    security must be worked on at a per-app basis and per each version release"*. So the unit of
    accountability is a DECISION and the unit of coverage is an APP VERSION.

    Subjects are ENUMERATED FROM THE APP (`polariapps.custom.security_decisions.enumerate_subjects`) — every
    class the app carries × five verbs × the groups touching it, every class as an owner-policy candidate,
    every trigger, every declared flow and role, every observed outbound edge, every class as a trace target —
    never only from what happened to be observed. An `open` row is therefore a REAL GAP, not silence.

    NOTHING CONFIRMS ITSELF (his ruling, design §6). A derivation may move a row from `open` to `suggested`
    and may refresh its evidence; only a PERSON writes `confirmed` or `denied`, through
    `POST /api/apps/security/decisions/confirm` or `POST /api/apps/security/confirm-profile`, and the row then
    carries their Keycloak `sub` and the hash of the proposal they saw. A converge pass NEVER overwrites a
    `confirmed` or `denied` row — the same rule `RoleAppBinding` follows for an admin binding.

    THE PII BOUNDARY (his rule D18-1): `confirmed_by` holds an opaque Keycloak `sub` and nothing else — never
    a username, an e-mail or a display name. The name is resolved live at render time through the one gated
    door `POST /api/security/people` (the `person` column format), never stored here.

    A VERSION BUMP (design §6): the previous version's rows carry forward as `inherited`; a subject the new
    version CHANGED becomes `stale` and must be re-ruled, so a release never ships on last release's rulings
    for something it changed. `coverage` for a version reads none / partial / full — full = no `open` and no
    `stale` rows of any kind.
    """

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', app_version: str = '', release: str = '',
                 kind: str = '', subject: str = '', state: str = 'open',
                 evidence_json: str = '{}', derived_from: str = '',
                 confirmed_by: str = '', confirmed_at: str = ''):
        self.name = name                    # the row id and dedup key — `app|app_version|kind|subject`
        self.app = app                      # PolariAppDefinition.name
        self.app_version = app_version      # the app's manifest version (see custom/security_decisions.app_version)
        self.release = release              # the Polari calendar tag it shipped in ('' until one is stamped)
        self.kind = kind                    # _shared.DECISION_KINDS entry
        self.subject = subject              # `Class:verb@group` · `Class` · `system:name:wire` · `trigger:name` · …
        self.state = state                  # _shared.DECISION_STATES entry
        self.evidence_json = evidence_json  # counts, sample trace, the proposal hash — JSON object, never a payload
        self.derived_from = derived_from    # what proposed it: 'AppPermissionProfile:<name>', 'observed', 'inherited:<ver>' …
        #: D18-1: the confirming person's Keycloak `sub` ALONE. Required for `confirmed` and `denied`.
        self.confirmed_by = confirmed_by
        self.confirmed_at = confirmed_at
