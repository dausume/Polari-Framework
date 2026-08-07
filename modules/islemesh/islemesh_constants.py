"""
@cross-cutting
@module islemesh.islemesh_constants

Shared vocabulary for the isle-mesh convergence module (mac-1).
Pure constants — NO framework imports (topology_constants
discipline), so parsers and selftests run stdlib-only.

The availability vocabulary is ISLE-MESH'S OWN, imported verbatim
from isle-core:~/Isle-Mesh/docs/AVAILABILITY-MODES.md ("Extended
availability modes": availability = up-trigger × down-trigger ×
placement; named modes are presets over that model). Polari does
not invent policy language here — it adopts isle's, so the two
sides literally share one vocabulary (the convergence rule).

@consumers
  - islemesh.* (basis, parse, api, seed, selftest)
  - polari-cli scripts/isle.sh (sync/mock payload shapes)
"""

#: Ingest payload schema version.
SCHEMA_VERSION = '1'

#: isle AVAILABILITY-MODES up-triggers (why an app comes UP).
UP_TRIGGERS = ('boot', 'access', 'schedule', 'presence', 'manual',
               'resource-permitting')

#: isle AVAILABILITY-MODES down-triggers (why an app goes DOWN).
DOWN_TRIGGERS = ('never', 'idle-timeout', 'schedule-end',
                 'presence-lost', 'manual', 'resource-pressure')

#: isle AVAILABILITY-MODES placement.
PLACEMENTS = ('single-host', 'replicated')

#: The two named preset modes isle ships today (registry field
#: availability_mode); the trigger triple above is the general form.
AVAILABILITY_MODES = ('always-available', 'on-demand')

#: isle registry "modes" — which network scope(s) an app serves.
APP_MODES = ('local', 'isle')

#: How the app's containers are orchestrated. 'compose' is isle's
#: today; 'swarm' arrives with the mac-4 converter upgrade.
ORCHESTRATORS = ('compose', 'swarm')

#: Simultaneous delivery realizations of one mesh-app (handoff §9,
#: §11): a real .deb stub with icon, an app-shell client, the plain
#: .isle website, or a KVM (USB/USB-C hardware passthrough).
REALIZATION_KINDS = ('local-stub', 'shell', 'website', 'kvm')

#: Package kinds the universal .deb story ships (mac-8).
PACKAGE_KINDS = ('', 'app-deb', 'polari-node-deb', 'module-deb')

#: Per-device isle uplink transports (handoff §10).
UPLINK_KINDS = ('ethernet', 'wifi', 'usb-wifi')

#: Per-device connectivity mode (handoff §10 addendum): dual-home
#: (internet + isle, separation enforced) is FIRST-CLASS.
CONNECTIVITY_MODES = ('sole-isle', 'dual-home')

#: Protocol classes the agent's nginx fragments can permit. Derived
#: rows only ever carry these — the protocol matrix renders them.
PERMIT_PROTOCOLS = ('http', 'https', 'https-mtls')

#: Ingest payload kinds accepted by /api/islemesh/ingest/*.
INGEST_KINDS = ('registry', 'fragments', 'device')

#: Device agent roles isle knows (agent.mode on isle-core's create).
AGENT_MODES = ('', 'core', 'remote')

#: The mock banner text the summary surfaces when ANY live row was
#: ingested with mock_network=true. The interface shows it large at
#: the top (Dustin 2026-08-07): real ingests NEVER carry the flag.
MOCK_BANNER = ('MOCK NETWORK — this is a mock isle configuration, '
               'not real mesh data')
