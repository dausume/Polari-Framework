"""
@module computers.custom.computers_gates

cmp-c-2: assembly feasibility as DFA-STYLE NAMED GATES (the
composition audit_promotion discipline applied to computer
assembly): every gate has a name, a verdict, and a refusal detail
that quotes the failing numbers; an undeclared spec yields
'unverified — <spec> not declared' (the affordance), and the
overall verdict never rounds an unverified up to a pass.

The four ai-8 checks (socket, ram-type, psu-wattage,
gpu-clearance) are REUSED from computerparts.custom.parts_assembly — this
module adds the gates the taxonomy's new declared specs enable:

  ram-slots     count of ram modules <= motherboard.ram_slots
  slot-budget   pcie-slot consumers (gpu/nic/fpga cards declaring
                pcie_slots) <= motherboard.pcie_x16_slots

computers genuinely imports computerparts (FEATURE_REQUIRES pair);
composition is never imported here.

@consumers
  - computers.computers_api (assembly payloads)
  - computers.computers_selftest
"""

import json

from computerparts.custom.parts_assembly import assembly_check
from computerparts.parts_basis import build_report

from computers.computers_basis import field_of


def _specs(part):
    raw = field_of(part, 'specs_json', '{}')
    try:
        return json.loads(raw or '{}')
    except ValueError:
        return {}


def _parts_of(build, parts_by_name):
    try:
        names = json.loads(field_of(build, 'parts_json', '[]')
                           or '[]')
    except ValueError:
        names = []
    return [parts_by_name[n] for n in names if n in parts_by_name]


def _first_of_kind(parts, kind):
    for p in parts:
        if field_of(p, 'kind') == kind:
            return p
    return None


def extended_gates(build, parts_by_name):
    """The cmp-c-2 additions over the ai-8 checks. Pure."""
    parts = _parts_of(build, parts_by_name)
    mb = _specs(_first_of_kind(parts, 'motherboard'))
    gates = []

    def add(gate, verdict, detail):
        gates.append({'check': gate, 'verdict': verdict,
                      'detail': detail})

    # ram-slots: PHYSICAL module count vs declared board slots.
    # A ram row may be a kit ('2x16') — it must declare 'modules'
    # or the count would be a lie; undeclared -> unverified.
    ram_rows = [p for p in parts if field_of(p, 'kind') == 'ram']
    undeclared = [field_of(p, 'name') for p in ram_rows
                  if not _specs(p).get('modules')]
    if ram_rows and not undeclared and mb.get('ram_slots'):
        count = sum(int(_specs(p)['modules']) for p in ram_rows)
        ok = count <= int(mb['ram_slots'])
        add('ram-slots', 'ok' if ok else 'mismatch',
            '%d physical module(s) vs %d board slot(s)'
            % (count, int(mb['ram_slots'])))
    elif ram_rows and undeclared:
        add('ram-slots', 'unverified',
            'modules (per-kit physical count) not declared on: '
            + ', '.join(undeclared))
    elif ram_rows:
        add('ram-slots', 'unverified',
            'ram_slots not declared on the motherboard')
    else:
        add('ram-slots', 'unverified', 'no ram parts in the build')

    # slot-budget: pcie consumers vs declared board slots
    consumers = [p for p in parts
                 if _specs(p).get('pcie_slots')]
    if consumers and mb.get('pcie_x16_slots'):
        need = sum(int(_specs(p)['pcie_slots']) for p in consumers)
        have = int(mb['pcie_x16_slots'])
        ok = need <= have
        add('slot-budget', 'ok' if ok else 'mismatch',
            '%d slot(s) consumed (%s) vs %d board slot(s)'
            % (need,
               ', '.join(field_of(p, 'name') for p in consumers),
               have))
    elif consumers:
        add('slot-budget', 'unverified',
            'pcie_x16_slots not declared on the motherboard '
            '(consumers present: %s)'
            % ', '.join(field_of(p, 'name') for p in consumers))
    else:
        add('slot-budget', 'unverified',
            'no part declares pcie_slots — declare it on '
            'gpu/nic/fpga rows to start answering')
    return gates


def assembly_gate_report(assembly, build, parts_by_name):
    """The full cmp-c-2 gate report for one assembly: ai-8 checks
    + extended gates + derived cost, refusals named per gate."""
    from computers.computers_ports_basis import port_budget_gates
    base = assembly_check(build, parts_by_name)
    gates = (list(base['checks'])
             + extended_gates(build, parts_by_name)
             + port_budget_gates(build, parts_by_name))
    answered = [g for g in gates if g['verdict'] != 'unverified']
    feasible = None
    if answered:
        feasible = all(g['verdict'] == 'ok' for g in answered)
    refusals = [g for g in gates if g['verdict'] == 'mismatch']
    unverified = [g for g in gates if g['verdict'] == 'unverified']
    return {
        'assembly': field_of(assembly, 'name'),
        'build': field_of(build, 'name'),
        'gates': gates,
        'feasible': feasible,
        'refusals': refusals,
        'unverified': unverified,
        'report': build_report(build, parts_by_name),
        'note': ('every ANSWERED gate passes; %d gate(s) stay '
                 'honestly unverified' % len(unverified)
                 if feasible else
                 'a declared gate REFUSES — see refusals'
                 if feasible is False else
                 'no gate answerable yet — declare the taxonomy '
                 'specs on the part rows'),
    }


def composition_view(assembly, build, parts_by_name):
    """The assembly as a composition-shaped tree WITHOUT writing
    composition rows: members = the parts, interfaces = the
    taxonomy's slot interfaces, every one designed-separable — so
    composition's own derivation rule yields 'assembly'
    (all-separable). This is a VIEW; materializing real
    CompositionNode/InterfaceDefinition rows is the later splice
    (assembly.node_ref stays empty until then)."""
    parts = _parts_of(build, parts_by_name)
    kinds = {}
    for p in parts:
        kinds.setdefault(field_of(p, 'kind'), []).append(
            field_of(p, 'name'))
    interfaces = []

    def iface(a_kind, b_kind, scheme):
        if a_kind in kinds and b_kind in kinds:
            interfaces.append({
                'member_a': kinds[a_kind][0],
                'member_b': kinds[b_kind][0],
                'retention_scheme': scheme,
                'designed_separable': True,
            })

    iface('cpu', 'motherboard', 'socket-latch')
    iface('ram', 'motherboard', 'dimm-slot')
    iface('gpu', 'motherboard', 'pcie-slot')
    iface('storage', 'motherboard', 'm2-or-sata')
    iface('nic', 'motherboard', 'pcie-slot')
    iface('fpga-accelerator', 'motherboard', 'pcie-or-usb')
    iface('cooler', 'cpu', 'bracket-mount')
    iface('motherboard', 'case', 'standoff-screws')
    iface('psu', 'case', 'bay-screws')
    members = [field_of(p, 'name') for p in parts]
    derived = 'assembly' if interfaces else ''
    return {
        'assembly': field_of(assembly, 'name'),
        'members': members,
        'interfaces': interfaces,
        'derived_level': derived,
        'derivation': ('every interface is designed-separable -> '
                       'composition derives ASSEMBLY (no bound '
                       'set); a promotion would need the DFA gate'
                       if derived else
                       'no interfaces derivable — build has fewer '
                       'than two known-kind parts'),
        'materialized': False,
        'note': 'view only — real composition rows are the later '
                'materialization splice (assembly.node_ref)',
    }
