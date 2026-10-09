"""
@module moduleService.tier_reach

Member TIERS and what each may install (his ruling 2026-09-14): a device joins an isle as one of three tiers,
and an app kind either runs on that tier or only has its ACCESS form there.

    access    — "Access only": only app SHELLS are installed (launchers that open an app hosted elsewhere on the
                isle); nothing is hosted, nothing keeps running. No Polari app, no container, no KVM guest.
    host      — also hosts polari-apps and isle-apps (containers) behind an agent.
    hardware  — also hosts hardware-apps / hardware-extension-apps (KVM guests with passthrough).

Every app has an access form — its shell (kind `access-app`: a .desktop + icon + polari-shell.json, built by
polari-app-shell/shells/build-launcher-deb.sh) — so an access-only device can USE every app the isle hosts; it just
cannot host any. Like the hardware notice (hardware_reach.py), this is a NOTICE at the Polari level, never a
refusal: the isle CLI on the device is where an install is refused for the tier.

@consumers
  - appstore.apps_api (per-app `tiers` reading), appstore.app_debs_page (the card sentence)
  - moduleService.selftest_tier_reach
"""

TIERS = ('access', 'member', 'hardware', 'core')
TIER_ALIASES = {'host': 'member', 'light': 'access', 'vlan': 'core', 'remote': 'member'}
TIER_WORDS = {
    'access': 'Access only — uses the isle\'s apps through shells; hosts nothing, nothing keeps running (lightest)',
    'member': 'Isle member — also runs Polari apps and containers for the isle; an agent and Docker stay running',
    'hardware': 'Hardware member — also lets hardware apps use this machine\'s devices (KVM/passthrough); libvirt + the agent; must stay on',
    'core': 'Isle core — hosts everything, including the apps that exist only on the core (the store, security, the isle itself)',
}

#: the LOWEST tier that can run each app kind; `access-app` runs everywhere (it hosts nothing). `hardware-app`'s
#: entry is the DEFAULT (realization unknown or kvm) — see REALIZATION_MIN_TIER/hardware_app_min_tier below for the
#: realization-derived reading D-ucd-2 actually rules.
MIN_TIER = {
    'access-app': 'access',
    'library': 'member',
    'polari-app': 'member',
    'isle-app': 'member',
    'suite-app': 'member',
    'hardware-app': 'hardware',
    'hardware-extension-app': 'hardware',
}

#: D-ucd-2 (ruled 2026-10-07, UNO_CORE_DEMO_PLAN.md §5): a hardware-app's REQUIRED `app.realization` (kvm | bridge)
#: decides what the device actually needs. `kvm` = a QEMU/KVM guest owning hardware by passthrough — needs the
#: HARDWARE tier (libvirt). `bridge` = a JavaFX app on the HOST binding to external hardware over USB/serial (the
#: Polari Firmware Installer is the first) — a bridge app never needs libvirt, so its tier is the one tier_reach
#: already calls "host" in its own words (TIER_WORDS['member']; TIER_ALIASES['host'] == 'member'). TIERS (access |
#: member | hardware | core) is a closed, four-word enum — "host" is not a fifth tier, it is `member`'s own name in
#: this module's prose — so no tier is added here; the realization only CHOOSES between the two tiers that already
#: exist. What a bridge app needs BESIDES a tier (a Hardware Shell App installed, with a PROVEN usb-serial
#: BridgingCapability on the host holding the port) is not a tier at all, so it is never folded into MIN_TIER/TIERS:
#: it is a separate, named requirement (`bridge_requirement` below), the thing `BridgingCapability` rows prove.
REALIZATIONS = ('kvm', 'bridge')
REALIZATION_MIN_TIER = {'kvm': 'hardware', 'bridge': 'member'}


def hardware_app_min_tier(app):
    """The tier a hardware-app ACTUALLY needs, once its `realization` is known (D-ucd-2). An app with no
    realization yet (should not happen once `manifests.validate` refuses one) reads as the old, safer default:
    'hardware' — never a silent downgrade of a requirement nobody declared."""
    return REALIZATION_MIN_TIER.get((app or {}).get('realization'), 'hardware')


