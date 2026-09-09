"""
@module printcam.custom.provision

Render the in-guest install for the print camera: ustreamer (Debian
package) as a systemd service on the camera device, Moonraker's [webcam]
entry so Mainsail shows the stream, and Moonraker's timelapse component
(git at a PINNED commit — refuses while unpinned). Applied inside the
voron-printer guest by `isle vm extend voron-printer --with printcam`.
"""
USTREAMER_PKG = 'ustreamer'   # Debian 12 package (GPL-3.0)
TIMELAPSE = {'repo': 'https://github.com/mainsail-crew/moonraker-timelapse', 'commit': '<PIN ME>', 'licence': 'GPL-3.0 (verify at pin time)'}


def provision_context(manager, payload):
    tables = getattr(manager, 'objectTables', None) or {}
    cams = [c for c in (tables.get('CameraDefinition', {}) or {}).values() if getattr(c, 'hardware_app', '') == payload.get('extends', payload.get('name'))]
    if not cams:
        return {}
    c = cams[0]
    return {'camera': {k: getattr(c, k) for k in vars(c) if not k.startswith('_') and k != 'manager'}}


def render_provision(defn):
    cam = defn.get('camera') if isinstance(defn, dict) else None
    refusals = []
    if not cam:
        return '', ['no CameraDefinition names this extension\'s host guest (%s)' % (defn.get('extends') if isinstance(defn, dict) else '?')]
    if not defn.get('passthrough_json') or defn.get('passthrough_json') == '[]':
        refusals.append('no camera port in passthrough_json — pol hwmap candidates --app printcam names one')
    if TIMELAPSE['commit'] == '<PIN ME>' and cam.get('timelapse') and not defn.get('allow_unpinned'):
        refusals.append('moonraker-timelapse commit is <PIN ME> — pin it (licence gate) or render with allow_unpinned')
    if refusals:
        return '', refusals
    dev, w, h, fps, port = cam['device'], cam['width'], cam['height'], cam['fps'], cam['stream_port']
    lines = ['#!/bin/sh', '# printcam — rendered from CameraDefinition %s; idempotent; applied inside the voron guest' % cam['name'], 'set -e',
             'apt-get update && apt-get install -y --no-install-recommends %s' % USTREAMER_PKG,
             'cat > /etc/systemd/system/ustreamer.service <<UNIT', '[Unit]', 'Description=ustreamer print camera', 'After=network.target', '[Service]',
             'ExecStart=/usr/bin/ustreamer --device=%s --resolution=%dx%d --desired-fps=%d --host=0.0.0.0 --port=%d --format=MJPEG' % (dev, w, h, fps, port),
             'Restart=always', 'User=printer', '[Install]', 'WantedBy=multi-user.target', 'UNIT',
             'usermod -aG video printer', 'systemctl daemon-reload && systemctl enable --now ustreamer',
             "MR=/home/printer/printer_data/config/moonraker.conf",
             "grep -q '^\\[webcam %s\\]' \"$MR\" || cat >> \"$MR\" <<CONF" % cam['webcam_name'], '',
             '[webcam %s]' % cam['webcam_name'], 'location: printer', 'service: mjpegstreamer-adaptive', 'stream_url: /webcam/?action=stream',
             'snapshot_url: /webcam/?action=snapshot', 'target_fps: %d' % fps, 'CONF',
             "# nginx: /webcam/ → the streamer (Mainsail's default path)",
             "grep -q 'location /webcam/' /etc/nginx/sites-available/mainsail || sed -i 's#^}$#    location /webcam/ { proxy_pass http://127.0.0.1:%d/; }\n}#' /etc/nginx/sites-available/mainsail" % port,
             'systemctl reload nginx || true']
    if cam.get('timelapse'):
        lines += ['# moonraker-timelapse at the pinned commit (offline: pre-staged clone under $VORON_STAGE when present)',
                  'T=/home/printer/moonraker-timelapse',
                  '[ -d "$T" ] || git clone --quiet %s "$T"' % TIMELAPSE['repo'], 'git -C "$T" checkout --quiet %s' % TIMELAPSE['commit'],
                  'ln -sf "$T/component/timelapse.py" /home/printer/moonraker/moonraker/components/timelapse.py',
                  'ln -sf "$T/klipper_macro/timelapse.cfg" /home/printer/printer_data/config/timelapse.cfg',
                  "grep -q '^\\[timelapse\\]' \"$MR\" || printf '\\n[timelapse]\\noutput_path: ~/printer_data/timelapse/\\nframe_path: /tmp/timelapse/\\n' >> \"$MR\"",
                  "grep -q 'include timelapse.cfg' /home/printer/printer_data/config/printer.cfg || printf '\\n[include timelapse.cfg]\\n' >> /home/printer/printer_data/config/printer.cfg",
                  'systemctl restart moonraker klipper || true']
    lines.append('')
    return '\n'.join(lines), []
