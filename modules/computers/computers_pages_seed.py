"""
@module computers.computers_pages_seed

cmp-c-4: the /display/computers page as PURE DATA — rows of the
two generic registered components only (class-rows-table /
api-json-panel), so this page costs a seed row and zero Angular
work. Detail panels point at the seeded assemblies; repoint by
editing the Display row — a knob, not code.
"""

from polariApiServer.module_pages_seed import (
    _api, _page, _row, _table,
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
                _api('computers-catalog', 0, 6,
                     'Catalog + fit matrix', '/api/computers'),
                _api('computers-parts', 1, 6,
                     'Parts + builds (dated prices, ai-8)',
                     '/api/computerparts'),
            ]),
            _row(2, [
                _api('computers-assembly-xeon', 0, 6,
                     'Gate report — owned Xeon 6338N assembly',
                     '/api/computers/assembly/'
                     'assembly-xeon-6338n'),
                _api('computers-fit-xeon-db', 1, 6,
                     'Fit — Xeon assembly vs DB-bound profile',
                     '/api/computers/fit/assembly-xeon-6338n/'
                     'profile-db-bound-storage'),
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
                _api('computers-port-matrix', 1, 6,
                     'Port matrix — owned Xeon build '
                     '(undeclared parts named honestly)',
                     '/api/computers/interconnects/build/'
                     'build-xeon-6338n'),
            ]),
        ]),
]