def bridge_requirement(app):
    """The NON-TIER requirement a `realization: bridge` hardware-app carries beside its (host/member) tier: a
    Hardware Shell App installed on that member, with a PROVEN usb-serial `BridgingCapability` on the host holding
    the port (D-ucd-2's ruling, verbatim). `None` for a kvm realization, a non-hardware-app kind, or no app given —
    this is a REQUIREMENT a reader checks beside the tier, never a tier substitute."""
    app = app or {}
    if app.get('kind') != 'hardware-app' or app.get('realization') != 'bridge':
        return None
    return {'requirement': 'bridge', 'tier': 'member',
            'needs': 'a Hardware Shell App installed on this member, with a PROVEN usb-serial BridgingCapability on '
                     'the host holding the port',
            'proof_class': 'BridgingCapability'}


def norm_tier(tier):
    return TIER_ALIASES.get(tier or '', tier or '')


def install_allowed(app, tier):
    """His rules 2026-09-14 for the INSTALL form on a member of `tier`: access → never (only shells); member (a normal
    isle member) → non-hardware, non-core-exclusive apps PLUS a `realization: bridge` hardware-app (D-ucd-2: it never
    needs libvirt, so the member tier hosts it); hardware → everything except core-exclusive apps; core → everything.
    A core-exclusive app declares agentTier = core in its manifest."""
    tier = norm_tier(tier)
    kind = (app or {}).get('kind', 'polari-app')
    core_only = (app or {}).get('agentTier') == 'core'
    if tier == 'access':
        return False
    if tier == 'core' or not tier:
        return True
    if core_only:
        return False
    if tier == 'hardware':
        return True
    if kind == 'hardware-extension-app':
        return False   # member: always needs the hardware tier (extends a guest running there)
    if kind == 'hardware-app':
        return (app or {}).get('realization') == 'bridge'   # D-ucd-2: a bridge realization never needs libvirt
    return True   # member


def access_allowed(app, tier):
    """The ACCESS form (a shell) is for every member of every tier — remote-controlling a hardware app from a normal
    member is exactly the point."""
    return True


def tiers_for(kind, app=None):
    """The member tiers that can HOST an app of this kind (an unknown kind is treated as a hosted polari-app); a
    core-exclusive app (agentTier core) is hosted by the core only. A `hardware-app`'s lowest tier DERIVES from its
    `realization` (D-ucd-2: kvm needs hardware, bridge needs only member/"host") rather than the kind's own
    MIN_TIER default."""
    if (app or {}).get('agentTier') == 'core':
        return ['core']
    lowest = hardware_app_min_tier(app) if kind == 'hardware-app' else MIN_TIER.get(kind or 'polari-app', 'member')
    return [t for t in TIERS if TIERS.index(t) >= TIERS.index(lowest)]


def runs_on(kind, tier, app=None):
    return norm_tier(tier or 'member') in tiers_for(kind, app)


def tier_notice(kind, tier, app=None):
    """'' when this kind runs on the tier; otherwise one plain sentence (a notice, never a refusal). `app` is
    optional (callers that only have the kind keep the old, safer-default reading — a hardware-app with no known
    realization reads as needing the hardware tier, per `hardware_app_min_tier`)."""
    tier = norm_tier(tier or 'member')
    if tier not in TIERS:
        return f"unknown tier '{tier}' — the isle CLI reports one of {', '.join(TIERS)}"
    if runs_on(kind, tier, app):
        return ''
    lowest = hardware_app_min_tier(app) if kind == 'hardware-app' else MIN_TIER.get(kind)
    if tier == 'access':
        return ('this device is ACCESS ONLY: it installs app shells (launchers) and uses the apps the isle hosts, but hosts '
                f"nothing itself. Install the app's shell here; the app ({kind or 'polari-app'}) runs on a host"
                f"{' or hardware' if lowest == 'hardware' else ''} member.")
    if lowest == 'hardware':
        return (f"a {kind} needs the HARDWARE tier (KVM/passthrough); this device is a {tier} member — its Polari side can be "
                'staged here, but the hardware half cannot run on this machine.')
    if kind == 'hardware-app' and (app or {}).get('realization') == 'bridge':
        br = bridge_requirement(app)
        return (f"a Hardware Bridge App needs the HOST (member) tier plus {br['needs']} — this device is {tier or 'unset'}; "
                'its Polari side can be staged here, but the bridge half needs a proven BridgingCapability before it holds the port.')
    return f'this app exists only on the isle core; a {tier} member reaches it through its shell (the access form).'


def access_form(module, title=''):
    """What the access-only install of an app IS: the launcher deb (built on the core), never the app deb."""
    return {'kind': 'access-app', 'package': f'polari-launcher-{module}', 'builds_with': 'build-launcher-deb.sh',
            'install': f'isle app shell install {module}',
            'reading': f"{title or module}: a launcher that opens the app hosted on the isle — kilobytes, hosts nothing"}
