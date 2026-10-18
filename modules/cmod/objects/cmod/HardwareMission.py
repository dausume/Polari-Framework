"""
@module cmod.objects.cmod.HardwareMission

HardwareMission - one class per file (design section 7). MISSION_PROFILE_SOLVER_PLAN.md sections 2.1 / 5 / 7 and
SYSTEM_HIERARCHY_TERMINOLOGY.md sections 8-13 (mis-0).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareMission(treeObject):
    """What it is: a HARDWARE MISSION - the why one level above a Purpose: one goal, the Purposes that serve it (each with an
    importance), the participants (hardware, software, people) that take part by role, the settings the solution search aims at
    (`objective`: minimum-resources | fastest-cycle) and the constraints any solution must respect (hardware stage, allowed boards).
    The row is the source of truth for everything a person decides. Whether the Mission can be done with the real bound hardware
    (`resolution`) and each Purpose's own status are DERIVED when asked (`cmod.custom.mission_derived`) and have NO field here, on purpose.
    Related concepts: `CapabilityDefinition` (a Purpose), `cmod.custom.mission_nocode` (the Mission drawn as no-code),
    `HardwareSystem` (the stage vocabulary).
    """

    plain_words = ('A Hardware Mission is the reason a piece of hardware exists: one goal, the Purposes that serve it and how much each '
                   'matters, who and what takes part, what the solution should aim at (the fewest resources, or the fastest pass through '
                   'every Purpose) and the limits it must stay inside.')

    LIFECYCLES = ('draft', 'enabled', 'suspended', 'retired')
    IMPORTANCES = ('safety', 'required', 'important', 'desired')   # decided 2026-10-17 (plan section 7)
    OBJECTIVES = ('minimum-resources', 'fastest-cycle')
    PARTICIPANT_KINDS = ('hardware', 'software', 'person')
    STAGES = ('S1-breadboard', 'S2-protoboard', 'S3-pcb', 'S4-vendor-soc', 'S5-blcnc-soc')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', goal: str = '', purposes_json: str = '[]', participants_json: str = '[]',
                 settings_json: str = '{"objective": "minimum-resources"}', constraints_json: str = '{}', lifecycle: str = 'enabled',
                 notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.goal = goal                            # ONE sentence, a person's words
        self.purposes_json = purposes_json          # [{purpose: <CapabilityDefinition name>, importance: safety|required|important|desired}]
        self.participants_json = participants_json  # [{role, kind: hardware|software|person, ref, variant}]
        self.settings_json = settings_json          # {objective: minimum-resources | fastest-cycle, notes}
        self.constraints_json = constraints_json    # {stage: S1-breadboard..S5-blcnc-soc (optional), allowed_boards: [board names] (optional)}
        self.lifecycle = lifecycle                  # draft | enabled | suspended | retired - STORED, a person's/seed's word
        self.notes = notes
