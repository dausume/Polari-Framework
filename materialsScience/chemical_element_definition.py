"""
@cross-cutting
@module materialsScience.chemical_element_definition
@tags @xc:bindings

A CHEMICAL ELEMENT as a first-class Polari object — the object-tree
home the periodic-table selection space (and everything the Materials
Science Module builds later) hangs off. One row per element; common
ions ride along so a selection can be an ELEMENT or a specific ION of
it.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - materialsScience.periodic_table_seed (118 rows + the selector scene)
  - frontend element-choice overlay/popup (ion selection)
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ChemicalElementDefinition(treeObject):
    @treeObjectInit
    def __init__(
        self,
        # Identity: the symbol is the human-stable name ('Fe').
        name: str = '',
        symbol: str = '',
        element_name: str = '',
        atomic_number: int = 0,
        # Standard-table placement (group_number 1-18 — 'group' is an SQL
        # reserved word, hence the suffix; lanthanides/actinides
        # carry their nominal group 3 — display_row/display_col below
        # give the visual f-block position).
        group_number: int = 0,
        period: int = 0,
        display_row: float = 0.0,
        display_col: float = 0.0,
        # Category drives the selector's color coding ('alkali-metal',
        # 'transition-metal', 'noble-gas', …).
        category: str = '',
        # Common ions as display labels, e.g. ["Fe2+", "Fe3+"] — the
        # ion-selection choices. '[]' = no common ionic forms.
        common_ions_json: str = '[]',
        # Standard atomic weight (0 = no stable value).
        atomic_mass: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.symbol = symbol
        self.element_name = element_name
        self.atomic_number = atomic_number
        self.group_number = group_number
        self.period = period
        self.display_row = display_row
        self.display_col = display_col
        self.category = category
        self.common_ions_json = common_ions_json
        self.atomic_mass = atomic_mass
