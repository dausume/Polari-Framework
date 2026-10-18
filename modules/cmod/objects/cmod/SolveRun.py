"""
@module cmod.objects.cmod.SolveRun

SolveRun - one class per file (design section 7). MISSION_PROFILE_SOLVER_PLAN.md sections 2.5 / 8.4 (sol-0).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SolveRun(treeObject):
    """What it is: one RUN of the attempt engine on a Hardware Mission - the record that makes the search reproducible (the reproducible-initial-conditions rule). It keeps the
    INPUTS by sha256 (the Mission row, the pin profiles, the isotope variants, the overlap table, the ladder rule files, the board rows, the tiers, the knobs, the tool
    versions), the objective and limits it ran with, a summary of EVERY candidate it found, the chosen candidate in full, what was pruned and why, and how long it took.
    The same inputs give the same candidates in the same order, so `result_sha256` is checked by a replay. The row never holds a score without its inputs.
    Related concepts: `HardwareMission` (what was solved), `IsotopeVariant` (what was chosen between), `firmwarefaults.ScenarioRun` (the same habit for a simulated run).
    """

    plain_words = ('A solve run is one attempt by the search to place a Mission on real hardware: what it was given (each input fingerprinted), what it found, '
                   'which plan it chose and why the others lost, so anyone can run it again and get the same answer.')

    @treeObjectInit
    def __init__(self, name: str = '', mission: str = '', objective: str = '', secondary_objective: str = '', inputs_json: str = '{}', inputs_sha256: str = '',
                 limits_json: str = '{}', boards_json: str = '[]', tiers_json: str = '[]', candidates_json: str = '[]', candidate_count: int = 0, chosen: str = '',
                 chosen_json: str = '{}', designed_for_json: str = '{}', pruned_json: str = '{}', counts_json: str = '{}', result_sha256: str = '', solver_version: str = '',
                 duration_s: float = 0.0, ran_at: str = '', who: str = '', status: str = 'complete', notes: str = '', manager=None):
        self.name = name                          # '<mission>:<result sha 10>:<n>'
        self.mission = mission                    # the HardwareMission name
        self.objective = objective                # minimum-resources | fastest-cycle (the one the ranking used)
        self.secondary_objective = secondary_objective
        self.inputs_json = inputs_json            # {mission_row, profiles, variants, overlap_table, ladder_rules {file: sha256}, boards {board: sha256}, kit, tiers, limits, tool_versions}
        self.inputs_sha256 = inputs_sha256        # sha256 of inputs_json
        self.limits_json = limits_json            # the knobs the run used (max_candidates, occupied, prefer, weights ...)
        self.boards_json = boards_json            # the boards asked for ([] = the default set)
        self.tiers_json = tiers_json              # the tiers asked for ([] = every tier the board offers)
        self.candidates_json = candidates_json    # a summary of every candidate: [{id, rank, hardware, tier, routes, pins, placement, resource_score, cycle_us, parts_missing}]
        self.candidate_count = candidate_count
        self.chosen = chosen                      # the winning candidate's id ('' = none could be placed)
        self.chosen_json = chosen_json            # the winning candidate in full (assignment with a reason per pin, score breakdown, risks)
        self.designed_for_json = designed_for_json  # the Task Plan's origin context + 'also runs on' (resolver-valid until proven)
        self.pruned_json = pruned_json            # {total, by_kind: {kind: {count, first: [{where, reason}]}}}
        self.counts_json = counts_json
        self.result_sha256 = result_sha256        # sha256 of the candidates + ranking + pruned log (not the clock): a replay must reproduce it
        self.solver_version = solver_version
        self.duration_s = duration_s
        self.ran_at = ran_at
        self.who = who
        self.status = status
        self.notes = notes
