"""@module computers.objects.computers_ports._shared — what the computers_ports row classes share (constants, seeds, helpers); split from computers_ports_basis.py (sap-2c)."""
from computers.computers_basis import field_of
import json

def _specs(part):
    raw = field_of(part, 'specs_json', '{}') or '{}'
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}
def part_ports(part):
    """A part's declared port counts. `declared` is False when the
    part declares NEITHER side — the caller must stay honest about
    it rather than treating {} as 'has no ports'."""
    specs = _specs(part)
    provided = {k: int(v) for k, v in
                (specs.get('ports_provided') or {}).items()}
    required = {k: int(v) for k, v in
                (specs.get('ports_required') or {}).items()}
    return {'provided': provided, 'required': required,
            'declared': bool(provided or required)}
def viable_links(part_a, part_b):
    """Every token one part provides and the other requires, both
    directions. Empty when nothing matches; None-shaped honesty is
    the caller's job via part_ports()['declared']."""
    a, b = part_ports(part_a), part_ports(part_b)
    links = []
    for src, dst, sp, dp in ((part_a, part_b, a, b),
                             (part_b, part_a, b, a)):
        for token, need in sorted(dp['required'].items()):
            have = sp['provided'].get(token, 0)
            if have > 0:
                links.append({
                    'interconnect': token,
                    'from': field_of(src, 'name'),
                    'to': field_of(dst, 'name'),
                    'provided': have,
                    'required': need,
                })
    return links
def interconnect_matrix(parts, interconnects_by_name=None):
    """The parts as nodes + every viable link as a typed edge —
    the data feed for the visual workbench (topology-graph /
    no-code slot-connector shaped). Undeclared parts are LISTED,
    not guessed; tokens missing from the vocabulary are flagged."""
    interconnects_by_name = interconnects_by_name or {}
    nodes, undeclared, tokens_used = [], [], set()
    for p in parts:
        ports = part_ports(p)
        nodes.append({
            'name': field_of(p, 'name'),
            'kind': field_of(p, 'kind'),
            'title': field_of(p, 'title'),
            'ports_provided': ports['provided'],
            'ports_required': ports['required'],
            'declared': ports['declared'],
        })
        tokens_used.update(ports['provided'])
        tokens_used.update(ports['required'])
        if not ports['declared']:
            undeclared.append(field_of(p, 'name'))
    edges = []
    for i, pa in enumerate(parts):
        for pb in parts[i + 1:]:
            edges.extend(viable_links(pa, pb))
    missing_vocab = sorted(
        t for t in tokens_used if t not in interconnects_by_name)
    return {
        'nodes': nodes,
        'edges': edges,
        'undeclared': sorted(undeclared),
        'vocabularyMissing': missing_vocab,
        'note': ('parts in `undeclared` declare no ports — the '
                 'matrix cannot answer for them until '
                 'ports_provided/ports_required land on their '
                 'specs_json'
                 if undeclared else
                 'every part declares its ports'),
    }
def port_budget_gates(build, parts_by_name):
    """Provided-vs-required totals per token across one build.
    Verdicts: ok (enough), mismatch (SOME provided but short —
    a declared shortage), unverified (nothing declares provision
    of a required token, or no part declares ports at all)."""
    from computers.custom.computers_gates import _parts_of
    parts = _parts_of(build, parts_by_name)
    declared = [p for p in parts if part_ports(p)['declared']]
    gates = []
    if not declared:
        return [{'check': 'port-budget', 'verdict': 'unverified',
                 'detail': 'no part in the build declares '
                           'ports_provided/ports_required — '
                           'declare them on specs_json to start '
                           'answering'}]
    provided, required, requirers = {}, {}, {}
    for p in parts:
        ports = part_ports(p)
        for token, n in ports['provided'].items():
            provided[token] = provided.get(token, 0) + n
        for token, n in ports['required'].items():
            required[token] = required.get(token, 0) + n
            requirers.setdefault(token, []).append(
                field_of(p, 'name'))
    for token in sorted(required):
        need, have = required[token], provided.get(token, 0)
        who = ', '.join(requirers[token])
        if have == 0:
            gates.append({
                'check': f'port-budget:{token}',
                'verdict': 'unverified',
                'detail': f'{need} required ({who}) but no part '
                          f'declares providing "{token}" — a '
                          f'provider part may exist undeclared',
            })
        else:
            ok = have >= need
            gates.append({
                'check': f'port-budget:{token}',
                'verdict': 'ok' if ok else 'mismatch',
                'detail': f'{need} required ({who}) vs {have} '
                          f'provided',
            })
    return gates
