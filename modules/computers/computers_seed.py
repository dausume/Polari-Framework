"""
@module computers.computers_seed

cmp-c seed rows: the component taxonomy (one row per part kind),
the v1 profile set (Dustin's decision 2: the four planned + the
dl-6 low-power member node), and assemblies wrapping the ai-8
example builds. Seeded through moduleService.seed_upsert — floors
and taxonomy vocabularies WILL evolve, so the seed must converge
live prior rows (never insert-by-name).

Profile floors carry their evidence in `rationale` — the knobs
ethos: a floor without a why is folklore with units.
"""

import json

#: One row per computerparts PART_KINDS entry (incl. the cmp-c-1
#: additions nic / fpga-accelerator). declared_specs = what a part
#: of this kind is expected to declare; interface_specs = which of
#: them feed which assembly gate.
SEED_COMPUTER_PART_CLASSES = [
    {
        'name': 'cpu', 'display_name': 'CPU',
        'summary': 'The processor: core count and socket drive '
                   'both capability floors and board fit.',
        'declared_specs_json': json.dumps([
            {'field': 'cores', 'unit': '', 'meaning':
             'physical cores'},
            {'field': 'threads', 'unit': '', 'meaning':
             'hardware threads'},
            {'field': 'socket', 'unit': '', 'meaning':
             'physical socket (AM5, LGA4189, ...)'},
            {'field': 'tdp_w', 'unit': 'W', 'meaning':
             'thermal design power'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'socket', 'gate': 'socket',
             'counterpart': 'motherboard'},
            {'field': 'tdp_w', 'gate': 'cooler-capacity',
             'counterpart': 'cooler'},
        ]),
        'gaps_note': 'tdp_w undeclared on the seed rows — the '
                     'cooler-capacity gate stays unverified until '
                     'someone declares it (future gate).',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'motherboard', 'display_name': 'Motherboard',
        'summary': 'The interface hub: nearly every gate has the '
                   'board as one side.',
        'declared_specs_json': json.dumps([
            {'field': 'socket', 'unit': '', 'meaning':
             'cpu socket'},
            {'field': 'ram_type', 'unit': '', 'meaning':
             'DDR generation'},
            {'field': 'ram_slots', 'unit': '', 'meaning':
             'physical DIMM slots'},
            {'field': 'pcie_x16_slots', 'unit': '', 'meaning':
             'x16-size expansion slots'},
            {'field': 'm2_slots', 'unit': '', 'meaning':
             'M.2 storage slots'},
            {'field': 'form_factor', 'unit': '', 'meaning':
             'ATX / microATX / E-ATX'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'socket', 'gate': 'socket',
             'counterpart': 'cpu'},
            {'field': 'ram_type', 'gate': 'ram-type',
             'counterpart': 'ram'},
            {'field': 'ram_slots', 'gate': 'ram-slots',
             'counterpart': 'ram'},
            {'field': 'pcie_x16_slots', 'gate': 'slot-budget',
             'counterpart': 'gpu/nic/fpga-accelerator'},
        ]),
        'gaps_note': 'pcie_x16_slots left undeclared on the seed '
                     'boards on purpose (board-model-specific) — '
                     'the slot-budget gate answers the moment a '
                     'real board declares it.',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'ram', 'display_name': 'Memory',
        'summary': 'Capacity feeds the floors; type and physical '
                   'module count feed the board gates.',
        'declared_specs_json': json.dumps([
            {'field': 'capacity_mb', 'unit': 'MB', 'meaning':
             'total capacity of the row (kit total)'},
            {'field': 'ram_type', 'unit': '', 'meaning':
             'DDR generation'},
            {'field': 'modules', 'unit': '', 'meaning':
             'PHYSICAL modules in the kit (a 2x16 kit is 2)'},
            {'field': 'speed_mt_s', 'unit': 'MT/s', 'meaning':
             'rated transfer rate'},
            {'field': 'ecc', 'unit': '', 'meaning':
             'error-correcting (bool)'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'ram_type', 'gate': 'ram-type',
             'counterpart': 'motherboard'},
            {'field': 'modules', 'gate': 'ram-slots',
             'counterpart': 'motherboard'},
        ]),
        'gaps_note': 'speed_mt_s/ecc undeclared on seeds — '
                     'performance matching is measured-benchmark '
                     'territory (deliberately not a gate).',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'storage', 'display_name': 'Storage (HDD/SSD)',
        'summary': 'Capacity, interface and endurance — the '
                   'DB-bound profile lives or dies here.',
        'declared_specs_json': json.dumps([
            {'field': 'capacity_mb', 'unit': 'MB', 'meaning':
             'usable capacity'},
            {'field': 'interface', 'unit': '', 'meaning':
             'nvme / sata'},
            {'field': 'form_factor', 'unit': '', 'meaning':
             'm2-2280 / 2.5in / 3.5in'},
            {'field': 'endurance_tbw', 'unit': 'TBW', 'meaning':
             'rated write endurance (DB workloads care)'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'form_factor', 'gate': 'm2-or-bay-budget',
             'counterpart': 'motherboard/case'},
        ]),
        'gaps_note': 'endurance_tbw undeclared on seeds — the '
                     'DB-bound profile scores capacity today and '
                     'says so; endurance floors start answering '
                     'when rows declare TBW.',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'gpu', 'display_name': 'Graphics card',
        'summary': 'VRAM floors (assistive-AI), power draw '
                   '(psu-wattage), length (clearance), slots '
                   '(slot-budget).',
        'declared_specs_json': json.dumps([
            {'field': 'vram_mb', 'unit': 'MB', 'meaning':
             'video memory'},
            {'field': 'watts', 'unit': 'W', 'meaning':
             'board power'},
            {'field': 'length_mm', 'unit': 'mm', 'meaning':
             'card length'},
            {'field': 'pcie_slots', 'unit': '', 'meaning':
             'x16-size slots consumed'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'watts', 'gate': 'psu-wattage',
             'counterpart': 'psu'},
            {'field': 'length_mm', 'gate': 'gpu-clearance',
             'counterpart': 'case'},
            {'field': 'pcie_slots', 'gate': 'slot-budget',
             'counterpart': 'motherboard'},
        ]),
        'gaps_note': 'length_mm still undeclared on the seed '
                     'cards (the ai-8 honest gap, unchanged) — '
                     'gpu-clearance stays unverified until card '
                     'lengths are declared.',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'psu', 'display_name': 'Power supply',
        'summary': 'Wattage vs the build draw + headroom.',
        'declared_specs_json': json.dumps([
            {'field': 'watts', 'unit': 'W', 'meaning':
             'rated output'},
            {'field': 'efficiency', 'unit': '', 'meaning':
             '80+ tier'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'watts', 'gate': 'psu-wattage',
             'counterpart': 'gpu'},
        ]),
        'gaps_note': '', 'published': True, 'is_prior': True,
        'notes': '',
    },
    {
        'name': 'case', 'display_name': 'Chassis',
        'summary': 'Physical clearances and form-factor fit.',
        'declared_specs_json': json.dumps([
            {'field': 'max_gpu_length_mm', 'unit': 'mm',
             'meaning': 'gpu clearance'},
            {'field': 'form_factors', 'unit': '', 'meaning':
             'board sizes accepted'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'max_gpu_length_mm', 'gate':
             'gpu-clearance', 'counterpart': 'gpu'},
        ]),
        'gaps_note': 'max_gpu_length_mm undeclared on the seed '
                     'case (ai-8 gap, unchanged).',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'cooler', 'display_name': 'CPU cooler',
        'summary': 'Socket mount + thermal capacity.',
        'declared_specs_json': json.dumps([
            {'field': 'socket', 'unit': '', 'meaning':
             'supported socket(s)'},
            {'field': 'tdp_capacity_w', 'unit': 'W', 'meaning':
             'rated dissipation'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'tdp_capacity_w', 'gate': 'cooler-capacity',
             'counterpart': 'cpu'},
        ]),
        'gaps_note': 'cooler-capacity is a FUTURE gate — neither '
                     'side declares TDP on the seeds yet.',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'nic', 'display_name': 'Network card',
        'summary': 'cmp-c-1 addition: member/hosting nodes on the '
                   'isle care about real NICs.',
        'declared_specs_json': json.dumps([
            {'field': 'speed_gbps', 'unit': 'Gb/s', 'meaning':
             'per-port rate'},
            {'field': 'ports', 'unit': '', 'meaning':
             'port count'},
            {'field': 'pcie_slots', 'unit': '', 'meaning':
             'x16-size slots consumed'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'pcie_slots', 'gate': 'slot-budget',
             'counterpart': 'motherboard'},
        ]),
        'gaps_note': '', 'published': True, 'is_prior': True,
        'notes': '',
    },
    {
        'name': 'fpga-accelerator',
        'display_name': 'FPGA accelerator / dev board',
        'summary': 'cmp-c-1 addition: the FPGA-lab profile\'s '
                   'defining part; also the chip-4 seam\'s future '
                   'landing pad (a chip-ladder artifact declaring '
                   'itself as fulfilling this class — deferred, '
                   'decision 4).',
        'declared_specs_json': json.dumps([
            {'field': 'luts', 'unit': '', 'meaning':
             'logic cells / LUTs'},
            {'field': 'fpga_family', 'unit': '', 'meaning':
             'device family'},
            {'field': 'interface', 'unit': '', 'meaning':
             'pcie / usb-jtag / m2'},
            {'field': 'pcie_slots', 'unit': '', 'meaning':
             'x16-size slots consumed (0 for bench boards)'},
        ]),
        'interface_specs_json': json.dumps([
            {'field': 'pcie_slots', 'gate': 'slot-budget',
             'counterpart': 'motherboard'},
        ]),
        'gaps_note': 'fpga_required is a PRESENCE check — whether '
                     'the interface suits a workload (PCIe DMA vs '
                     'bench JTAG) is declared here, judged '
                     'nowhere yet.',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'prebuilt', 'display_name': 'Prebuilt machine',
        'summary': 'A whole machine sold as one unit — specs are '
                   'machine specs; assembly gates do not apply.',
        'declared_specs_json': json.dumps([
            {'field': 'cores', 'unit': '', 'meaning': 'cores'},
            {'field': 'ram_mb', 'unit': 'MB', 'meaning': 'RAM'},
            {'field': 'disk_mb', 'unit': 'MB', 'meaning': 'disk'},
            {'field': 'vram_mb', 'unit': 'MB', 'meaning': 'VRAM'},
        ]),
        'interface_specs_json': '[]',
        'gaps_note': '', 'published': True, 'is_prior': True,
        'notes': '',
    },
]

