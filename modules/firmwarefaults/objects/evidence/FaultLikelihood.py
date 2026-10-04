"""
@module firmwarefaults.objects.evidence.FaultLikelihood

FaultLikelihood — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class FaultLikelihood(treeObject):
    """What it is: The LIKELIHOOD TABLE row per fault kind (FIRMWARE_SCENARIO_PLAN.md §5 tier 3, sc-2): for one fault row at one
    stimulus value, how often the bug happened WITHOUT the technique (events / trials, rate, 95 % Wilson interval) and how
    often WITH it (the technique's residual), from one ScenarioCampaign. A measure on a twin under stated coverage — never a
    proof and never a field rate until a cited physical rate is plugged in as the stimulus.
    Related concepts: `ScenarioCampaign`, the fault row (`fault_class`:`fault`), `ScenarioStatistic`, `Technique`.
    """

    plain_words = ('A likelihood row says, for one kind of firmware bug at one level of disturbance, how often it happened '
                   'without the fix and how often with it, each with a range that says how sure the number is.')

    @treeObjectInit
    def __init__(self, name: str = '', fault_class: str = '', fault: str = '', campaign: str = '', scenario: str = '', parameter: str = '',
                 parameter_value: float = 0.0, parameter_unit: str = '', trial_unit: str = '', before_events: int = 0, before_trials: int = 0,
                 before_rate: float = 0.0, before_ci_low: float = 0.0, before_ci_high: float = 0.0, technique: str = '', after_events: int = 0,
                 after_trials: int = 0, after_rate: float = 0.0, after_ci_low: float = 0.0, after_ci_high: float = 0.0, ttff_median_ms: float = -1.0,
                 coverage: str = '', ran_at: str = '', notes: str = '', manager=None):
        self.name = name
        self.fault_class = fault_class
        self.fault = fault
        self.campaign = campaign
        self.scenario = scenario
        self.parameter = parameter
        self.parameter_value = parameter_value
        self.parameter_unit = parameter_unit
        self.trial_unit = trial_unit  # what one trial is (a carry, a command, a press, a request)
        self.before_events = before_events
        self.before_trials = before_trials
        self.before_rate = before_rate  # the likelihood without the technique
        self.before_ci_low = before_ci_low
        self.before_ci_high = before_ci_high
        self.technique = technique
        self.after_events = after_events  # the technique's residual
        self.after_trials = after_trials
        self.after_rate = after_rate
        self.after_ci_low = after_ci_low
        self.after_ci_high = after_ci_high
        self.ttff_median_ms = ttff_median_ms  # -1 = not observable in this scenario
        self.coverage = coverage  # seeds, window, builds
        self.ran_at = ran_at
        self.notes = notes
