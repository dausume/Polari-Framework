"""
@module voron.custom.provision

Render the POSIX-sh provisioner for the Voron guest (Debian): Klipper +
Moonraker + Mainsail at PINNED commits, the systemd units, the rendered
printer.cfg and the Voron-standard macros. Pure: `defn` in, (script,
refusals) out — the script is NOT rendered while any upstream pin below is
still '<PIN ME>' (a named refusal), unless `defn['allow_unpinned']` is
True, in which case the script says so in a comment and clones the
default branch HEAD (development renders only).

`defn` is the HardwareAppDefinition-shaped dict of the guest PLUS two keys
the API adds: 'printer' (the PrinterDefinition-shaped dict / row) and
'boards' (its PrinterBoard rows / dicts). The printer.cfg is rendered from
those by printer_cfg.render_printer_cfg; its refusals are this
provisioner's refusals too. Mode `sim` additionally builds Klipper's MCU
firmware with the Linux-process target (menuconfig replaced by a written
.config + `make olddefconfig`; `make flash` is NOT run — out/klipper.elf
is copied to /usr/local/bin/klipper_mcu and a klipper-mcu.service is
installed); mode `real` skips that build. Everything runs as user
`printer` under /home/printer (the pi-equivalent). Offline installs: the
script prefers pre-staged copies under $VORON_STAGE (klipper/, moonraker/,
mainsail.zip) and Moonraker's [update_manager] is deliberately absent so
nothing fetches after install.
"""
from voron.custom.printer_cfg import render_printer_cfg, PRINTER_DATA, MACROS_FILE, HOST_MCU_SERIAL

UNPINNED = '<PIN ME>'
KLIPPER = {'repo': 'https://github.com/Klipper3d/klipper', 'commit': UNPINNED, 'licence': 'GPL-3.0'}
MOONRAKER = {'repo': 'https://github.com/Arksine/moonraker', 'commit': UNPINNED, 'licence': 'GPL-3.0'}
MAINSAIL = {'release': 'https://github.com/mainsail-crew/mainsail/releases/download/%s/mainsail.zip' % UNPINNED, 'licence': 'GPL-3.0'}

APT_PACKAGES = ('git python3-venv virtualenv python3-dev libffi-dev build-essential libncurses-dev libusb-dev avrdude gcc-avr '
                'binutils-avr avr-libc stm32flash libnewlib-arm-none-eabi gcc-arm-none-eabi binutils-arm-none-eabi libusb-1.0-0 '
                'pkg-config dfu-util nginx curl unzip libopenjp2-7 libsodium-dev zlib1g-dev libjpeg-dev liblmdb-dev')
HOME = '/home/printer'
TRUSTED_CLIENTS = ('10.0.0.0/8', '192.168.0.0/16', '127.0.0.1')