#: Decision 2 v1 set: the four planned + low-power member (dl-6
#: 'small'). Floors in the ai-6 gauge vocabulary; every floor's
#: WHY is in rationale.
SEED_COMPUTER_PROFILES = [
    {
        'name': 'profile-standard-user',
        'display_name': 'Standard user desktop',
        'use_case': 'Browsing, documents, a Polari member node — '
                    'the dl-6 "normal" class machine.',
        'floors_json': json.dumps({'cores': 4, 'ram_mb': 8192,
                                   'disk_mb': 256000}),
        'db_binding': 'none', 'db_ref': '',
        'planner_class': 'normal',
        'rationale': 'pub-0 measured 9 modules + deps at ~196 MiB '
                     'RSS on a 4-vCPU/8 GB cap — a 4-core/8 GB '
                     'floor hosts the demo set with room for a '
                     'desktop session.',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'profile-assistive-ai',
        'display_name': 'Assistive-AI dedicated',
        'use_case': 'A machine dedicated to local AI assistance '
                    '(LocalAI-class engines behind the reasoning '
                    'knob).',
        'floors_json': json.dumps({'cores': 8, 'ram_mb': 32768,
                                   'disk_mb': 1000000,
                                   'vram_mb': 16384,
                                   'gpu_required': True}),
        'db_binding': 'none', 'db_ref': '',
        'planner_class': 'gpu',
        'rationale': 'ai-6/ai-7 research: 16 GB VRAM runs '
                     'quantized 13B-30B assistant models; 24 GB '
                     '(used 3090) is the researched value play. '
                     'Disk floor covers model files (tens of GB '
                     'each).',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'profile-db-bound-storage',
        'display_name': 'High-capacity storage — dedicated '
                        'database residence',
        'use_case': 'A machine that dedicated databases DECLARE '
                    'residence on (object-ownership arc).',
        'floors_json': json.dumps({'cores': 8, 'ram_mb': 32768,
                                   'disk_mb': 4000000}),
        'db_binding': 'declare', 'db_ref': '',
        'planner_class': 'highmem',
        'rationale': 'Declare-only v1 (decision 3): the profile '
                     'records residence intent + capacity fit; '
                     'real topology hooks (a database row naming '
                     'this profile) are the object-ownership '
                     'arc\'s half. 4 TB floor = several module '
                     'databases + growth; endurance floors start '
                     'when storage rows declare TBW.',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'profile-fpga-lab',
        'display_name': 'FPGA / hardware dev lab',
        'use_case': 'Synthesis + on-bench FPGA work (hwfpga '
                    'ladder, oss-cad-suite toolchain).',
        'floors_json': json.dumps({'cores': 4, 'ram_mb': 16384,
                                   'fpga_required': True}),
        'db_binding': 'none', 'db_ref': '',
        'planner_class': 'normal',
        'rationale': '16 GB covers Yosys/nextpnr on mid-size '
                     'parts; the defining floor is the FPGA '
                     'itself (presence check, interface '
                     'suitability stated in the taxonomy row).',
        'published': True, 'is_prior': True, 'notes': '',
    },
    {
        'name': 'profile-low-power-member',
        'display_name': 'Low-power member node',
        'use_case': 'Mini PC / thin client joining the isle as a '
                    'member device — hosts nothing.',
        'floors_json': json.dumps({'cores': 2, 'ram_mb': 4096}),
        'db_binding': 'none', 'db_ref': '',
        'planner_class': 'small',
        'rationale': 'dl-6 "small" class (module budget 0, role '
                     'member): the floor is only what a browser '
                     'session needs; anything bigger graduates to '
                     'standard-user.',
        'published': True, 'is_prior': True, 'notes': '',
    },
]

