"""
@module pcb.objects.pcb.FabRuleSet

FabRuleSet — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FabRuleSet(treeObject):
    """What it is: A FAB's constraints as a set (plan §2 `FabProfile`): the fab, its page (cited, retrieved on a date), and
    the file names it accepts per layer — the rules themselves are FabRule rows. DKRed (DigiKey's fab service) first.
    """

    @treeObjectInit
    def __init__(self, name: str = '', fab: str = '', title: str = '', url: str = '', retrieved: str = '',
                 accepted_extensions_json: str = '{}', discrepancies: str = '', notes: str = '', manager=None):
        self.name = name
        self.fab = fab
        self.title = title
        self.url = url
        self.retrieved = retrieved
        self.accepted_extensions_json = accepted_extensions_json  # {layer kind: [extensions]}
        self.discrepancies = discrepancies  # what the page and the upload form disagree on (settled at the first upload)
        self.notes = notes
