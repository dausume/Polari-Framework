"""@module electrodevice.objects.device._shared — what the device row classes share (constants, seeds, helpers); split from device_basis.py (sap-2c)."""

SEED_DEVICES = [
    {'name': 'cnt-solgel-led-resistor', 'device_type': 'resistor',
     'sim_model': 'cnt-solgel-percolation',
     'length_m': 0.002, 'cross_section_m2': 1.4e-8,
     'film_thickness_m': 1e-4,   # 100 um paste trace -> W 140 um
     'notes': 'Current limiter for the renode-led-grid pins; derive '
              'before use.'},
    # CNT-network FETs (sol-gel gate dielectric): channel on-state
    # from the percolation sim; threshold/type from the doped-CNT
    # frontier-orbital profiles. Short fat channel = switch-grade Ron.
    {'name': 'cnt-nfet-led-switch', 'device_type': 'nfet',
     'sim_model': 'cnt-solgel-percolation',
     'semiconductor_profile': 'cnt-potash-doped',
     'length_m': 2e-5, 'cross_section_m2': 1.4e-8,
     'film_thickness_m': 1e-6,   # 1 um film -> W 14 mm (honest!)
     'notes': 'Low-side LED switch + inverter pull-down.'},
    {'name': 'cnt-pfet-inverter', 'device_type': 'pfet',
     'sim_model': 'cnt-solgel-percolation',
     'semiconductor_profile': 'cnt-p-doped',
     'length_m': 2e-5, 'cross_section_m2': 1.4e-8,
     'film_thickness_m': 1e-6,
     'notes': 'Inverter pull-up (complementary to the nfet).'},
]
