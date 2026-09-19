"""@module polariapps.objects.apps_security._shared — the vocabulary of a security DECISION (ct-8).

Design: AI-Notes/designs/CAUSAL_TRACE_OBJECT_FLOW_DESIGN.md §6 ("Accountability" + "Coverage accounting", his
rulings 2026-09-18: *"track how many objects have any kind of security coverage and how much if any"* and
*"track security policy decisions of different types and how many have been covered per app, since security
must be worked on at a per-app basis and per each version release"*).

WHY THESE LIVE IN polariapps AND NOT security (the same reasoning §57 wrote down for `RoleAppBinding`): a
decision row is about an APP and a RELEASE — which app version needs a ruling on what, and whether a person
has given it. The security module owns the security CONCEPTS (prototypes, observations, owner policies,
the causal map); this module owns apps, their versions and what an app's release still owes. Everything this
module reads out of security is read through a guarded import, so an instance carrying no security module at
all still enumerates its subjects and still counts its coverage — honestly, saying which source was absent.

THE EIGHT KINDS — one per sort of ruling a release has to have made:

  profile-verb    a class × verb for a group (the `AppPermissionProfile` grant)
  owner-policy    a class opted in to owner-defined permissions, or explicitly not (`OwnedClassPolicy`)
  outbound        a send to a system outside Polari (system:name:wire) — the policy row itself is ct-9
  inbound         a caller from outside (source kind:source) — the policy row itself is ct-9
  trigger-run-as  a trigger, its solution and the authority the solution runs with (`EventTrigger.run_as`)
  flow-declared   a manifest `app.flows` entry (design §9) — or an observed flow nothing declared
  role-binding    a manifest `app.roles` entry, i.e. which roles this app belongs to
  trace-coverage  the class has been a `TraceTarget`, so a closure over it answers something

THE SIX STATES — `open` is the point of the whole row: subjects are enumerated FROM THE APP, never only from
what happened to be observed, so an `open` row is a real gap rather than silence.

  open        the subject exists and nobody has ruled
  suggested   an analysis proposed something, with its evidence
  confirmed   a PERSON confirmed it (a Keycloak `sub` and a proposal hash — nothing confirms itself)
  denied      a PERSON refused it
  inherited   carried forward from the previous app version, subject unchanged
  stale       inherited, but the subject CHANGED in this version — it must be re-ruled before the release
"""

#: design §6 — the sorts of ruling an app version owes
DECISION_KINDS = ('profile-verb', 'owner-policy', 'outbound', 'inbound',
                  'trigger-run-as', 'flow-declared', 'role-binding', 'trace-coverage')

#: design §6 — where a subject stands
DECISION_STATES = ('open', 'suggested', 'confirmed', 'denied', 'inherited', 'stale')

#: the two states only a PERSON may write (his ruling: nothing confirms, enforces or widens itself)
HUMAN_STATES = ('confirmed', 'denied')

#: the states that still owe somebody a ruling — `full` coverage means none of these are left
UNRULED_STATES = ('open', 'stale')

#: how an app version reads as a whole (design §6)
COVERAGE_LEVELS = ('none', 'partial', 'full')


def decision_name(app, app_version, kind, subject):
    """The row id, and therefore the dedup key: `app|app_version|kind|subject` (design §6).

    Converging twice writes one row, and the same subject at two app versions is deliberately two rows — that
    is what makes "a release never ships on last release's rulings for something it changed" checkable."""
    return '|'.join([str(app or ''), str(app_version or ''), str(kind or ''), str(subject or '')])
