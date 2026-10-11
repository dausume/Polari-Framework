"""
@module uno_core_demo.uno_core_demo_page

/display/uno-core-demo-readiness — ucd-2 (UNO_CORE_DEMO_PLAN.md §2), re-pointed at the light test by ucd-light: ONE configured table of DemoReadiness rows
(his rule: no raw JSON on screens, no new component) — a `refs` column ('Class:name', class-rows-table.component.ts
's refs format — `ref_name:ref:<Class>` cannot be one class per column since the six parts each name a different
class) links straight to the part's own detail object; the description names the three parts his ask combines
(firmware, bridge, Polari app) and links to the pages that show them traversed (UNO_CORE_DEMO_PLAN.md §3's
traversal rule).
"""
from polariApiServer.module_pages_seed import _page, _row, _table

ROUTE = 'uno-core-demo-readiness'

SEED_UNO_CORE_DEMO_PAGE_DISPLAYS = [
    _page(ROUTE, ROUTE,
          'Is the light test ready? The test needs five things to be in place: the firmware that runs on the board, the serial '
          'link that carries the light\'s state up and the on/off command down, the cross-domain solution that ties them '
          'together, and the two Purposes that say what the test is for (the screen turns the light on and off, and the '
          'board\'s button turns it on and off). Each row below says whether that thing exists, how far it has been proven, '
          'and why; the last row (composition) is only as good as the weakest of them. The light itself is on '
          '/display/uno-core-demo.',
          'DemoReadiness', [
              _row(0, [_table('ucd-readiness', 0, 12,
                              'What the light test needs, and whether each part is ready', 'DemoReadiness',
                              description='One row for each thing the test needs: part names which one, refs opens it, '
                                          'exists says whether it is there, status says how far it has got, why says it in words, '
                                          'and checked_at says when this was last worked out. The composition row at the bottom '
                                          'is the weakest of the rest.',
                              columns='part,refs,exists,status,why,checked_at',
                              column_formats='refs:refs')], min_height=320),
          ]),
]
