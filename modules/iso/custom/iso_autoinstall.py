"""
@module iso.custom.iso_autoinstall

The subiquity autoinstall (`user-data`) for one build, from its choices — ISO plan §1b/§2 and D1–D15:
unattended always (D4); role × shape (detect at deploy unless forced); Secure Boot ON by default, off only as a
deliberate choice with its warning (D6); disk encryption OFF by default, refused on a headless shape (D8); ssh from
the first boot with the owner's and the core's keys (D11); the desktop task when the shape allows it (KDE Plasma,
§2b) with the look preset (D13); the platform installed OFFLINE from the ISO's own `polari/debs` and the isle joined
(or become) at first boot with the posture recorded. Nothing asked on the machine.

@consumers
  - iso.custom.iso_builder (writes it into the image), iso.iso_api (preview), iso.iso_selftest
"""
import json

ENCRYPTION_WARNING = ('Disk encryption puts a second password on the machine: it must be typed at every boot before anything '
                      'starts, and a forgotten passphrase means the data is gone for good. Off by default for that reason.')
SECURE_BOOT_OFF_WARNING = ('Secure Boot off means the firmware will boot anything, including a tampered kernel. Ubuntu boots with '
                           'Secure Boot ON; turn it off only for hardware whose drivers cannot be signed, and say why.')
HEADLESS_ENCRYPTION_REFUSAL = ('disk encryption on a headless machine is refused: nobody is there to type the passphrase at boot, '
                               'so the machine would never come up (ISO plan D8)')
DEV_WARNING = ('DEV MODE: any connection to systems that are not your own is EXTREMELY DANGEROUS — the relaxed security travels '
               'with every connection. Keep this machine on your own isle.')

DESKTOP_PACKAGES = ['kubuntu-desktop', 'plasma-workspace', 'sddm', 'konsole', 'dolphin', 'plasma-discover']
BASE_PACKAGES = ['openssh-server', 'curl', 'jq', 'python3', 'ca-certificates']
DESKTOP_EXTRA_PACKAGES = ['zenity', 'policykit-1']   # the store's dialogs and pkexec: only where a desktop can exist
HARDWARE_PACKAGES = ['qemu-kvm', 'libvirt-daemon-system', 'virtinst', 'bridge-utils', 'ovmf']


def validate(build):
    """Named refusals and warnings for a set of choices (dict with the IsoBuild fields). (refusal, warnings)."""
    warnings = []
    if build.get('encryption') and build.get('shape') == 'headless':
        return HEADLESS_ENCRYPTION_REFUSAL, warnings
    if build.get('encryption'):
        warnings.append(ENCRYPTION_WARNING)
    if (build.get('secure_boot') or 'on') == 'off':
        warnings.append(SECURE_BOOT_OFF_WARNING)
    if build.get('posture') == 'dev':
        warnings.append(DEV_WARNING)
    if build.get('role') in ('member', 'hardware', 'access') and not build.get('join_fingerprint'):
        warnings.append('no isle CA fingerprint given: the machine installs Polari but joins nothing until "isle onboard" is run with the core\'s fingerprint')
    if build.get('role') == 'hardware' and build.get('shape') == 'detect':
        warnings.append('hardware role with shape "detect": the hardware tier is installed only where /dev/kvm and IOMMU are detected at deploy')
    return '', warnings


