"""
@module grpcbridge.custom.bridge_paths

hsp-3a (HARDWARE_SYSTEM_PINS_PLAN.md §7, his notebook draft 2026-10-28: "tying usb and usb-c conversions to userspace, so we define where a bridge is"): the
seeds and the rules of BridgePath + PolariBridgeInstance.

  node_url(name)               -> 'https://api.<name>.isle' - what `isle polari instance deploy --name <name>` registers behind the device's agent
  check_bridge(row, paths)     -> (status, why) - bound | gap; a bridge without a polari_node REFUSES (gap, named); a url that is not the node's isle name is a gap
  hops(path)                   -> the hop rows of a path, a level nobody cited = -1 with what to read
  bench_bridges(bench, rows)   -> {bridges[], paths[], hops[]} for the bench's two views (plain rows; no raw JSON on screens)

Levels are cited or -1 (derive-or-cite-chip-data): the UNO's chip and converter hops take the board's own cited +5V logic level (board.custom.electrical_check,
one board = one logic level); the Elecrow S3's are -1 until its documents are read. The host port is -1 until hwmap scans the device holding the cable.
"""
import json
import re

#: the hop kinds of a path, in order
HOP_KINDS = ('chip-pins', 'converter', 'connector', 'host-port', 'userspace')
MODES = ('serial', 'simulated')
PROTOCOLS = ('uart-text', 'polari-frames', 'scpi')
_NODE = re.compile(r'^[a-z][a-z0-9-]{0,62}$')

HOME_BENCH = 'home-bench'
UNO_PATH = 'home-bench/UNO #1:usb'
S3_PATH = 'home-bench/ESP32-S3 e-paper #1:usb'
UNO_BRIDGE = 'uno-1-bridge'


def node_url(name):
    """The Polari node's API on the isle: `isle polari instance deploy --name <n>` registers <n>.isle + api.<n>.isle behind the device's agent."""
    return 'https://api.%s.isle' % name


def _uno_level():
    try:
        from board.custom.electrical_check import _board_logic_level
        return _board_logic_level('arduino-uno-r3')
    except Exception as e:  # noqa: BLE001 - board absent: the level is not cited here
        return None, 'unread: the board module is not importable (%s)' % e


def _hop(n, kind, what, ref='', level=-1.0, basis=''):
    return {'n': n, 'kind': kind, 'what': what, 'ref': ref, 'signal_level_v': level, 'basis': basis}


def _paths():
    v, why = _uno_level()
    uno_level = v if v is not None else -1.0
    uno = [_hop(1, 'chip-pins', 'PD0 (RXD) / PD1 (TXD) - USART0 of the ATmega328P', 'arduino-uno-r3:PD0,PD1', uno_level, why),
           _hop(2, 'converter', 'ATmega16U2 USB-serial bridge (U2)', 'UsbInterfaceDefinition:atmega16u2-bridge', uno_level,
                'the same board, one logic level (electrical_check rule d): ' + why),
           _hop(3, 'connector', 'USB-B socket on the UNO R3', 'arduino-uno-r3:pinout.usb_bridge', -1.0,
                'named in the notebook draft and the plan; a connector carries no level of its own (USB D+/D- are the 16U2\'s)'),
           _hop(4, 'host-port', 'the USB port of the device holding the cable (pol-core)', 'hwmap', -1.0,
                '-1 until hwmap scans the device: its bus / port / serial join the hardware_id then'),
           _hop(5, 'userspace', 'the Polari Hardware Bridge (generated uno-light bridge) reading /dev/ttyACM*', 'HardwareBridgeDefinition:uno-light', -1.0,
                'protocol polari-frames (the LightState wire contract); in simulated mode the last hop is the twin worker\'s port (hsp-3c)')]
    s3 = [_hop(1, 'chip-pins', 'U0TXD / U0RXD - UART0 of the ESP32-S3', 'elecrow-esp32-eval:U0TXD,U0RXD', -1.0,
               'unread: the ESP32-S3 datasheet\'s VDD_SPI / IO supply section (3.3 V class expected, not cited)'),
          _hop(2, 'converter', 'CH340 USB-serial bridge', 'UsbInterfaceDefinition:ch340-bridge', -1.0,
               'unread: the CH340 datasheet and the board schematic (his note "TTA -> 3.3 V" names the class, not this board)'),
          _hop(3, 'connector', 'USB-C socket on the Elecrow board', 'elecrow-esp32-eval', -1.0, 'named in the plan; not checked against the board\'s documentation'),
          _hop(4, 'host-port', 'the USB port of the device holding the cable (pol-core)', 'hwmap', -1.0, '-1 until hwmap scans the device'),
          _hop(5, 'userspace', 'esptool / a serial reader (no Polari bridge generated for this board yet)', '', -1.0, 'protocol uart-text')]
    return [
        {'name': UNO_PATH, 'bench': HOME_BENCH, 'board': 'arduino-uno-r3', 'label': 'UNO #1', 'hops_json': json.dumps(uno), 'protocol': 'polari-frames', 'mode': 'serial',
         'basis': 'his notebook draft 2026-10-28 (P7/P8 UART -> UART-to-USB -> userspace) on the real UNO R3', 'notes': ''},
        {'name': S3_PATH, 'bench': HOME_BENCH, 'board': 'elecrow-esp32-eval', 'label': 'ESP32-S3 e-paper #1', 'hops_json': json.dumps(s3), 'protocol': 'uart-text',
         'mode': 'serial', 'basis': 'the bench note: read by esptool over its CH340 bridge 2026-10-24', 'notes': ''},
    ]