def _g(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _pins_missing():
    out = []
    if KLIPPER['commit'] == UNPINNED:
        out.append('KLIPPER commit')
    if MOONRAKER['commit'] == UNPINNED:
        out.append('MOONRAKER commit')
    if UNPINNED in MAINSAIL['release']:
        out.append('MAINSAIL release')
    return out


def _macros(model):
    level = {'voron-2.4': '    QUAD_GANTRY_LEVEL', 'voron-trident': '    Z_TILT_ADJUST'}.get(model, '    # single-Z model: no gantry/bed leveling step')
    return '\n'.join([
        '# macros-voron-standard.cfg — rendered by voron.custom.provision (profile voron-standard, model %s)' % model,
        '# In sim mode heater/leveling commands echo "Unknown command" (no heaters, no gantry); the flow still runs.', '',
        '[gcode_macro G32]', 'gcode:', '    SAVE_GCODE_STATE NAME=STATE_G32', '    G90', '    G28', level, '    G28',
        '    RESTORE_GCODE_STATE NAME=STATE_G32', '',
        '[gcode_macro PRINT_START]', '#   slicer start G-code: PRINT_START BED=[bed_temperature] EXTRUDER=[temperature]', 'gcode:',
        '    {% set BED = params.BED|default(0)|float %}', '    {% set EXTRUDER = params.EXTRUDER|default(0)|float %}',
        '    M140 S{BED}', '    M104 S{EXTRUDER}', '    G32', '    M190 S{BED}', '    M109 S{EXTRUDER}', '    G90', '    G1 Z10 F3000', '',
        '[gcode_macro PRINT_END]', 'gcode:', '    M400', '    G92 E0', '    G1 E-5.0 F1800', '    TURN_OFF_HEATERS', '    G91',
        '    G0 Z2 F3600', '    G90', '    M107', '    M84', '',
        '[gcode_macro PAUSE]', 'rename_existing: BASE_PAUSE', 'gcode:', '    {% set z = params.Z|default(10)|int %}',
        "    {% if printer['pause_resume'].is_paused|int == 0 %}", '        SET_GCODE_VARIABLE MACRO=RESUME VARIABLE=zhop VALUE={z}',
        '        SAVE_GCODE_STATE NAME=PAUSE', '        BASE_PAUSE', '        G91', '        G1 Z{z} F900', '        G90', '    {% endif %}', '',
        '[gcode_macro RESUME]', 'rename_existing: BASE_RESUME', 'variable_zhop: 0', 'gcode:',
        "    {% if printer['pause_resume'].is_paused|int == 1 %}", '        G91', '        G1 Z{zhop * -1} F900', '        G90',
        '        RESTORE_GCODE_STATE NAME=PAUSE MOVE=1 MOVE_SPEED=100', '        BASE_RESUME', '    {% endif %}', '',
        '[gcode_macro CANCEL_PRINT]', 'rename_existing: BASE_CANCEL_PRINT', 'gcode:', '    CLEAR_PAUSE', '    SDCARD_RESET_FILE',
        '    PRINT_END', '    BASE_CANCEL_PRINT', ''])


def _moonraker_conf():
    return '\n'.join(['# moonraker.conf — rendered by voron.custom.provision', '[server]', 'host: 0.0.0.0', 'port: 7125',
                      'klippy_uds_address: %s/comms/klippy.sock' % PRINTER_DATA, '', '[authorization]', 'trusted_clients:']
                     + ['    %s' % c for c in TRUSTED_CLIENTS]
                     + ['cors_domains:', '    *://*', '', '[file_manager]', '', '[history]', '', '[octoprint_compat]', '',
                        '# [update_manager] is deliberately absent: offline installs must not fetch; upgrades are a new render at new pins.', ''])


def _nginx_site():
    proxy = ['        proxy_pass http://apiserver%s;', '        proxy_http_version 1.1;', '        proxy_set_header Host $http_host;',
             '        proxy_set_header X-Real-IP $remote_addr;', '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;',
             '        proxy_set_header X-Scheme $scheme;']
    return '\n'.join(['# mainsail — rendered by voron.custom.provision', 'upstream apiserver { ip_hash; server 127.0.0.1:7125; }', 'server {',
                      '    listen 80 default_server;', '    listen [::]:80 default_server;', '    root /var/www/mainsail;', '    index index.html;',
                      '    client_max_body_size 0;', '    location / { try_files $uri $uri/ /index.html; }', '    location /websocket {']
                     + [p % '/websocket' if '%s' in p else p for p in proxy]
                     + ['        proxy_set_header Upgrade $http_upgrade;', '        proxy_set_header Connection "upgrade";', '        proxy_read_timeout 86400;',
                        '    }', '    location ~ ^/(printer|api|access|machine|server)/ {']
                     + [p % '$request_uri' if '%s' in p else p for p in proxy] + ['    }', '}', ''])


def _unit(desc, exec_start, after, user='printer'):
    return '\n'.join(['[Unit]', 'Description=%s' % desc, 'After=%s' % after, '', '[Service]', 'Type=simple', 'User=%s' % user,
                      'ExecStart=%s' % exec_start, 'Restart=always', 'RestartSec=10', '', '[Install]', 'WantedBy=multi-user.target', ''])


def _heredoc(path, text, mode='0644', owner='printer:printer'):
    return ["cat > '%s' <<'EOF_POLARI'" % path, text.rstrip('\n'), 'EOF_POLARI', "chmod %s '%s'; chown %s '%s'" % (mode, path, owner, path), '']


def _fetch(name, spec, unpinned):
    """git clone at the pinned commit (or the staged copy), idempotent."""
    target = '%s/%s' % (HOME, name)
    lines = ['if [ ! -d "%s/.git" ]; then' % target,
             '  if [ -d "$VORON_STAGE/%s/.git" ]; then git clone "$VORON_STAGE/%s" "%s"; else git clone "%s" "%s"; fi' % (name, name, target, spec['repo'], target),
             'fi']
    if spec['commit'] == UNPINNED:
        lines.append('# UNPINNED (%s): allow_unpinned render — the default branch HEAD, whatever it is today' % name)
    else:
        lines.append('git -C "%s" fetch --quiet origin || true; git -C "%s" checkout --quiet %s' % (target, target, spec['commit']))
    lines.append('chown -R printer:printer "%s"' % target)
    return lines + ['']


def render_provision(defn):
    """defn: HardwareAppDefinition-shaped dict (+ 'printer', 'boards',
    optional 'allow_unpinned'). Returns (script, refusals)."""
    refusals = []
    if (_g(defn, 'guest_kind', '') or '') != 'debian':
        refusals.append("the Voron provisioner targets guest_kind 'debian' (got %r)" % _g(defn, 'guest_kind', ''))
    printer, boards = _g(defn, 'printer'), list(_g(defn, 'boards', []) or [])
    if printer is None:
        refusals.append("defn has no 'printer' (the PrinterDefinition the API attaches)")
    unpinned = bool(_g(defn, 'allow_unpinned', False))
    missing = _pins_missing()
    if missing and not unpinned:
        refusals.append('upstream pin(s) still %s: %s — pin them in voron.custom.provision (or render with allow_unpinned: True for development)'
                        % (UNPINNED, ', '.join(missing)))
    if refusals:
        return '', refusals
    cfg, cfg_refusals = render_printer_cfg(printer, boards)
    if cfg_refusals:
        return '', ['printer.cfg: %s' % r for r in cfg_refusals]
    mode, model = _g(printer, 'mode'), _g(printer, 'model')
    s = ['#!/bin/sh', '# Voron guest provisioner — rendered by voron.custom.provision from HardwareAppDefinition %r' % _g(defn, 'name', ''),
         '# printer %r, model %s, mode %s. Idempotent: re-run after a new render. Runs as root inside the Debian guest.' % (_g(printer, 'name', ''), model, mode),
         '# Upstreams: klipper %s @ %s (%s); moonraker %s @ %s (%s); mainsail %s (%s)' % (
             KLIPPER['repo'], KLIPPER['commit'], KLIPPER['licence'], MOONRAKER['repo'], MOONRAKER['commit'], MOONRAKER['licence'], MAINSAIL['release'], MAINSAIL['licence'])]
    if missing:
        s.append('# WARNING: rendered with allow_unpinned=True while %s are %s — development only, never a release.' % (', '.join(missing), UNPINNED))
    s += ['set -eu', 'export DEBIAN_FRONTEND=noninteractive', 'VORON_STAGE="${VORON_STAGE:-/var/lib/polari/voron-stage}"   # offline: pre-staged klipper/, moonraker/, mainsail.zip', '',
          '# --- user + tree (the pi-equivalent is `printer`)',
          'id printer >/dev/null 2>&1 || useradd -m -s /bin/bash printer', 'usermod -aG dialout,tty printer',
          'install -d -o printer -g printer %s %s/config %s/logs %s/gcodes %s/comms' % ((PRINTER_DATA,) * 5), '',
          '# --- packages', 'apt-get update -qq', 'apt-get install -y -qq --no-install-recommends %s' % APT_PACKAGES, '', '# --- klipper']
    s += _fetch('klipper', KLIPPER, unpinned)
    s += ['[ -x %s/klippy-env/bin/python ] || sudo -u printer virtualenv -p python3 %s/klippy-env' % (HOME, HOME),
          'sudo -u printer %s/klippy-env/bin/pip install -q -r %s/klipper/scripts/klippy-requirements.txt' % (HOME, HOME), '']
    if mode == 'sim':
        s += ['# --- sim mode: Klipper MCU firmware built with the Linux-process target (menuconfig replaced by a written .config;',
              '#     make flash is NOT run — the binary is copied and the unit installed by hand)',
              "printf 'CONFIG_LOW_LEVEL_OPTIONS=y\\nCONFIG_MACH_LINUX=y\\n' > %s/klipper/.config" % HOME,
              'make -C %s/klipper olddefconfig >/dev/null' % HOME, 'make -C %s/klipper -j"$(nproc)"' % HOME,
              'install -m 0755 %s/klipper/out/klipper.elf /usr/local/bin/klipper_mcu' % HOME]
        s += _heredoc('/etc/systemd/system/klipper-mcu.service',
                      _unit('Klipper MCU firmware (Linux process target, sim mode)', '/usr/local/bin/klipper_mcu -I %s' % HOST_MCU_SERIAL, 'local-fs.target', user='root')
                      .replace('[Service]', '[Service]\n# the pty is world-readable by the tty group; klipper runs as printer (in tty)'), owner='root:root')
    else:
        s += ['# --- real mode: no host-MCU build; the boards are passed through (see the [mcu] sections in printer.cfg)', '']
    s += ['# --- printer.cfg + macros'] + _heredoc('%s/config/printer.cfg' % PRINTER_DATA, cfg) + _heredoc('%s/config/%s' % (PRINTER_DATA, MACROS_FILE), _macros(model))
    s += _heredoc('/etc/systemd/system/klipper.service',
                  _unit('Klipper 3D printer firmware', '%s/klippy-env/bin/python %s/klipper/klippy/klippy.py %s/config/printer.cfg -l %s/logs/klippy.log -a %s/comms/klippy.sock'
                        % (HOME, HOME, PRINTER_DATA, PRINTER_DATA, PRINTER_DATA), 'network-online.target' + (' klipper-mcu.service' if mode == 'sim' else '')), owner='root:root')
    s += ['# --- moonraker']
    s += _fetch('moonraker', MOONRAKER, unpinned)
    s += ['[ -x %s/moonraker-env/bin/python ] || sudo -u printer virtualenv -p python3 %s/moonraker-env' % (HOME, HOME),
          'sudo -u printer %s/moonraker-env/bin/pip install -q -r %s/moonraker/scripts/moonraker-requirements.txt' % (HOME, HOME), '']
    s += _heredoc('%s/config/moonraker.conf' % PRINTER_DATA, _moonraker_conf())
    s += _heredoc('/etc/systemd/system/moonraker.service',
                  _unit('Moonraker API server', '%s/moonraker-env/bin/python %s/moonraker/moonraker/moonraker.py -d %s' % (HOME, HOME, PRINTER_DATA), 'network-online.target klipper.service'),
                  owner='root:root')
    s += ['# --- mainsail (static) behind nginx on :80, /websocket + /server (and the other Moonraker prefixes) proxied to :7125',
          'if [ ! -f /var/www/mainsail/.release ] || [ "$(cat /var/www/mainsail/.release)" != "%s" ]; then' % MAINSAIL['release'],
          '  if [ -f "$VORON_STAGE/mainsail.zip" ]; then cp "$VORON_STAGE/mainsail.zip" /tmp/mainsail.zip; else curl -fsSL -o /tmp/mainsail.zip "%s"; fi' % MAINSAIL['release'],
          '  rm -rf /var/www/mainsail && mkdir -p /var/www/mainsail && unzip -q -o /tmp/mainsail.zip -d /var/www/mainsail',
          "  printf '%%s\\n' '%s' > /var/www/mainsail/.release" % MAINSAIL['release'], 'fi', '']
    s += _heredoc('/etc/nginx/sites-available/mainsail', _nginx_site(), owner='root:root')
    s += ['rm -f /etc/nginx/sites-enabled/default', 'ln -sf /etc/nginx/sites-available/mainsail /etc/nginx/sites-enabled/mainsail', 'nginx -t', '',
          '# --- services', 'systemctl daemon-reload',
          'systemctl enable --now %snginx klipper.service moonraker.service' % ('klipper-mcu.service ' if mode == 'sim' else ''),
          'systemctl restart %sklipper.service moonraker.service nginx' % ('klipper-mcu.service ' if mode == 'sim' else ''),
          'echo "voron guest provisioned: mode %s — Mainsail on http://$(hostname -I | cut -d\' \' -f1)/ (Moonraker :7125)"' % mode, '']
    return '\n'.join(s), []


def provision_context(manager, payload):
    """Called by hardwareapps' render for a guest whose `provisioner` is this
    module: the PrinterDefinition whose hardware_app is this guest, and its
    boards, as dicts — so the provisioner renders the real printer.cfg."""
    tables = getattr(manager, 'objectTables', None) or {}
    def rows(cls):
        return list((tables.get(cls, {}) or {}).values())
    def as_dict(r):
        return {k: getattr(r, k) for k in vars(r) if not k.startswith('_') and k != 'manager'}
    printers = [p for p in rows('PrinterDefinition') if getattr(p, 'hardware_app', '') == payload.get('name')]
    if not printers:
        return {}
    printer = printers[0]
    boards = [as_dict(b) for b in rows('PrinterBoard') if getattr(b, 'printer', '') == printer.name]
    return {'printer': as_dict(printer), 'boards': boards}