def render(build, ssh_keys=(), core_key='', polari_debs=(), apps=()):
    """The autoinstall YAML (as a dict; the builder dumps it) for one IsoBuild-shaped dict."""
    role = build.get('role') or 'member'; shape = build.get('shape') or 'detect'
    hostname = build.get('hostname') or f"polari-{role}"
    user = build.get('username') or 'polari'
    keys = [k for k in list(ssh_keys) + ([core_key] if core_key else []) if k]
    packages = list(BASE_PACKAGES)
    if shape in ('desktop', 'detect'):
        packages += DESKTOP_EXTRA_PACKAGES + DESKTOP_PACKAGES      # the pool carries the union (§1b); detect installs only what the device needs
    if role in ('core', 'hardware') or shape == 'detect':
        packages += HARDWARE_PACKAGES
    storage = {'layout': {'name': 'lvm'}}
    if build.get('encryption'):
        storage['layout'] = {'name': 'lvm', 'password': build.get('encryption_passphrase') or 'CHANGE-ME-AT-FIRST-BOOT'}
    late = [
        # the platform from the ISO itself, offline (his rule: the offline flavour carries what it needs)
        'curtin in-target --target=/target -- mkdir -p /var/lib/polari-iso',
        'cp -r /cdrom/polari /target/var/lib/polari-iso/',
        'curtin in-target --target=/target -- sh -c "cd /var/lib/polari-iso/polari/debs && apt-get install -y ./polari-complete_*.deb || dpkg -i ./polari-complete_*.deb || true"',
        # posture (his ruling: dev vs production is an install-level mode)
        f'curtin in-target --target=/target -- sh -c "mkdir -p /etc/polari && printf \'%s\' \'{json.dumps({"posture": build.get("posture") or "production", "until": "", "relaxations": [], "applied_by": "iso-build"})}\' > /etc/polari/posture.json"',
        # what this machine IS (the plan lands with the machine; first boot reads it)
        f'curtin in-target --target=/target -- sh -c "printf \'%s\' \'{json.dumps({"role": role, "shape": shape, "join_core": build.get("join_core") or "", "join_fingerprint": build.get("join_fingerprint") or "", "join_tier": build.get("join_tier") or ("hardware" if role == "hardware" else "member" if role == "member" else "access" if role == "access" else ""), "look": build.get("look") or "plasma-default", "apps": list(apps), "report_to": build.get("report_to") or "", "target_hash": build.get("target_hash") or ""})}\' > /etc/polari/plan.json"',
        # first boot: detect (display, kvm, nics, tpm), then become the core or join, then admit the apps carried
        'cp /cdrom/polari/first-boot.sh /target/usr/local/lib/polari/first-boot.sh || (mkdir -p /target/usr/local/lib/polari && cp /cdrom/polari/first-boot.sh /target/usr/local/lib/polari/first-boot.sh)',
        'curtin in-target --target=/target -- chmod 755 /usr/local/lib/polari/first-boot.sh',
        'cp /cdrom/polari/polari-first-boot.service /target/etc/systemd/system/polari-first-boot.service',
        'curtin in-target --target=/target -- systemctl enable polari-first-boot.service',
    ]
    if shape == 'headless':
        late.append('curtin in-target --target=/target -- systemctl set-default multi-user.target')
        late.append('curtin in-target --target=/target -- sh -c "systemctl disable sddm 2>/dev/null || true"')
    early = []
    if shape == 'detect':
        # D8 at deploy: encryption chosen but no display → refuse the install on purpose
        if build.get('encryption'):
            early.append('sh -c "ls /sys/class/drm/card*-*/status >/dev/null 2>&1 || { echo \'REFUSED: disk encryption was chosen and this machine has no display: nobody could type the passphrase at boot (ISO plan D8)\' >&2; exit 1; }"')
    ai = {
        'version': 1,
        'locale': 'en_US.UTF-8',
        'keyboard': {'layout': 'us'},
        'identity': {'hostname': hostname, 'username': user, 'password': build.get('password_hash') or '!'},   # '!' = no password login; ssh keys only (D11)
        'ssh': {'install-server': True, 'allow-pw': False, 'authorized-keys': keys},
        'storage': storage,
        # offline first (ISO plan §1): when no mirror answers, install from the ISO's own pool instead of aborting;
        # a full Polari pool (our packages' apt closure on the ISO) is the next slice
        'apt': {'fallback': 'offline-install', 'preserve_sources_list': False},
        'packages': packages,
        'updates': 'security',
        'early-commands': early,
        'late-commands': late,
        'user-data': {'disable_root': True},
    }
    return {'autoinstall': ai}


