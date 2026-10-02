"""
@module firmwarefaults.objects.evidence.ScenarioCampaign

ScenarioCampaign — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ScenarioCampaign(treeObject):
    """What it is: The STATISTICS TIER as a row (FIRMWARE_SCENARIO_PLAN.md §5 tier 3, sc-2): one scenario × one fault kind ×
    the fault's RATE as the stimulus distribution (a bit error rate, a drop probability, a bounce-window length, an
    asynchronous-traffic rate — one or several values) × seeds × a window per run. Running it runs the harness once per
    (side, rate, seed) with the seed machinery of sc-1, then aggregates per rate: the likelihood of the bug without the
    technique (BEFORE) with its 95 % Wilson interval, the technique's RESIDUAL (AFTER), the time-to-first-fault distribution
    where the run can observe it, writes ScenarioStatistic + FaultLikelihood rows, updates the fault row's rate_source and
    adds the `statistics` evidence tier to the scenario's claims (the claim's status stays witnessed / refuted — a rate is
    a measure, never a proof). Coverage is stated: these seeds, this window, these builds.
    Related concepts: `Scenario`, `ScenarioStatistic`, `FaultLikelihood`, the fault row, mathproofs' `MathClaim`.
    """

    plain_words = ('A campaign runs one bug-forcing scenario many times with a realistic rate of disturbance, with and without '
                   'the fix, and says how likely the bug is, with a range that says how sure that number is.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', scenario: str = '', fault_class: str = '', fault: str = '', parameter: str = '',
                 parameter_unit: str = '', rates_json: str = '[]', seeds: int = 0, run_seconds: float = 0.0, sides_json: str = '["before", "after"]',
                 stimulus: str = '', event_before: str = '', event_after: str = '', ttff_what: str = '', status: str = 'not-run',
                 results_json: str = '[]', likelihood_summary: str = '', ttff_summary: str = '', statistics_json: str = '[]', runs: int = 0,
                 wall_s: float = 0.0, harness_digest: str = '', repro_json: str = '{}', ran_at: str = '', provenance: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.title = title
        self.scenario = scenario  # the Scenario name
        self.fault_class = fault_class
        self.fault = fault  # the fault row whose rate_source the campaign updates
        self.parameter = parameter  # ber | drop_p | bounce_window_ms | rx_noise_rate
        self.parameter_unit = parameter_unit
        self.rates_json = rates_json  # the stimulus values, in order
        self.seeds = seeds  # per (side, rate)
        self.run_seconds = run_seconds  # simulated seconds per run (0 = the scenario's own)
        self.sides_json = sides_json  # before | after
        self.stimulus = stimulus  # how the rate drives the harness, in words
        self.event_before = event_before  # what counts as the bug happening without the technique
        self.event_after = event_after  # what the technique leaves (the residual)
        self.ttff_what = ttff_what  # what "time to first fault" means here, or why it is not observable
        self.status = status  # not-run | ran | refused: …
        self.results_json = results_json  # [{rate, before:{k,n,p,lo,hi}, after:{…}, ttff:{…}}]
        self.likelihood_summary = likelihood_summary  # one line per rate, for people
        self.ttff_summary = ttff_summary
        self.statistics_json = statistics_json  # the ScenarioStatistic names written
        self.runs = runs
        self.wall_s = wall_s
        self.harness_digest = harness_digest
        self.repro_json = repro_json
        self.ran_at = ran_at
        self.provenance = provenance
        self.notes = notes
