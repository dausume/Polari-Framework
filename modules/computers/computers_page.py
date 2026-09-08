"""
@module computers.computers_page

cmp-c-4: the /display/computers page as PURE DATA — rows of the
two generic registered components only (class-rows-table /
api-structured-panel: tables and chips, never a JSON wall), so this
page costs a seed row and zero Angular work. Detail panels point at
the seeded assemblies; repoint by editing the Display row — a knob,
not code. Each panel `pick`s the one record list that is its point
(gate rows, fit verdicts, port nodes) so nothing lands in the
structured panel's JSON expander.
"""

from polariApiServer.module_pages_seed import (
    _page, _row, _sapi, _table,
)

SEED_COMPUTERS_PAGE_DISPLAYS = [
    _page(
        'computers-home', 'computers',
        'Computers: the component taxonomy (declared specs + '
        'honest gaps), the parts catalog with dated prices, '
        'assembly gate reports, and use-case profile fits.',
        'ComputerAssemblyDefinition',
        [
            _row(0, [
                _table('computers-taxonomy', 0, 6,
                       'Component taxonomy (cmp-c-1)',
                       'ComputerPartClassDefinition',
                       columns='name,display_name,summary,'
                               'gaps_note'),
                _table('computers-profiles', 1, 6,
                       'Use-case profiles (data rows)',
                       'ComputerProfileDefinition',
                       columns='name,display_name,use_case,'
                               'planner_class,db_binding'),
            ]),
            _row(1, [
                # the taxonomy + profiles already sit in row 0 as
                # class tables; the catalog's OWN contribution is the
                # assembly list (fit verdicts per assembly: row 2).
                _sapi('computers-catalog', 0, 4,
                      'Assemblies (catalog)', '/api/computers',
                      pick='assemblies'),
                _sapi('computers-parts', 1, 4,
                      'Parts (dated prices, ai-8)',
                      '/api/computerparts', pick='parts'),
                _sapi('computers-builds', 2, 4,
                      'Builds (total USD, oldest price date)',
                      '/api/computerparts', pick='builds'),
            ]),
            _row(2, [
                _sapi('computers-assembly-xeon', 0, 6,
                      'Gate report — owned Xeon 6338N assembly '
                      '(check / verdict / detail)',
                      '/api/computers/assembly/'
                      'assembly-xeon-6338n', pick='gateReport.gates'),
                _sapi('computers-fit-xeon-db', 1, 6,
                      'Fit — Xeon assembly vs DB-bound profile '
                      '(floor by floor)',
                      '/api/computers/fit/assembly-xeon-6338n/'
                      'profile-db-bound-storage', pick='fit.verdicts'),
            ]),
            # cmp-c-6: interconnects as data — the vocabulary rows
            # + the owned build's port matrix (the workbench's
            # data feed, visible before the visual UI lands).
            _row(3, [
                _table('computers-interconnects', 0, 6,
                       'Interconnect vocabulary (cmp-c-6)',
                       'InterconnectDefinition',
                       columns='name,display_name,kind,carries,'
                               'attachment,summary'),
                _sapi('computers-port-matrix', 1, 6,
                      'Port matrix — owned Xeon build: one row per '
                      'part (declared = False names the undeclared '
                      'ports honestly)',
                      '/api/computers/interconnects/build/'
                      'build-xeon-6338n', pick='matrix.nodes'),
            ]),
        ]),
]
