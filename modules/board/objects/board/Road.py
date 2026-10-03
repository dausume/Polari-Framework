"""
@module board.objects.board.Road

Road — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Road(treeObject):
    """What it is: The road for ONE tracked device (plan §8a: track all, simulate few): the ordered steps (datasheet facts ->
    definition complete -> twin -> firmware template -> flashed on real hardware -> measured), each todo |
    in-progress | done, and the road's status. It hangs on the 'board-roads' tech tree as one concept node
    (techtree TechNode carries no status, so the status lives here).
    Related concepts: `BoardDefinition.road`, techtree `TechNode` (concept_node).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', status: str = 'todo', steps_json: str = '[]',
                 concept_node: str = '', notes: str = '', manager=None):
        self.name = name  # 'road-<board>'
        self.board = board
        self.status = status  # todo | in-progress | done
        self.steps_json = steps_json  # [{step, status, note}]
        self.concept_node = concept_node  # the TechNode name on board-roads
        self.notes = notes