def _ic(name, display_name, kind, carries, attachment, summary,
        gaps_note=''):
    return {'name': name, 'display_name': display_name,
            'kind': kind, 'carries': carries,
            'attachment': attachment, 'summary': summary,
            'gaps_note': gaps_note, 'published': True,
            'is_prior': True, 'notes': ''}
SEED_INTERCONNECTS = [
    _ic('cpu-socket', 'CPU socket (declared model)', 'socket',
        'data+power', 'internal',
        'The socket pairing stays the ai-8 string-equality gate '
        '(lga4189 vs lga4189); this token adds it to the port '
        'matrix as one seat.'),
    _ic('ddr4-dimm', 'DDR4 DIMM slot', 'slot', 'data+power',
        'internal',
        'One physical DDR4 module seat; kits must declare their '
        'module count (the ram-slots gate rule).'),
    _ic('pcie-x16', 'PCIe x16 slot', 'slot', 'data+power',
        'internal',
        'Full-length expansion slot (GPUs, accelerators).'),
    _ic('pcie-x4', 'PCIe x4 slot', 'slot', 'data+power',
        'internal',
        'Short expansion slot (NVMe carriers, USB controllers, '
        'NICs).'),
    _ic('m2-key-m', 'M.2 Key-M slot', 'slot', 'data+power',
        'internal', 'NVMe/SATA storage module seat.'),
    _ic('m2-key-e', 'M.2 Key-E slot', 'slot', 'data+power',
        'internal',
        'The EMBEDDED comms seat — WiFi/BT modules mount here.'),
    _ic('sata-data', 'SATA data port', 'port', 'data', 'internal',
        'One drive\'s data link; pairs with a psu sata-power '
        'lead.'),
    _ic('sata-power', 'SATA power lead', 'connector', 'power',
        'internal', 'PSU-side drive power.'),
    _ic('usb-a', 'USB-A port', 'port', 'data+power', 'external',
        'External Type-A attachment point (dongles, adapters, '
        'peripherals).'),
    _ic('usb-c', 'USB-C port', 'port', 'data+power', 'external',
        'External Type-C attachment point.',
        gaps_note='generation/alt-mode (3.2 gen2, USB4, DP-alt) '
                  'not modeled yet — a later column, not a new '
                  'mechanism'),
    _ic('usb2-header', 'USB 2.0 internal header', 'header',
        'data+power', 'internal',
        'Motherboard header a case front-panel or internal '
        'device cables into — one of the parts-that-enable-USB.'),
    _ic('usb3-header', 'USB 3.x internal header', 'header',
        'data+power', 'internal',
        'Front-panel USB-A 3.x enablement.'),
    _ic('usb-c-header', 'USB-C front-panel header', 'header',
        'data+power', 'internal',
        'Front-panel USB-C enablement — absent on many boards; '
        'a pcie-x4 USB controller card is the retrofit path.'),
    _ic('rj45', 'RJ45 Ethernet port', 'port', 'data', 'external',
        'Wired network attachment.'),
    _ic('atx-24pin', 'ATX 24-pin', 'connector', 'power',
        'internal', 'Main board power.'),
    _ic('eps-8pin', 'EPS 8-pin CPU power', 'connector', 'power',
        'internal', 'CPU power feed(s).'),
    _ic('pcie-power-8pin', 'PCIe 8-pin power', 'connector',
        'power', 'internal', 'GPU/accelerator power feed(s).'),
]
SEED_PORT_PART_CLASSES = [
    {
        'name': 'comms',
        'display_name': 'Communications',
        'summary': 'WiFi / Bluetooth / cellular parts — EMBEDDED '
                   '(an m2-key-e module) or ATTACHED (a usb-a / '
                   'usb-c adapter). Which of the two a part is '
                   'falls out of its ports_required declaration, '
                   'not a subclass.',
        'declared_specs_json': json.dumps([
            {'field': 'ports_required', 'unit': '{token: count}',
             'meaning': 'the seat(s) this part occupies '
                        '(m2-key-e ¦ usb-a ¦ usb-c)'},
            {'field': 'radio', 'unit': 'text',
             'meaning': 'wifi6e / bt5.3 / lte-cat4 ... — '
                        'declared, not derived'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'ports_required',
             'gate': 'port-budget',
             'counterpart': 'motherboard|usb-expansion'},
        ]),
        'gaps_note': 'antenna routing and regulatory (FCC/CE) '
                     'columns not modeled; declaring radio bands '
                     'would let profiles gate on connectivity.',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'usb-expansion',
        'display_name': 'USB enablement',
        'summary': 'The parts that make usb-a/usb-c attachment '
                   'EXIST: PCIe USB controller cards, hubs, '
                   'front-panel header adapters. They REQUIRE a '
                   'seat (pcie-x4 / usb3-header / usb-c) and '
                   'PROVIDE ports.',
        'declared_specs_json': json.dumps([
            {'field': 'ports_required', 'unit': '{token: count}',
             'meaning': 'the seat this enabler occupies'},
            {'field': 'ports_provided', 'unit': '{token: count}',
             'meaning': 'the attachment points it adds'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'ports_provided',
             'gate': 'port-budget', 'counterpart': 'comms'},
        ]),
        'gaps_note': 'per-port bandwidth/power budgets not '
                     'modeled — provided counts answer seats, '
                     'not throughput.',
        'published': True, 'is_prior': True, 'notes': '',
    },
]
def _example_part(name, title, kind, specs, note):
    return {
        'name': name, 'title': title, 'kind': kind, 'model': '',
        'condition': 'new', 'specs_json': json.dumps(specs),
        'price_amount': 0.0, 'price_unit': 'USD',
        'price_as_of': '', 'price_source': '',
        'price_note': 'UNPRICED example — set a dated price when '
                      'a real part is sourced (ai-8 rule)',
        'notes': note, 'published': True, 'is_prior': True,
    }
SEED_PORT_EXAMPLE_PARTS = [
    _example_part(
        'comms-m2e-wifi-bt-example',
        'WiFi/BT module, M.2 Key-E (EMBEDDED example)', 'comms',
        {'radio': 'wifi + bt (declare the real bands on a '
                  'sourced part)',
         'ports_required': {'m2-key-e': 1}},
        'cmp-c-6 example: the embedded comms path.'),
    _example_part(
        'comms-usb-wifi-example',
        'USB WiFi adapter (ATTACHED example)', 'comms',
        {'radio': 'wifi (declare on a sourced part)',
         'ports_required': {'usb-a': 1}},
        'cmp-c-6 example: the attached comms path — needs a '
        'usb-a port something in the build PROVIDES.'),
    _example_part(
        'usbexp-pcie-usbc-card-example',
        'PCIe x4 USB-C controller card (ENABLER example)',
        'usb-expansion',
        {'ports_required': {'pcie-x4': 1},
         'ports_provided': {'usb-c': 2}},
        'cmp-c-6 example: the enablement path — a board without '
        'usb-c gains it by spending a pcie-x4 seat.'),
]
