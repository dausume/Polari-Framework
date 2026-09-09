"""
@module printing_suite.printing_suite_basis

The INDEX of printing_suite rows (design §7) + the suite seeds: the suite,
its parts (with placement needs), the contracts between them, and one
example PrintProfile for the seeded Voron in sim mode.
"""
from printing_suite.objects.printing.MaterialLot import MaterialLot, MATERIAL_FORMS  # noqa: F401
from printing_suite.objects.printing.PrintProfile import PrintProfile  # noqa: F401
from printing_suite.objects.printing.SliceJob import SliceJob, SLICE_STATES, SHAPE_SOURCES  # noqa: F401
from printing_suite.objects.printing.GcodeArtifact import GcodeArtifact  # noqa: F401
from printing_suite.objects.printing.PrintJob import PrintJob, PRINT_STATES  # noqa: F401
from printing_suite.objects.printing.PrintOutcome import PrintOutcome, OUTCOME_VERDICTS  # noqa: F401
from printing_suite.objects.printing.ProductionRun import ProductionRun, RUN_STEPS, RUN_STATES  # noqa: F401
from printing_suite.objects.printing.RunStepRecord import RunStepRecord  # noqa: F401

SUITE = 'printing-production'

SEED_PRINTING_SUITES = [{
    'name': SUITE, 'title': '3D printing — production', 'purpose': 'production 3D printing',
    'description': 'Everything needed to print parts for real (not the research stack): design (CAD → shape), material + mold, '
                   'slicing (Kiri:Moto), the printer (Klipper + Moonraker + Mainsail in a KVM guest), the hardware map that says '
                   'which device can host it, and the measured outcome that feeds the next profile.',
    'front_page': 'printing-suite', 'personas_json': '["maker", "shop operator"]'}]

SEED_PRINTING_PARTS = [
    {'name': SUITE + ':design', 'suite': SUITE, 'app': 'mathshapes', 'kind': 'polari-app', 'role': 'design', 'placement': 'core', 'required': True, 'order': 0,
     'notes': 'CAD import (ImportedCadObject) and math shapes — the shape rows a SliceJob names'},
    {'name': SUITE + ':material', 'suite': SUITE, 'app': 'materials_science', 'kind': 'polari-app', 'role': 'material', 'placement': 'core', 'required': True, 'order': 1,
     'notes': 'Material rows the PrintProfile derives from'},
    {'name': SUITE + ':mold', 'suite': SUITE, 'app': 'casting', 'kind': 'polari-app', 'role': 'mold', 'placement': 'core', 'required': False, 'order': 2,
     'notes': 'MoldDefinition / MoldNestingChain — a shape becomes a material-specific mold (with waxprint for wax feedstock)'},
    {'name': SUITE + ':map', 'suite': SUITE, 'app': 'hwmap', 'kind': 'polari-app', 'role': 'map', 'placement': 'core', 'required': True, 'order': 3,
     'notes': 'which device can take the printer guest (serial boards mapped)'},
    {'name': SUITE + ':slicer', 'suite': SUITE, 'app': 'kirimoto', 'kind': 'isle-app', 'role': 'slice', 'placement': 'any', 'required': True, 'order': 4,
     'notes': 'Kiri:Moto in a container behind the isle agent; consumes SliceJob, produces GcodeArtifact'},
    {'name': SUITE + ':printer', 'suite': SUITE, 'app': 'voron-printer', 'kind': 'hardware-app', 'role': 'control', 'placement': 'hardware', 'required': True, 'order': 5,
     'notes': 'the Voron as a hardware app; consumes GcodeArtifact via Moonraker, reports PrintJob state'},
    {'name': SUITE + ':measure', 'suite': SUITE, 'app': 'printing_suite', 'kind': 'polari-app', 'role': 'measure', 'placement': 'core', 'required': True, 'order': 6,
     'notes': 'PrintOutcome rows: the measured result, fed back to material/mold rows'},
    {'name': SUITE + ':network', 'suite': SUITE, 'app': 'isle-relay', 'kind': 'hardware-app', 'role': 'network', 'placement': 'hardware', 'required': False, 'order': 7,
     'notes': 'optional: a relay guest when the printer sits beyond the router'},
]

