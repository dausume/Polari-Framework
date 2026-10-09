"""
@module cmod.objects.cmod.HardwareBinding

HardwareBinding — one class per file (design §7); ucd-0b2b (UNO_CORE_DEMO_PLAN.md §5h, his ruling 2026-10-08).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class HardwareBinding(treeObject):
    """What it is: THE MASK THAT LAYS ONE `FirmwareSolution` OVER ONE BOARD (ucd-0b2b, his ruling 2026-10-08, verbatim:
    "Solutions should be separable from specific hardware, we should have hardware specific objects that are bindings
    or masks that bind to the solutions to combine into making a valid firmware, needing to meet the minimum
    requirements of the task for the hardware to be a valid target"). A `FirmwareSolution` is hardware-agnostic (its
    tasks and their `TargetDefinition` requirements); a `HardwareBinding` ('<solution>@<board>') OWNS the hardware-
    specific rows this solution produces on THIS board — the `RegisterAssignment` rows (re-keyed here by `configuration`
    = this binding's name), and through them the derived `PinClaim` / `PeripheralClaim` / `SignalRoute` /
    `RegisterSetting` / `RegisterFieldSetting` rows (`assignments_refs_json` / `claims_refs_json` / `settings_refs_json`
    / `routes_refs_json`, reverse links as 'Class:name' strings). `status` is computed from rows only
    (`cmod.custom.binding.validity`): valid (every required `TargetDefinition` row of the solution's graph is bound to
    a resource THIS board actually has, no conflict), incomplete (some unmet, or the board's own hardware chain is not
    materialized yet — never a crash), invalid (a conflict, or a bound resource the board lacks/cannot support) — `why`
    names every unmet/conflicting/incompatible requirement in plain words. ONE default binding is derived per seeded
    `FirmwareSolution` at boot, from its resolved board (`FirmwareSolution.board_definition`/`board_variable`) —
    `FirmwareSolution.board_definition` is now read as "the DEFAULT binding's board"; a person may add another
    binding (POST .../bindings, `provenance='canvas'`) to the SAME or a different board, kept (never converged away).
    A build/run/export takes a binding, not a bare solution; the API/CLI accept '<solution>' (its default binding) or
    '<solution>@<board>'.
    Related concepts: `FirmwareSolution`, `TargetDefinition`, `RegisterAssignment`, `PinClaim`, `PeripheralClaim`,
    board's `BoardDefinition`, `board.custom.target_compat.compatible`.
    """

    plain_words = ('A hardware binding lays one firmware solution over one board — whether that board meets every '
                   'task\'s minimum requirement to be a valid target, and why not when it does not.')

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', board: str = '', soc: str = '', is_default: bool = False,
                 status: str = 'incomplete', why: str = '', requirements_total: int = 0, requirements_met: int = 0,
                 assignments_refs_json: str = '[]', claims_refs_json: str = '[]', settings_refs_json: str = '[]',
                 routes_refs_json: str = '[]', last_build: str = '', provenance: str = 'derived', notes: str = '',
                 manager=None):
        self.name = name                        # '<solution>@<board>' ('uno-sim-rig@arduino-uno-r3')
        self.solution = solution                # the FirmwareSolution row
        self.board = board                      # the BoardDefinition row name
        self.soc = soc                          # the board's own SocDefinition name
        self.is_default = is_default            # True for the ONE converged default binding of this solution
        self.status = status                    # valid | incomplete | invalid
        self.why = why                          # plain words, every unmet/conflicting/incompatible requirement named
        self.requirements_total = requirements_total  # count of the solution graph's own required TargetDefinition rows
        self.requirements_met = requirements_met       # how many of those this binding's own assignments satisfy
        self.assignments_refs_json = assignments_refs_json  # ["RegisterAssignment:…", …] of THIS binding
        self.claims_refs_json = claims_refs_json            # ["PinClaim:…"/"PeripheralClaim:…", …]
        self.settings_refs_json = settings_refs_json        # ["RegisterSetting:…"/"RegisterFieldSetting:…", …]
        self.routes_refs_json = routes_refs_json            # ["SignalRoute:…", …]
        self.last_build = last_build            # the FirmwareBuild/CGlueBuild this binding last produced
        self.provenance = provenance            # derived (the converged default) | canvas (a person added it — kept)
        self.notes = notes
