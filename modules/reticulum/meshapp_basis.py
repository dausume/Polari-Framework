"""
@module reticulum.meshapp_basis

THE APP ACCESS LADDER (ret-1c, plan §5n, DECIDED rows 20/21 — Dustin
2026-08-13): the reserved isle-mesh suffixes, per-app knobs
defaulting to the most restrictive.

  isle   (.isle)  reachable only on its own isle (the default).
  arch   (.arch)  archipelago-accessible: apps inside the .arch talk
                  as their own network. The farmer's market — vendors
                  mesh their isles so customers move between stalls
                  as one.
  mesh   (.mesh)  the ZERO-TRUST wider mesh: beyond the archipelago
                  is water that belongs to no one. Arbitrary
                  consumers connect to a LIGHTHOUSE (MeshAppRelay)
                  that broadcasts the app's current (and optionally
                  prior) state; consumers are pseudonymous — tracked
                  SOLELY by Reticulum identity — and nothing they
                  send mutates state except through the ret-8
                  proposal seam, like everyone else.
  web             the internet, with its various possible endpoints
                  (the EXTERNAL_APPS story) — outermost, distinct
                  from the mesh (the standing local-vs-web split).

An app may hold exposures at SEVERAL levels at once (one row per
level, each its own enable) — "multiple different definition levels"
are rows, not a single field.

Three treeObjects:

  AppArchExposure  the knob row: app ⇄ scope ⇄ which archipelago ⇄
                   OUR ROLE for that app at that level (server /
                   relay-only / user / observer). Enable/disable at
                   will; disabled and isle-scoped are
                   indistinguishable to the outside, which is the
                   point.
  MeshAppRelay     the lighthouse for one app: fans out a
                   WatchedObject's state (§5f verbatim — parent/
                   child versions, keyframes mandatory), cadence
                   adaptively adjusted between bounds, expected user
                   count for the census.
  MeshConsumer     one consumer, named BY its RNS identity hash.
                   kc_subject stays '' unless the consumer opted in
                   under the relay's kc_link_mode — and 'required'
                   DOES NOT EXIST as a mode: a zero-trust tier that
                   demands enrolment is not zero-trust.

Inter-archipelago: each arch holds FULL state (keyframes land at the
arch, so local consumers get wholeness locally); BETWEEN archs only
deltas travel, gRPC/protobuf-encoded (§2/ret-5).
ObjectStateVersion.source_arch_name already keys versions per arch;
the delta algebra is replication_basis's.

@consumers reticulum.reticulum_api, the relay daemon (sidecar,
           ret-5/ret-7)
@see modules/reticulum/replication_basis.py (the state machinery this
     reuses), plan §5n
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/meshapp/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from reticulum.objects.meshapp._shared import APP_SCOPE_VALUES, KC_LINK_MODE_VALUES, MESH_APP_ROLE_VALUES, SEED_KIT_PROFILES, _SCOPE_RANK, adaptive_cadence, scope_allows, user_census  # noqa: F401
from reticulum.objects.meshapp.AppArchExposure import AppArchExposure  # noqa: F401
from reticulum.objects.meshapp.MeshAppRelay import MeshAppRelay  # noqa: F401
from reticulum.objects.meshapp.KitProfile import KitProfile  # noqa: F401
from reticulum.objects.meshapp.MeshConsumer import MeshConsumer  # noqa: F401
