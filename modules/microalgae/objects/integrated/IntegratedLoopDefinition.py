"""
@module microalgae.objects.integrated.IntegratedLoopDefinition

Row class IntegratedLoopDefinition of the microalgae module — one class per file (design §7), split
from integrated_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
