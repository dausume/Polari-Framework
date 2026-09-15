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

#: the LOWEST tier that can run each app kind; `access-app` runs everywhere (it hosts nothing)
MIN_TIER = {
    'access-app': 'access',
    'library': 'member',
    'polari-app': 'member',
    'isle-app': 'member',
    'suite-app': 'member',
    'hardware-app': 'hardware',
    'hardware-extension-app': 'hardware',
}


def norm_tier(tier):
    return TIER_ALIASES.get(tier or '', tier or '')


def install_allowed(app, tier):
    """His rules 2026-09-14 for the INSTALL form on a member of `tier`: access → never (only shells); member (a normal
    isle member) → non-hardware, non-core-exclusive apps; hardware → everything except core-exclusive apps; core →
    everything. A core-exclusive app declares agentTier = core in its manifest."""
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
    return kind not in ('hardware-app', 'hardware-extension-app')   # member


def access_allowed(app, tier):
    """The ACCESS form (a shell) is for every member of every tier — remote-controlling a hardware app from a normal
    member is exactly the point."""
    return True


def tiers_for(kind, app=None):
    """The member tiers that can HOST an app of this kind (an unknown kind is treated as a hosted polari-app); a
    core-exclusive app (agentTier core) is hosted by the core only."""
    if (app or {}).get('agentTier') == 'core':
        return ['core']
    lowest = MIN_TIER.get(kind or 'polari-app', 'member')
    return [t for t in TIERS if TIERS.index(t) >= TIERS.index(lowest)]


def runs_on(kind, tier):
    return norm_tier(tier or 'member') in tiers_for(kind)


def tier_notice(kind, tier):
    """'' when this kind runs on the tier; otherwise one plain sentence (a notice, never a refusal)."""
    tier = norm_tier(tier or 'member')
    if tier not in TIERS:
        return f"unknown tier '{tier}' — the isle CLI reports one of {', '.join(TIERS)}"
    if runs_on(kind, tier):
        return ''
    if tier == 'access':
        return ('this device is ACCESS ONLY: it installs app shells (launchers) and uses the apps the isle hosts, but hosts '
                f"nothing itself. Install the app's shell here; the app ({kind or 'polari-app'}) runs on a host"
                f"{' or hardware' if MIN_TIER.get(kind) == 'hardware' else ''} member.")
    if MIN_TIER.get(kind) == 'hardware':
        return (f"a {kind} needs the HARDWARE tier (KVM/passthrough); this device is a {tier} member — its Polari side can be "
                'staged here, but the hardware half cannot run on this machine.')
    return f'this app exists only on the isle core; a {tier} member reaches it through its shell (the access form).'


def access_form(module, title=''):
    """What the access-only install of an app IS: the launcher deb (built on the core), never the app deb."""
    return {'kind': 'access-app', 'package': f'polari-launcher-{module}', 'builds_with': 'build-launcher-deb.sh',
            'install': f'isle app shell install {module}',
            'reading': f"{title or module}: a launcher that opens the app hosted on the isle — kilobytes, hosts nothing"}
