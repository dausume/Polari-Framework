"""
moduleService/hardware_reach.py — can this deployment reach the hardware a
module needs?

His rule (2026-09-12): the Polari side of a hardware module (its data model,
pages, simulations) may be installed ANYWHERE — that is useful for development —
but a normal user must be told plainly when it will not actually work here:
hardware kinds need the full isle (the app route: debs, KVM guests with
passthrough, the hardware agent tier) to reach the OS kernel and the devices. A
Docker Swarm deployment can never run that half. So this is a NOTICE, never a
refusal; it travels with the module's health row, the admission response and
the download page.

Route detection: POLARI_DEPLOY_ROUTE (isle | swarm | dev), set by the compose
files (swarm) and the isle's compose (isle); otherwise inferred.
"""
import os

ROUTES = ('isle', 'swarm', 'dev')
HARDWARE_KINDS = ('hardware-app', 'hardware-extension-app')


def deployment_route():
    r = (os.environ.get('POLARI_DEPLOY_ROUTE') or '').strip().lower()
    if r in ROUTES:
        return r
    if os.path.isdir('/etc/isle-mesh') or os.environ.get('POLARI_ISLE_NAME'):
        return 'isle'
    if os.environ.get('DEPLOY_ENV') == 'production' or os.environ.get('POLARI_INSTANCE_ID') == 'public':
        return 'swarm'
    return 'dev'


def hardware_notice(manifest, route=None):
    """'' when the module's hardware half can work here (or it has none);
    otherwise one plain sentence for the user."""
    app = (manifest or {}).get('app') or {}
    sec = (manifest or {}).get('security') or {}
    kind = app.get('kind', '')
    hardware = kind in HARDWARE_KINDS or sec.get('profile') == 'hardware-extension' or bool(sec.get('devices'))
    if not hardware:
        return ''
    route = route or deployment_route()
    tier = app.get('agentTier') or 'hardware'
    if route == 'isle':
        return ''   # the isle decides per device (agent tier, hwmap); nothing to warn about at the Polari level
    what = 'a hardware extension' if kind == 'hardware-extension-app' else 'a hardware app'
    return (f"{what}: only its Polari side (data, pages, simulations) runs here — a "
            f"{'Docker Swarm' if route == 'swarm' else 'development'} deployment cannot reach the OS kernel or devices. "
            f"The hardware half needs a full isle with the '{tier}' agent tier (the app route: installed from the deb, "
            f"with the KVM guest and passthrough the hardware map assigns). Fine for development; not a working device here.")


def hardware_summary(manifest, route=None):
    """{'hardware': bool, 'route': str, 'reach': 'ok'|'polari-side-only'|'none', 'notice': str}"""
    notice = hardware_notice(manifest, route)
    app = (manifest or {}).get('app') or {}
    sec = (manifest or {}).get('security') or {}
    hw = app.get('kind', '') in HARDWARE_KINDS or sec.get('profile') == 'hardware-extension' or bool(sec.get('devices'))
    return {'hardware': hw, 'route': route or deployment_route(),
            'reach': 'none' if not hw else ('polari-side-only' if notice else 'ok'), 'notice': notice}
