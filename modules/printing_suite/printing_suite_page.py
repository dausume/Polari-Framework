"""@module printing_suite.printing_suite_page — /display/printing-suite: the suite front page (tables + structured panels only)."""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_PRINTING_SUITE_PAGE_DISPLAYS = [
    _page('printing-suite', 'printing-suite',
          '3D printing, production: the suite app that bundles design (CAD → shape), material + mold, slicing (Kiri:Moto), the printer '
          '(Klipper in a KVM guest), the hardware map and the measured outcome. Every hand-off between parts is a row: shape → mold → '
          'profile → slice job → gcode artifact → print job → outcome.',
          'PrintJob',
          [_row(0, [_sapi('ps-pipeline', 0, 6, 'Pipeline (row counts per step)', '/api/printing-suite/summary', pick='pipeline'),
                    _sapi('ps-placement', 1, 6, 'Where the parts run', '/api/suiteapps/printing-production', pick='parts')]),
           _row(1, [_table('ps-profiles', 0, 6, 'Print profiles', 'PrintProfile', columns='name,material,printer,slicer,nozzle_mm,layer_mm,nozzle_temp_c,bed_temp_c,provenance'),
                    _table('ps-lots', 1, 6, 'Material lots', 'MaterialLot', columns='name,material,form,diameter_mm,mass_g,vendor,location')]),
           _row(2, [_table('ps-slice', 0, 4, 'Slice jobs', 'SliceJob', columns='name,shape_class,shape,profile,slicer,state'),
                    _table('ps-gcode', 1, 4, 'Gcode artifacts', 'GcodeArtifact', columns='name,slice_job,sha256,bytes,estimated_seconds'),
                    _table('ps-jobs', 2, 4, 'Print jobs', 'PrintJob', columns='name,artifact,printer,state,progress_pct')]),
           _row(3, [_table('ps-outcomes', 0, 12, 'Outcomes (measured)', 'PrintOutcome', columns='name,print_job,verdict,actual_seconds,actual_material_g,defects_json,measured_by,method,feeds_back_to')])]),
]
