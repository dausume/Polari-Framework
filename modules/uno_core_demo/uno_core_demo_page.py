"""
@module uno_core_demo.uno_core_demo_page

/display/uno-core-demo-readiness — ucd-2 (UNO_CORE_DEMO_PLAN.md §2): ONE configured table of DemoReadiness rows
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
          'The UNO core demo\'s readiness (ucd-2): is the whole composition — a bare-bones proof that a Polari '
          'Hardware App, its Polari app component and its Firmware Solution talk to one another — actually there? '
          'Six parts, each in its own no-code kind: firmware (the FirmwareSolution `uno-button-clock`, C tasks on '
          'the board), bridge (the `button-clock` HardwareBridgeDefinition — a Hardware Bridge App\'s proven, or '
          'never-run, BridgingCapability), polari_app (the backend solution `button-clock-ledger` + '
          '/display/uno-core-demo), cross_domain (the Cross-Domain Solution `uno-button-clock` composing all of '
          'it), circuit (the breadboard, `CircuitDefinition uno-button-clock`), and purpose (the Purpose '
          '`button-clock-to-os`). One row per part names what it points at (exists/status/why), and a seventh row, '
          'composition, carries the WEAKEST of the six — the demo is only as ready as its least-ready part, never '
          'a hand-set claim. Traverse to /display/uno-core-demo (the demo\'s own data), /display/firmware (the '
          'Firmware Run detail) and /display/hardware-chain (the Bridge/wire-contract detail).',
          'DemoReadiness', [
              _row(0, [_table('ucd-readiness', 0, 12,
                              'Every composed part of the UNO core demo, DERIVED fresh on every GET of '
                              '/api/uno-core-demo/readiness — never seeded with a claim.', 'DemoReadiness',
                              description='What this is for: one row per part (firmware, bridge, polari_app, '
                                          'cross_domain, circuit, purpose) plus one composition row carrying the '
                                          'weakest of the six. Columns: part (which of the six, or composition), '
                                          'refs (links to the row this part names), exists (is it actually there), '
                                          'status (the part\'s own status word), why (plain words, always), '
                                          'checked_at.',
                              columns='part,refs,exists,status,why,checked_at',
                              column_formats='refs:refs')], min_height=320),
          ]),
]