def first_boot_script():
    """/usr/local/lib/polari/first-boot.sh — runs once: detect, then become the core or join with the plan, then the apps."""
    return r'''#!/bin/bash
# polari first boot (ISO plan §1b "detect at deploy"): read /etc/polari/plan.json, detect what this machine is,
# become the core or join the isle as planned, admit the apps the ISO carried, report; then disable itself.
set -u
PLAN=/etc/polari/plan.json; LOG=/var/log/polari-first-boot.log; exec >>"$LOG" 2>&1
[ -f "$PLAN" ] || { echo "no plan"; exit 0; }
field(){ python3 -c "import json,sys; print(json.load(open('$PLAN')).get('$1',''))"; }
ROLE=$(field role); SHAPE=$(field shape); CORE=$(field join_core); FP=$(field join_fingerprint); TIER=$(field join_tier)
# ---- detect
DISPLAY_OK=0; ls /sys/class/drm/card*-*/status >/dev/null 2>&1 && DISPLAY_OK=1
KVM_OK=0; [ -e /dev/kvm ] && KVM_OK=1; IOMMU=0; [ -n "$(ls /sys/kernel/iommu_groups 2>/dev/null)" ] && IOMMU=1
NICS=$(ls /sys/class/net | grep -vE '^(lo|docker|br-|veth|virbr)' | wc -l); TPM=0; [ -e /dev/tpm0 ] && TPM=1
python3 - "$DISPLAY_OK" "$KVM_OK" "$IOMMU" "$NICS" "$TPM" <<'PY'
import json, sys
d = dict(zip(('display', 'kvm', 'iommu', 'nics', 'tpm'), [int(x) for x in sys.argv[1:6]]))
json.dump(d, open('/etc/polari/detected.json', 'w'))
PY
# ---- the desktop only where a display exists (unless the shape forced it)
if [ "$SHAPE" = detect ]; then
    if [ "$DISPLAY_OK" = 1 ]; then systemctl set-default graphical.target; systemctl enable sddm 2>/dev/null || true
    else systemctl set-default multi-user.target; systemctl disable sddm 2>/dev/null || true; fi
fi
# ---- the role
ISLE=$(command -v isle || echo /usr/local/bin/isle)
case "$ROLE" in
    core)   ISLE_ASSUME_YES=1 "$ISLE" core-install --skip-security || echo "core-install failed" ;;
    member|hardware|access)
        if [ -n "$FP" ]; then
            SRC="https://${CORE:-apt.isle}/isle-bootstrap.sh"; T=$(mktemp)
            if curl -fsSk "$SRC" -o "$T"; then
                case "$TIER" in access) bash "$T" --fingerprint "$FP" ${CORE:+--core "$CORE"} ;; *) bash "$T" --fingerprint "$FP" ${CORE:+--core "$CORE"} --host ;; esac
            else echo "core unreachable at $SRC — join later: sudo isle onboard"; fi
        fi ;;
    server) echo "server role: run 'pol prod guide' on this machine" ;;
esac
# ---- the apps the ISO carried (offline, presence-checked)
if [ -f /var/lib/polari-iso/polari/apps/install-apps.sh ]; then bash /var/lib/polari-iso/polari/apps/install-apps.sh --no-platform || true; fi
# ---- report back to the core that built this image (his ask 2026-09-15: ssh scaffolding from the core outward)
REPORT=$(field report_to); HASH=$(field target_hash)
if [ -n "$REPORT" ]; then
    ADDRS=$(ip -4 -o addr show scope global | awk '{print $4}' | cut -d/ -f1 | tr '\n' ',' | sed 's/,$//')
    python3 - "$REPORT" "$HASH" "$ROLE" "$SHAPE" "$ADDRS" <<'PY' || echo "report to the core failed (it will be retried by the next boot of the unit if re-enabled)"
import json, socket, ssl, sys, urllib.request
report, h, role, shape, addrs = sys.argv[1:6]
body = json.dumps({'hw_hash': h, 'hostname': socket.gethostname(), 'addresses': [a for a in addrs.split(',') if a], 'role': role, 'shape': shape, 'ssh_user': 'polari',
                   'detected': json.load(open('/etc/polari/detected.json'))}).encode()
req = urllib.request.Request(report.rstrip('/') + '/api/iso/joined', data=body, headers={'Content-Type': 'application/json'}, method='POST')
ctx = ssl._create_unverified_context()   # the core may be self-signed at home; the fingerprint trust is the isle's, not TLS's
with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
    print('reported to the core:', r.read()[:200].decode())
PY
fi
systemctl disable polari-first-boot.service 2>/dev/null || true
echo "first boot done: role=$ROLE shape=$SHAPE display=$DISPLAY_OK kvm=$KVM_OK iommu=$IOMMU nics=$NICS tpm=$TPM"
'''


def first_boot_unit():
    return '''[Unit]
Description=Polari first boot: detect, become the core or join the isle, admit the carried apps
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/lib/polari/first-boot.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
'''
