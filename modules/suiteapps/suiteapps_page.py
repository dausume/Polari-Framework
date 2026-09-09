"""@module suiteapps.suiteapps_page — /display/suite-apps: suites, parts, contracts, placements (tables + structured panel)."""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_SUITEAPPS_PAGE_DISPLAYS = [
    _page('suite-apps', 'suite-apps',
          'Suite apps: purpose-oriented compositions of apps of every kind (Polari modules, isle containers, hardware KVM guests, '
          'extension apps) with the object contracts their parts pass through Polari and a placement plan across devices — the '
          'layer above a single app, for purposes too big for one computer.',
          'SuiteAppDefinition',
          [_row(0, [_sapi('suites-summary', 0, 12, 'Suites + placement summary', '/api/suiteapps', pick='suites')]),
           _row(1, [_table('suite-parts', 0, 7, 'Parts', 'SuitePart', columns='suite,app,kind,role,placement,required,order'),
                    _table('suite-contracts', 1, 5, 'Contracts (objects passed between parts)', 'SuiteContract', columns='suite,object_class,owner_module,producer,consumer')]),
           _row(2, [_table('suite-placements', 0, 12, 'Placement (computed)', 'SuitePlacement', columns='suite,part,device,verdict,reason,computed_at')])]),
]
