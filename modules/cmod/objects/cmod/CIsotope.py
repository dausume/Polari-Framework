"""
@module cmod.objects.cmod.CIsotope

CIsotope — one class per file (design §7); ucd-iso-0 (His ruling 2026-10-10, AI-Notes/plans/UNO_CORE_DEMO_PLAN.md
"the C-atom's CODE INTERFACE and C-ISOTOPES"): a NAMED VARIANT of a `CFunctionAtom`, already carrying the C text
for one datasheet-bound binding (or, for a FOUNDATIONAL isotope, for one runtime/RTOS level with no bare-C parent at
all). His words: "C-isotopes should only have the substitutions needed for their board and other datasheet
properties and inherit general structure from their parent."
"""
from objectTreeDecorators import treeObject, treeObjectInit


class CIsotope(treeObject):
    """What it is: one C-isotope of a `CFunctionAtom` — the parent's own function TEXT with ONLY its binding-
    dependent identifiers (declared pin macros, programming-reference knobs) substituted to this binding's resolved
    values; a register identifier is never substituted (its value is SoC-fixed, not binding-dependent). `bindings_json`
    names which of the three datasheet kinds (soc | board | programming) this isotope actually draws on — at least
    one, never all three required (his ruling: "not necessarily all three data-sheet section bindings, but at least
    one binding out of three"). `minimum_level` is this isotope's own place on the runtime ladder
    (`cmod.custom.code_interface.LEVEL_ORDER` — bare-c < freertos < esp-idf < zephyr): every isotope DERIVED from a
    bare-C UNO atom is 'bare-c'; a FOUNDATIONAL isotope (`foundational=True`) has no bare-C parent body at all — it
    is authored directly against a higher-level runtime (a FreeRTOS task, say) and carries that runtime's own name
    here, so selecting it on a binding whose runtime is lower on the ladder is refused BY NAME
    (`cmod.custom.code_interface.level_ok`).
    Related concepts: `CFunctionAtom`, `HardwareBinding`, `hwnocode.custom.runtimes` (where c-device/c-twin code
    actually executes — a DIFFERENT axis from this one, which runtime/RTOS level an isotope needs at minimum).
    """

    plain_words = ('A C-isotope is one ready-to-read variant of a C building block — the same function, with its '
                   'board/datasheet-specific values already filled in, and the minimum OS level it needs to run.')

    @treeObjectInit
    def __init__(self, name: str = '', parent: str = '', project: str = '', bindings_json: str = '{}',
                 substitutions_json: str = '[]', source: str = '', minimum_level: str = 'bare-c', sha256: str = '',
                 foundational: bool = False, provenance: str = 'derived', notes: str = '', manager=None):
        self.name = name                              # '<atom>@<binding>' (derived) | '<atom-or-authored-name>@<datasheet-set>' (foundational)
        self.parent = parent                          # the CFunctionAtom row name this isotope is a variant of ('' for a foundational one authored by hand)
        self.project = project
        self.bindings_json = bindings_json             # {soc, board, programming} -> Datasheet slug, >=1 non-empty
        self.substitutions_json = substitutions_json   # [{identifier, value, datasheet_kind, datasheet, fact}, ...]
        self.source = source                           # the parent's text with ONLY those substitutions applied (structure inherited)
        self.minimum_level = minimum_level              # bare-c | freertos | esp-idf | zephyr (cmod.custom.code_interface.LEVEL_ORDER)
        self.sha256 = sha256                            # of `source` — stable across re-derivation (the idempotence proof)
        self.foundational = foundational                # True: no bare-C parent body — authored directly at `minimum_level`
        self.provenance = provenance                    # derived (code_interface.render, per atom x HardwareBinding) | authored (foundational example)
        self.notes = notes
