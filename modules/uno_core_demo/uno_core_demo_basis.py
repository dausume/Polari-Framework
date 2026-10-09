"""
@module uno_core_demo.uno_core_demo_basis

The INDEX of uno_core_demo rows (design §7): DemoReadiness, one per composed part of the UNO core demo
(UNO_CORE_DEMO_PLAN.md §3). No rows are seeded here — every DemoReadiness row is DERIVED and upserted on request by
`GET /api/uno-core-demo/readiness` (`uno_core_demo.custom.readiness.readiness`), never a claim typed in at boot.
"""
from uno_core_demo.objects.uno_core_demo.DemoReadiness import DemoReadiness, PARTS  # noqa: F401

UNO_CORE_DEMO_SEED_PAIRS = [('DemoReadiness', DemoReadiness, [])]
UNO_CORE_DEMO_CLASSES = [cls for _, cls, _ in UNO_CORE_DEMO_SEED_PAIRS]