SEED_BRIDGE_PATHS = _paths()

SEED_POLARI_BRIDGES = [
    {'name': UNO_BRIDGE, 'hardware_id': 'home-bench/UNO #1', 'polari_node': 'polari-pol', 'polari_node_url': node_url('polari-pol'), 'mode': 'serial',
     'path': UNO_PATH, 'bench': HOME_BENCH, 'pins': 'PD0,PD1', 'maps': 'LightState_t->LightState', 'bridge_definition': 'uno-light',
     'status': 'gap', 'status_why': '', 'basis': 'ELECTRONICS_DISTRIBUTION_PLAN D4 (ruled): the bridge + boards stay on pol-core; one Polari instance per device (D3): polari-pol',
     'notes': 'the USB serial joins hardware_id once hwmap scans pol-core'},
]


def check_bridge(row, path_names=None):
    """(status, why) for one PolariBridgeInstance-shaped dict. Refuses (gap) without a polari_node; its url must be that node's isle name; the path must exist;
    `bound` only when all hold (reachability is a live question for the isle, not this check)."""
    node = (row.get('polari_node') or '').strip()
    if not node:
        return 'gap', 'bridge %s names no polari_node: every bridge is bound to one Polari node with a named url on the isle' % row.get('name', '?')
    if not _NODE.match(node):
        return 'gap', 'polari_node %r is not an isle name (lowercase letters, digits, hyphens)' % node
    want = node_url(node)
    if (row.get('polari_node_url') or want) != want:
        return 'gap', 'polari_node_url %r is not %s\'s isle url %s' % (row['polari_node_url'], node, want)
    if (row.get('mode') or 'serial') not in MODES:
        return 'gap', 'mode must be one of %s' % (MODES,)
    if path_names is not None and row.get('path') not in path_names:
        return 'gap', 'path %r is not a BridgePath' % row.get('path')
    if not (row.get('hardware_id') or '').strip():
        return 'gap', 'no hardware_id: name the bench entry (and the USB serial once scanned) or the twin session'
    return 'bound', 'bound to %s at %s over %s (%s)' % (row['hardware_id'], want, row.get('path'), row.get('mode') or 'serial')


def hops(path):
    try:
        return json.loads(path.get('hops_json') or '[]')
    except ValueError:
        return []


def _get(o, k, d=''):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def bench_bridges(bench, bridge_rows=None, path_rows=None):
    """The bench's bridges with their status recomputed, its paths and the flat hop rows. Rows default to the seeds (host tools / selftests)."""
    bridge_rows = SEED_POLARI_BRIDGES if bridge_rows is None else bridge_rows
    path_rows = SEED_BRIDGE_PATHS if path_rows is None else path_rows
    paths = [{k: _get(p, k) for k in ('name', 'bench', 'board', 'label', 'protocol', 'mode', 'basis', 'hops_json')} for p in path_rows if _get(p, 'bench') == bench]
    names = {p['name'] for p in paths}
    bridges = []
    for b in bridge_rows:
        if _get(b, 'bench') != bench:
            continue
        row = {k: _get(b, k) for k in ('name', 'hardware_id', 'polari_node', 'polari_node_url', 'mode', 'path', 'bench', 'pins', 'maps', 'bridge_definition', 'basis', 'notes')}
        row['status'], row['status_why'] = check_bridge(row, names)
        bridges.append(row)
    flat = [dict(h, path=p['name'], board=p['board'], signal_level=('%g V' % h['signal_level_v']) if h['signal_level_v'] >= 0 else '-1')
            for p in paths for h in hops(p)]
    for p in paths:
        p['hops'] = ' -> '.join(h['kind'] for h in hops(p))
        del p['hops_json']
    return {'ok': True, 'bench': bench, 'bridges': bridges, 'paths': paths, 'hops': flat,
            'basis': 'BridgePath + PolariBridgeInstance rows; status recomputed on read (a bridge without a polari_node refuses); levels cited or -1'}
