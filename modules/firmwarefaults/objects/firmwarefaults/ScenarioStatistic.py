"""
@module firmwarefaults.objects.firmwarefaults.ScenarioStatistic

ScenarioStatistic — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ScenarioStatistic(treeObject):
    """What it is: The STATISTICS TIER of a scenario (FIRMWARE_SCENARIO_PLAN.md §5 tier 3, sc-1's first step): many seeded
    runs of one build under one stimulus parameter (a bit error rate, an asynchronous-traffic rate) → events in trials,
    the rate and its 95 % Wilson interval, the per-seed counts, and — where an ideal reference exists — the RESIDUAL apart
    (events the firmware caused beyond what the stimulus itself destroyed). Coverage is stated: these seeds, this window,
    this build; it is an estimate, never a proof.
    Related concepts: `Scenario`, `ScenarioRun`, the fault row whose rate it measures.
    """

    plain_words = ('A scenario statistic runs the same simulated board many times with different random seeds and counts '
                   'how often the bug happens, with a range that says how sure the count is.')

    @treeObjectInit
    def __init__(self, name: str = '', scenario: str = '', side: str = '', variant: str = '', build_name: str = '', measure: str = '',
                 parameter: str = '', parameter_value: float = 0.0, seeds: int = 0, seed_list: str = '', trials: int = 0, events: int = 0,
                 rate: float = 0.0, ci_low: float = 0.0, ci_high: float = 0.0, ci_method: str = 'wilson 95 %', residual_events: int = 0,
                 residual_rate: float = 0.0, residual_ci_low: float = 0.0, residual_ci_high: float = 0.0, per_seed: str = '',
                 window_s: float = 0.0, wall_s: float = 0.0, firmware_sha256: str = '', harness_digest: str = '', repro_json: str = '{}',
                 ran_at: str = '', notes: str = '', events_per_1000: float = 0.0, manager=None):
        self.name = name
        self.scenario = scenario
        self.side = side  # before | after | natural
        self.variant = variant
        self.build_name = build_name
        self.measure = measure  # what an event and a trial are, in words
        self.parameter = parameter  # ber | rx_noise_rate | …
        self.parameter_value = parameter_value
        self.seeds = seeds
        self.seed_list = seed_list  # e.g. 0..19
        self.trials = trials  # pooled over the seeds
        self.events = events
        self.rate = rate  # events / trials
        self.ci_low = ci_low
        self.ci_high = ci_high
        self.ci_method = ci_method
        self.residual_events = residual_events  # events beyond the ideal reference (the firmware's own share)
        self.residual_rate = residual_rate
        self.residual_ci_low = residual_ci_low
        self.residual_ci_high = residual_ci_high
        self.per_seed = per_seed  # k/n per seed, in order
        self.window_s = window_s  # simulated seconds per run
        self.wall_s = wall_s  # total wall time of the batch
        self.firmware_sha256 = firmware_sha256
        self.harness_digest = harness_digest
        self.repro_json = repro_json
        self.ran_at = ran_at
        self.notes = notes
        self.events_per_1000 = events_per_1000  # events per 1000 trials (frames lost per 1000 sent, …)
