"""
@module kirimoto.kirimoto_basis

The INDEX of kirimoto rows (design §7) + the seeds: the store row (an
isle-app container), the instance row, and the Voron device profile.
"""
from kirimoto.objects.kirimoto.SlicerInstance import SlicerInstance  # noqa: F401
from kirimoto.objects.kirimoto.SlicerProfile import SlicerProfile  # noqa: F401

#: the upstream pin — filled after PRINTER_STACK_GATE.md verifies the licence; the store refuses while unpinned
KIRIMOTO_UPSTREAM = {'repo': 'https://github.com/GridSpace/grid-apps', 'commit': 'ff7692241c48c3495da0bb8eb7455f906f3abb2d', 'licence': 'MIT (license.md; 256/275 source headers say All Rights Reserved and defer to license.md — PRINTER_STACK_GATE.md, amber note)'}
KIRIMOTO_IMAGE = 'polari/kirimoto:%s' % (KIRIMOTO_UPSTREAM['commit'][:10] if KIRIMOTO_UPSTREAM['commit'] != '<PIN ME>' else 'unpinned')

SEED_KIRIMOTO_CATALOG = [{
    'name': 'kirimoto', 'title': 'Kiri:Moto slicer', 'kind': 'mesh-app', 'category': 'printing',
    'description': 'Browser-based slicer (FDM/CNC/laser) as an isle container app at kirimoto.isle; slices the printing suite\'s SliceJobs and sends gcode to the Voron guest\'s Moonraker.',
    'source_ref': KIRIMOTO_IMAGE, 'service': 'kirimoto', 'port': 8080,   # gs-app-server serves /kiri on 8080 'domain': 'kirimoto.isle', 'published': KIRIMOTO_UPSTREAM['commit'] != '<PIN ME>',
    'notes': 'unpublished until the upstream commit is pinned (licence gate)' if KIRIMOTO_UPSTREAM['commit'] == '<PIN ME>' else ''}]

SEED_SLICER_INSTANCES = [{'name': 'kirimoto', 'domain': 'kirimoto.isle', 'upstream_commit': KIRIMOTO_UPSTREAM['commit'], 'moonraker_targets_json': '["voron-2.4-350"]',
                          'notes': 'the row the isle updates after isle app deploy kirimoto'}]
SEED_SLICER_PROFILES = [{'name': 'voron-2.4-350@kirimoto', 'printer': 'voron-2.4-350', 'bed_x_mm': 350.0, 'bed_y_mm': 350.0, 'bed_z_mm': 340.0,
                         'nozzle_mm': 0.4, 'gcode_flavor': 'klipper', 'notes': 'derived from the seeded PrinterDefinition bed'}]

KIRIMOTO_SEED_PAIRS = [('SlicerInstance', SlicerInstance, SEED_SLICER_INSTANCES), ('SlicerProfile', SlicerProfile, SEED_SLICER_PROFILES)]
KIRIMOTO_CLASSES = [cls for _, cls, _ in KIRIMOTO_SEED_PAIRS]
