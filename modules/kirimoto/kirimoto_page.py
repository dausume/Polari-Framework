"""@module kirimoto.kirimoto_page — /display/kirimoto (tables + structured panel only)."""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_KIRIMOTO_PAGE_DISPLAYS = [
    _page('kirimoto', 'kirimoto',
          'Kiri:Moto: the browser slicer as an isle container app (kirimoto.isle), built from a pinned upstream commit; its device '
          'profiles per printer, and the slice jobs it takes from the printing suite.',
          'SlicerInstance',
          [_row(0, [_sapi('km-summary', 0, 12, 'Instance, pin state, build', '/api/kirimoto/summary', hide='profiles')]),
           _row(1, [_table('km-instances', 0, 5, 'Instances', 'SlicerInstance', columns='name,domain,upstream_commit,version,probe_ok,observed_at'),
                    _table('km-profiles', 1, 7, 'Device profiles', 'SlicerProfile', columns='name,printer,bed_x_mm,bed_y_mm,bed_z_mm,nozzle_mm,gcode_flavor')])]),
]