#: Assemblies wrapping the ai-8 example builds — the gate engine
#: and fit matrix run against these.
SEED_COMPUTER_ASSEMBLIES = [
    {
        'name': 'assembly-xeon-6338n',
        'display_name': 'Owned Xeon Gold 6338N build',
        'build_ref': 'build-xeon-6338n',
        'archetype_ref': '', 'node_ref': '',
        'published': True, 'is_prior': True,
        'notes': 'Dustin\'s first-build candidate — the owned '
                 'CPU seeded 2026-08-16.',
    },
    {
        'name': 'assembly-used-3090',
        'display_name': 'Used RTX 3090 AI desktop',
        'build_ref': 'build-used-3090',
        'archetype_ref': '', 'node_ref': '',
        'published': True, 'is_prior': True,
        'notes': 'The researched VRAM value play (ai-7).',
    },
]


def seed_computers(manager):
    """Upsert taxonomy -> profiles -> assemblies (assemblies name
    builds seeded by computerparts, which polariServer seeds
    first). Composition absent -> loud no-op, honest empty
    report."""
    from computerparts.parts_basis import ComputerPartDefinition

    from computers.computers_basis import (
        ComputerAssemblyDefinition, ComputerPartClassDefinition,
        ComputerProfileDefinition,
    )
    from computers.computers_ports_basis import (
        InterconnectDefinition, SEED_INTERCONNECTS,
        SEED_PORT_EXAMPLE_PARTS, SEED_PORT_PART_CLASSES,
    )
    try:
        from moduleService.seed_upsert import upsert_seed_pairs
    except ImportError as exc:
        print(f'[ComputersSeed] moduleService.seed_upsert '
              f'unavailable ({exc}) — computers seeds NOT '
              f'applied', flush=True)
        return []
    return upsert_seed_pairs(
        manager,
        [('ComputerPartClassDefinition',
          ComputerPartClassDefinition,
          SEED_COMPUTER_PART_CLASSES + SEED_PORT_PART_CLASSES),
         ('ComputerProfileDefinition', ComputerProfileDefinition,
          SEED_COMPUTER_PROFILES),
         ('ComputerAssemblyDefinition', ComputerAssemblyDefinition,
          SEED_COMPUTER_ASSEMBLIES),
         # cmp-c-6: the interconnect vocabulary + the unpriced
         # comms/enabler example parts (honest ai-8 rows).
         ('InterconnectDefinition', InterconnectDefinition,
          SEED_INTERCONNECTS),
         ('ComputerPartDefinition', ComputerPartDefinition,
          SEED_PORT_EXAMPLE_PARTS)],
        tag='ComputersSeed')
