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

TIERS = ('access', 'host', 'hardware')
TIER_WORDS = {
    'access': 'Access only — uses the isle\'s apps through shells; hosts nothing, nothing keeps running (lightest)',
    'host': 'Host — also runs Polari apps and containers for the isle; an agent and Docker stay running (heavier)',
    'hardware': 'Hardware — also lets hardware apps use this machine\'s devices (KVM/passthrough); libvirt + the agent; must stay on (heaviest)',
}

#: the LOWEST tier that can run each app kind; `access-app` runs everywhere (it hosts nothing)
MIN_TIER = {
    'access-app': 'access',
    'library': 'host',
    'polari-app': 'host',
    'isle-app': 'host',
    'suite-app': 'host',
    'hardware-app': 'hardware',
    'hardware-extension-app': 'hardware',
}


def tiers_for(kind):
    """The member tiers that can HOST an app of this kind (an unknown kind is treated as a hosted polari-app)."""
    lowest = MIN_TIER.get(kind or 'polari-app', 'host')
    return [t for t in TIERS if TIERS.index(t) >= TIERS.index(lowest)]


def runs_on(kind, tier):
    return (tier or 'host') in tiers_for(kind)


def tier_notice(kind, tier):
    """'' when this kind runs on the tier; otherwise one plain sentence (a notice, never a refusal)."""
    tier = tier or 'host'
    if tier not in TIERS:
        return f"unknown tier '{tier}' — the isle CLI reports one of {', '.join(TIERS)}"
    if runs_on(kind, tier):
        return ''
    if tier == 'access':
        return ('this device is ACCESS ONLY: it installs app shells (launchers) and uses the apps the isle hosts, but hosts '
                f"nothing itself. Install the app's shell here; the app ({kind or 'polari-app'}) runs on a host"
                f"{' or hardware' if MIN_TIER.get(kind) == 'hardware' else ''} member.")
    return (f"a {kind} needs the HARDWARE tier (KVM/passthrough); this device is a {tier} member — its Polari side can be "
            'staged here, but the hardware half cannot run on this machine.')


def access_form(module, title=''):
    """What the access-only install of an app IS: the launcher deb (built on the core), never the app deb."""
    return {'kind': 'access-app', 'package': f'polari-launcher-{module}', 'builds_with': 'build-launcher-deb.sh',
            'install': f'isle app shell install {module}',
            'reading': f"{title or module}: a launcher that opens the app hosted on the isle — kilobytes, hosts nothing"}
