"""
@module firmwarefaults.objects.firmwarefaults.ScenarioStep

ScenarioStep — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ScenarioStep(treeObject):
    """What it is: One forcing step of a Scenario, in order (FIRMWARE_SCENARIO_PLAN.md §1): its kind
    (irq-at-pc | irq-at-cycle | corrupt-word | drop-nth-frame | flip-bit-at-cycle | uart-ber | hold-lock-order |
    clock-skew), its arguments (a PC as a SYMBOL plus a disassembly pattern, resolved against each build's ELF so a
    rebuild re-resolves the address; a vector; an address; a value; a cycle) and the condition that must hold when it
    fires. `forcible` says whether the harness can do this kind today; when not, `not_forcible_reason` says why.
    Related concepts: `Scenario`, the harness flags of polari-avr-twin (prf-board-engines/twin_forcing.c).
    """

    plain_words = ('A scenario step is one action in a bug-forcing recipe, such as "fire the timer interrupt right after '
                   'this instruction" or "change this memory word at this moment".')

    @treeObjectInit
    def __init__(self, name: str = '', scenario: str = '', position: int = 0, kind: str = '', args_json: str = '{}',
                 condition_json: str = '{}', forcible: bool = True, not_forcible_reason: str = '', notes: str = '', manager=None):
        self.name = name
        self.scenario = scenario  # the Scenario name
        # fw-2: named `position`, not `order` — `order` is a SQLite reserved word and broke
        # CREATE TABLE for this class ('near "order": syntax error'); rows never persisted.
        self.position = position
        self.kind = kind  # irq-at-pc | irq-at-cycle | corrupt-word | drop-nth-frame | flip-bit-at-cycle | uart-ber | hold-lock-order | clock-skew
        self.args_json = args_json  # {symbol, pattern, vec, addr, value, cycle, p, n}
        self.condition_json = condition_json  # {symbol, width, mask, value} — e.g. g_ms & 0xFF == 0xFF
        self.forcible = forcible  # the harness supports this kind now
        self.not_forcible_reason = not_forcible_reason
        self.notes = notes
