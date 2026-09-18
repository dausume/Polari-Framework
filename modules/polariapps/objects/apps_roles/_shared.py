"""@module polariapps.objects.apps_roles._shared — what the apps_roles row classes share.

roles -> apps (his ask 2026-09-18): *"We want to be able to have a primary role and additional roles. We will
want to be able to tie Apps to roles so that the user can see and navigate to the apps they need more easily.
And then the user should be able to refine that further and add apps they want to use or remove ones they do
not care about."*

Two rows carry it:

  RoleAppBinding     role (a Keycloak GROUP name) -> an ORDERED list of app names. Institutional: the same for
                     everyone who holds the role. `source` says who decided it.
  UserAppPreference  one person's refinement of what their roles gave them, keyed by the Keycloak `sub` ALONE
                     (his rule D18-1 — Keycloak exists to keep personal data away from Polari).

BINDING_SOURCES is the whole vocabulary of how a binding came to exist:

  manifest          derived from data the modules themselves declare (a manifest's `app.roles`, or the older
                    `personas` list when the persona name IS the role name). Re-derived on every read, so a
                    manifest edit reaches the live instance without an admin acting.
  admin             an administrator set it through POST /api/apps/roles/{role}. NEVER overwritten by the
                    manifest derivation — a person's decision outranks a derivation (the seed/prior rule).
  prototype-review  a role-play review was accepted into a binding. The review itself only ever SUGGESTS
                    (GET /api/apps/roles/{role}/suggested); nothing binds without an admin's POST.
"""

BINDING_SOURCES = ('manifest', 'admin', 'prototype-review')

#: How a `manifest`-sourced binding was derived — evidence, not a source of authority.
DERIVATIONS = ('app.roles', 'personas', '')

#: Where an app in `/api/apps/mine` came from.
VIA = ('primary', 'additional', 'added')
