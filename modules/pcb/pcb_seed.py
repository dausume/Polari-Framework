"""
@module pcb.pcb_seed

THE FAB RULES AS ROWS (pcb-0, plan §2 FabProfile/FabRule): DKRed's constraints (pcb.custom.fab_rules, cited from
https://www.digikey.com/en/resources/dkred) are the only CODE-OWNED seed — the fab does not change per server. Every
other class (Part, Symbol, Footprint, LandPattern, Schematic/SchematicSheet, PcbBoard, Placement, Route, DrcResult,
FabricationExport) is OBSERVED — written by `pol pcb ingest` or the schematic writer, never seeded, because a board is a
design someone made, not a fact about the world.
"""
from pcb.pcb_basis import FabRuleSet, FabRule, Part, Symbol, Footprint, LandPattern, Schematic, SchematicSheet, PcbBoard, \
    Placement, Route, DrcResult, FabricationExport
from pcb.custom import fab_rules as FR


def _register_owned(rows):
    """DKRed's rules are code-owned (re-read the page, the rows follow) — the instance never gets to keep a stale value."""
    return [dict(r, _converge=[k for k in r if k != 'name']) for r in rows]


PCB_SEED_PAIRS = [
    ('FabRuleSet', FabRuleSet, _register_owned(FR.rule_set_rows())),
    ('FabRule', FabRule, _register_owned(FR.rule_rows())),
    # observed, never seeded:
    ('Part', Part, []),
    ('Symbol', Symbol, []),
    ('Footprint', Footprint, []),
    ('LandPattern', LandPattern, []),
    ('Schematic', Schematic, []),
    ('SchematicSheet', SchematicSheet, []),
    ('PcbBoard', PcbBoard, []),
    ('Placement', Placement, []),
    ('Route', Route, []),
    ('DrcResult', DrcResult, []),
    ('FabricationExport', FabricationExport, []),
]
