"""
@module cmod.cmod_isotope_page

/display/isotope-variants (iso-0): every way a C atom's job can be done, as configured tables only (no raw JSON, no new component). Three tables read
the variant doors: the jobs, the variants on the Arduino UNO (status, eligibility, costs, parts) and the same on the modelled ESP32-C3.
"""
from polariApiServer.module_pages_seed import _page, _row, _table

_UNO = 'arduino-uno-r3'
_C3 = 'esp32-c3'
_COLS = 'job,route,title,status,eligible,eligible_why,minimum_level,pins_text,peripherals_text,parts_text,cost_flash_bytes,cost_ram_bytes,cost_stack_bytes,cost_cpu_share,cost_latency,wastefulness_note,status_why'
_WHAT = ('One row = one variant: one way to do one job. Columns: status (how far the route has got: declared, template-exists, compiles, proven-on-twin, proven-on-hardware - read off the '
         'atoms, builds and test runs that exist), eligible (ok, blocked or undetermined on that board, with the reason by name), minimum_level (the lowest runtime tier it runs at), '
         'pins_text / peripherals_text / parts_text (what it needs; a part is marked when it is NOT on the bench), cost_* (each value says measured, estimated or undetermined), '
         'wastefulness_note (when it is a poor default and when it is the only route left).')

ISOTOPE_PAGES = [
    _page('isotope-variants', 'isotope-variants',
          'Isotope variants - every way a C atom\'s job can be done. A job such as "read the button" can be done by watching the pin, by an interrupt, through a shift register and more; '
          'each way is a variant with the pins, chip blocks and extra parts it needs, what it costs and how far it has got. A wasteful way is listed, not hidden: it is simply scored worse, '
          'and can be the only way left when everything better is taken. Status is read off what exists, never typed. From the command line: python3 -m cmod.custom.isotope_variants '
          'variants read-button --board arduino-uno-r3. The doors: GET /api/atom-jobs and GET /api/atom-jobs/<job>/variants?board=.',
          'IsotopeVariant', [
              _row(0, [_table('iso-jobs', 0, 12, 'Jobs - what a C atom has to do, said without any hardware', 'AtomJob',
                              description='What this is for: the questions the variants answer. One row = one job. Columns: direction (in = the world to the firmware, out = the firmware to the world, '
                                          'transport), purposes (which Purposes need it), atoms (the existing atoms that do it, from the seed and found by the pin macro they declare), '
                                          'variant_count / implemented_count (how many routes exist, how many have an atom), best_status.',
                              columns='name,title,direction,plain,purposes,atoms,variant_count,implemented_count,best_status,routes',
                              data_path='/api/atom-jobs')], min_height=220),
              _row(1, [_table('iso-variants-uno', 0, 12, 'Variants on the Arduino UNO (ATmega328P, the bench kit)', 'IsotopeVariant', description=_WHAT, columns=_COLS,
                              data_path='/api/atom-variants?board=%s' % _UNO)], min_height=520),
              _row(2, [_table('iso-variants-c3', 0, 12, 'The same variants on the modelled ESP32-C3 (its pin routing is not modelled, so many are undetermined)', 'IsotopeVariant',
                              description=_WHAT, columns=_COLS, data_path='/api/atom-variants?board=%s' % _C3)], min_height=520),
          ]),
]