SEED_PRINTING_CONTRACTS = [
    {'name': SUITE + ':shape', 'suite': SUITE, 'object_class': 'ImportedCadObject', 'owner_module': 'mathshapes', 'producer': 'design', 'consumer': 'mold',
     'description': 'the imported CAD shape (also MathShapeDefinition) the mold and slice steps start from'},
    {'name': SUITE + ':mold', 'suite': SUITE, 'object_class': 'MoldDefinition', 'owner_module': 'casting', 'producer': 'mold', 'consumer': 'slicer',
     'description': 'a material-specific mold derived from the shape (the research stack\'s big result, reused as-is)'},
    {'name': SUITE + ':material', 'suite': SUITE, 'object_class': 'Material', 'owner_module': 'materials_science', 'producer': 'material', 'consumer': 'measure',
     'description': 'the material whose properties the profile derives from and the outcome feeds back into'},
    {'name': SUITE + ':lot', 'suite': SUITE, 'object_class': 'MaterialLot', 'owner_module': 'printing_suite', 'producer': 'material', 'consumer': 'printer',
     'description': 'the spool/batch actually loaded'},
    {'name': SUITE + ':profile', 'suite': SUITE, 'object_class': 'PrintProfile', 'owner_module': 'printing_suite', 'producer': 'material', 'consumer': 'slicer',
     'description': 'how this material prints on this printer — the slicer\'s inputs, derived not typed'},
    {'name': SUITE + ':slicejob', 'suite': SUITE, 'object_class': 'SliceJob', 'owner_module': 'printing_suite', 'producer': 'design', 'consumer': 'slicer',
     'description': 'shape + profile → a request the slicer fulfils'},
    {'name': SUITE + ':gcode', 'suite': SUITE, 'object_class': 'GcodeArtifact', 'owner_module': 'printing_suite', 'producer': 'slicer', 'consumer': 'printer',
     'description': 'the sliced file as a checksummed row (never a path handed around)'},
    {'name': SUITE + ':printjob', 'suite': SUITE, 'object_class': 'PrintJob', 'owner_module': 'printing_suite', 'producer': 'printer', 'consumer': 'measure',
     'description': 'the artifact on the printer, state from Moonraker'},
    {'name': SUITE + ':outcome', 'suite': SUITE, 'object_class': 'PrintOutcome', 'owner_module': 'printing_suite', 'producer': 'measure', 'consumer': 'material',
     'description': 'what came out, measured — feeds MoldLifecycleRecord / CastingRunRecord / material rows'},
    {'name': SUITE + ':printerstate', 'suite': SUITE, 'object_class': 'PrinterState', 'owner_module': 'voron', 'producer': 'printer', 'consumer': 'measure',
     'description': 'the printer\'s live state the PrintJob follows'},
    {'name': SUITE + ':candidates', 'suite': SUITE, 'object_class': 'PassthroughCandidate', 'owner_module': 'hwmap', 'producer': 'map', 'consumer': 'printer',
     'description': 'which port on which device can be handed to the printer guest'},
]

SEED_PRINT_PROFILES = [{'name': 'pla-generic@voron-2.4-350', 'material': 'PLA (generic)', 'printer': 'voron-2.4-350', 'slicer': 'kirimoto',
                        'nozzle_mm': 0.4, 'layer_mm': 0.2, 'nozzle_temp_c': 210.0, 'bed_temp_c': 60.0, 'speed_mm_s': 150.0, 'retraction_mm': 0.5,
                        'fan_pct': 100.0, 'infill_pct': 20.0, 'provenance': 'vendor datasheet range (cited); replace with derived values from Material rows',
                        'notes': 'the one example profile; sim-mode printer accepts it without moving'}]

PRINTING_SUITE_SEED_PAIRS = [('MaterialLot', MaterialLot, []), ('PrintProfile', PrintProfile, SEED_PRINT_PROFILES),
                             ('SliceJob', SliceJob, []), ('GcodeArtifact', GcodeArtifact, []), ('PrintJob', PrintJob, []),
                             ('PrintOutcome', PrintOutcome, []),
                             ('ProductionRun', ProductionRun, []), ('RunStepRecord', RunStepRecord, [])]
PRINTING_SUITE_CLASSES = [cls for _, cls, _ in PRINTING_SUITE_SEED_PAIRS]
