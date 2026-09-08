"""
@cross-cutting
@module microalgae.integrated_basis
@tags @xc:bindings

algae-2 — IntegratedLoopDefinition: an ecosystem designed AROUND the
algae reactor (Dustin). A source system carries a MODEST designed
nitrogen surplus; one or more reactors are sized to consume exactly that
surplus while fixing CO2, so the composite nets to balance.

The coherent design has TWO requirements, not one:
  1. BALANCED  — composite net N ≈ 0 with the reactor running.
  2. RESILIENT — the base surplus (without the reactor) is small enough
                 that the passive regulators (macroalgae + substrate
                 denitrification + harvest) hold it if the reactor goes
                 offline. A design that only balances BECAUSE a large
                 excess is being drained by the reactor is fragile
                 ('reactor-load-bearing') — it spikes toxic if the
                 reactor hiccups, violating the self-sustaining ethos.
The reactor is a decarbonization + fine-regulation LAYER on a base that
nearly self-balances — not the load-bearing balance mechanism. The
reactors' biochar draw caps guarantee they can never over-pull the base.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - microalgae.custom.integrated_analysis (chained_balance)
@see /SALTWATER_FOOD_FOREST_SPEC.md, tanks/, [[microalgae-reactors]]
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Two design starting points, same underlying balance+resilience model:
#:   'reactor-first' — design the ecosystem AROUND a target reactor:
#:                     size the base surplus (fish stocking) to feed it.
#:   'add-on'        — add a reactor to an already-balanced forest:
#:                     introduce a modest HEADROOM surplus for it to eat.
DESIGN_MODES = ('reactor-first', 'add-on')


class IntegratedLoopDefinition(treeObject):
    """An excess-source + algae-reactor chain, balanced as a whole."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('excess-fish-algae-loop').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # DESIGN_MODES entry — which end you start from (tailors the
        # sizing recommendation; the verdict logic is shared).
        design_mode: str = 'reactor-first',
        # The excess-PRODUCING systems (TankSystemDefinition names) —
        # the "excess fish tanks" that accumulate nitrogen by design.
        source_system_names_json: str = '[]',
        # How the source surplus is resolved ('tank' → live net-N
        # balance; else the reactors' assumed knobs).
        source_kind: str = 'tank',
        # The CONSUMING algae reactors (AlgaeReactorDefinition names)
        # that draw the shared excess pool + fix CO2.
        reactor_names_json: str = '[]',
        # Persisted chained-balance snapshot (JSON) for scoring.
        loop_result_json: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.design_mode = design_mode
        self.source_system_names_json = source_system_names_json
        self.source_kind = source_kind
        self.reactor_names_json = reactor_names_json
        self.loop_result_json = loop_result_json
        self.provenance_id = provenance_id
        self.notes = notes
