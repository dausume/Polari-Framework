"""@module magnetics.objects.magnet_circuit._shared — what the magnet_circuit row classes share (constants, seeds, helpers); split from magnet_circuit_basis.py (sap-2c)."""

ELEMENT_KINDS = ('mmf-coil', 'core-segment', 'air-gap', 'magnet',
                 'leakage-path', 'flux-probe')
SEED_MAGNETIC_CIRCUITS = [
    {
        'name': 'gapped-toroid-demo',
        'description': 'Gapped toroid inductor: 100-turn coil at '
                       '1 A around a magnetic-geopolymer core '
                       '(mu 2.196) with a 2 mm air gap. THE '
                       'hand-computable series loop — and the '
                       'demonstration that at mu~2 the CORE, not '
                       'the gap, dominates the reluctance (the '
                       'physics-honesty datum rendered as numbers).',
        'analyses_json': '[{"type": "op"}, {"type": "sweep", '
                         '"element": "gap1", "param": "length_m", '
                         '"values": [0.001, 0.002, 0.004, 0.008]}]',
        'notes': 'mag-3 seed; expected flux pinned in selftest.',
    },
    {
        'name': 'c-core-coil-gap-demo',
        'description': 'C-core + coil + working gap + flux probe: '
                       'the probe branch proves the ammeter shape '
                       '(zero-MMF source) and reads the same flux '
                       'as the series loop.',
        'analyses_json': '[{"type": "op"}]',
        'notes': 'mag-3 seed.',
    },
    {
        'name': 'horseshoe-keeper-demo',
        'description': 'Hexaferrite horseshoe magnet + fired-'
                       'ferrite keeper + explicit leakage path: '
                       'the magnet is a Thevenin MMF source '
                       '(H_c*l_m) behind its internal reluctance; '
                       'leakage splits the flux — the first '
                       'parallel network.',
        'analyses_json': '[{"type": "op"}]',
        'notes': 'mag-3 seed; magnet MMF = 250e3 * 0.02 = 5000 '
                 'A-turns from opt-srfe12o19 h_c_ka_m.',
    },
]
SEED_FLUX_NODES = [
    # gapped-toroid-demo: coil 0->a, core a->b, gap b->0.
    {'name': 'toroid-node-a', 'circuit_name': 'gapped-toroid-demo',
     'node': 'a', 'description': 'coil exit / core entry'},
    {'name': 'toroid-node-b', 'circuit_name': 'gapped-toroid-demo',
     'node': 'b', 'description': 'core exit / gap entry'},
    {'name': 'toroid-node-0', 'circuit_name': 'gapped-toroid-demo',
     'node': '0', 'is_reference': True, 'description': 'return'},
    # c-core-coil-gap-demo: coil 0->a, core a->b, gap b->c,
    # probe c->0.
    {'name': 'ccore-node-a', 'circuit_name': 'c-core-coil-gap-demo',
     'node': 'a', 'description': 'coil exit'},
    {'name': 'ccore-node-b', 'circuit_name': 'c-core-coil-gap-demo',
     'node': 'b', 'description': 'core exit / gap entry'},
    {'name': 'ccore-node-c', 'circuit_name': 'c-core-coil-gap-demo',
     'node': 'c', 'description': 'gap exit / probe entry'},
    {'name': 'ccore-node-0', 'circuit_name': 'c-core-coil-gap-demo',
     'node': '0', 'is_reference': True, 'description': 'return'},
    # horseshoe-keeper-demo: magnet 0->a, poles a->b, keeper b->0,
    # leakage a->0 (parallel).
    {'name': 'horseshoe-node-a', 'circuit_name':
     'horseshoe-keeper-demo', 'node': 'a',
     'description': 'magnet north pole face'},
    {'name': 'horseshoe-node-b', 'circuit_name':
     'horseshoe-keeper-demo', 'node': 'b',
     'description': 'pole/keeper junction'},
    {'name': 'horseshoe-node-0', 'circuit_name':
     'horseshoe-keeper-demo', 'node': '0', 'is_reference': True,
     'description': 'south pole return'},
]
SEED_MAGNETIC_ELEMENTS = [
    # --- gapped-toroid-demo ---
    {'name': 'coil1', 'circuit_name': 'gapped-toroid-demo',
     'kind': 'mmf-coil',
     'params_json': '{"turns": 100, "amps": 1.0}',
     'nodes_json': '["a", "0"]',
     'description': '100 turns at 1 A = 100 A-turns MMF'},
    {'name': 'core1', 'circuit_name': 'gapped-toroid-demo',
     'kind': 'core-segment',
     'params_json': '{"length_m": 0.2, "area_m2": 1e-4, '
                    '"material_ref": "opt-geopolymer-ferrite"}',
     'nodes_json': '["a", "b"]',
     'description': '20 cm mean path, 1 cm^2, mu from the '
                    'Section-A catalog row'},
    {'name': 'gap1', 'circuit_name': 'gapped-toroid-demo',
     'kind': 'air-gap',
     'params_json': '{"length_m": 0.002, "area_m2": 1e-4}',
     'nodes_json': '["b", "0"]',
     'description': '2 mm working gap, fringing 1.0 (the honest '
                    'default until measured)'},
    # --- c-core-coil-gap-demo ---
    {'name': 'coil2', 'circuit_name': 'c-core-coil-gap-demo',
     'kind': 'mmf-coil',
     'params_json': '{"turns": 200, "amps": 0.5}',
     'nodes_json': '["a", "0"]',
     'description': '200 turns at 0.5 A = 100 A-turns'},
    {'name': 'core2', 'circuit_name': 'c-core-coil-gap-demo',
     'kind': 'core-segment',
     'params_json': '{"length_m": 0.15, "area_m2": 2e-4, '
                    '"material_ref": "opt-fired-ferrite-ceramic"}',
     'nodes_json': '["a", "b"]',
     'description': 'fired-ceramic C-core (mu 2.484, the cast '
                    'ceiling)'},
    {'name': 'gap2', 'circuit_name': 'c-core-coil-gap-demo',
     'kind': 'air-gap',
     'params_json': '{"length_m": 0.001, "area_m2": 2e-4, '
                    '"fringing_factor": 1.1}',
     'nodes_json': '["b", "c"]',
     'description': '1 mm gap with a 1.1 fringing prior (an '
                    'estimate, said so)'},
    {'name': 'probe2', 'circuit_name': 'c-core-coil-gap-demo',
     'kind': 'flux-probe', 'params_json': '{}',
     'nodes_json': '["c", "0"]',
     'description': 'the flux ammeter — must read the loop flux'},
    # --- horseshoe-keeper-demo ---
    {'name': 'magnet3', 'circuit_name': 'horseshoe-keeper-demo',
     'kind': 'magnet',
     'params_json': '{"length_m": 0.02, "area_m2": 1e-4, '
                    '"material_ref": "opt-srfe12o19"}',
     'nodes_json': '["a", "0"]',
     'description': 'SrFe12O19 horseshoe: MMF = H_c*l_m = 5000 '
                    'A-turns, internal reluctance from mu_r_eff '
                    '1.3'},
    {'name': 'poles3', 'circuit_name': 'horseshoe-keeper-demo',
     'kind': 'core-segment',
     'params_json': '{"length_m": 0.05, "area_m2": 1e-4, '
                    '"material_ref": "opt-fired-ferrite-ceramic"}',
     'nodes_json': '["a", "b"]',
     'description': 'pole extensions'},
    {'name': 'keeper3', 'circuit_name': 'horseshoe-keeper-demo',
     'kind': 'core-segment',
     'params_json': '{"length_m": 0.03, "area_m2": 1e-4, '
                    '"material_ref": "opt-fired-ferrite-ceramic"}',
     'nodes_json': '["b", "0"]',
     'description': 'the keeper bar'},
    {'name': 'leak3', 'circuit_name': 'horseshoe-keeper-demo',
     'kind': 'leakage-path',
     'params_json': '{"reluctance_per_wb": 2e9}',
     'nodes_json': '["a", "0"]',
     'description': 'explicit leakage prior (2e9 A-t/Wb — an '
                    'estimate until measured)'},
]
