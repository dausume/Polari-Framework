"""
@module cntfet.cnt_process_basis

S3: manufacturing processes as FIRST-CLASS OBJECTS contributing
DISTRIBUTIONS, never ideal values (plan D7). A device declares its
targets (chirality, Lg, t_ox, Rc prior); the process set predicts
what a real line would produce around those targets; Monte Carlo
(cnt_montecarlo) instantiates the population. The manufacturing
feedback loop — method -> measured capability -> process model ->
device MC -> yield -> dominant limitation — is the point.

The six process classes are the plan's D7 list. Every distribution
parameter carries source + confidence; UNSOURCED sigmas are
engineering priors, flagged low-confidence and TUNABLE — and the
MC engine refuses a process row whose distributions_confidence is
'none' (refusal, not silent idealization).

manufacturing_regime coherence (D6): process rows declare which
regime they describe; binding a device to a process set from a
different regime is refused loudly (a coarse solution-processed
line cannot fabricate a 15 nm aligned device).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
  - cntfet.cnt_montecarlo (the sampling engine)
  - cntfet.selftest_cntfet
"""

from objectTreeDecorators import treeObject, treeObjectInit


class CNTAlignmentProcess(treeObject):
    """Tube-axis alignment: angle spread. A misaligned tube's
    effective channel lengthens by 1/cos(theta)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        angle_sigma_deg: float = 0.0,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.angle_sigma_deg = angle_sigma_deg
        self.source = source
        self.confidence = confidence
        self.notes = notes


class CNTPlacementProcess(treeObject):
    """Tube placement: pitch spread + the missing-tube
    probability. At S3's one-tube scope a missing tube IS a dead
    device; pitch matters from the multi-tube arc onward."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        pitch_mu_nm: float = 0.0,
        pitch_sigma_nm: float = 0.0,
        missing_tube_prob: float = 0.0,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.pitch_mu_nm = pitch_mu_nm
        self.pitch_sigma_nm = pitch_sigma_nm
        self.missing_tube_prob = missing_tube_prob
        self.source = source
        self.confidence = confidence
        self.notes = notes


class CNTPurificationProcess(treeObject):
    """Semiconducting sorting + diameter distribution. A metallic
    tube (probability 1 - purity) kills a one-tube FET outright.
    RINSE/DREAM ride here as explicit mitigation knobs (their
    Hills-2019 numbers are cited anchors)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        semiconducting_purity: float = 0.9999,
        diameter_mu_nm: float = 1.2,
        diameter_sigma_nm: float = 0.1,
        rinse_applied: bool = True,
        dream_design_context: bool = False,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.semiconducting_purity = semiconducting_purity
        self.diameter_mu_nm = diameter_mu_nm
        self.diameter_sigma_nm = diameter_sigma_nm
        self.rinse_applied = rinse_applied
        self.dream_design_context = dream_design_context
        self.source = source
        self.confidence = confidence
        self.notes = notes


class ContactFormationProcess(treeObject):
    """Contact resistance spread (D9 stays first-class in
    variability too: Rc gets ITS OWN distribution, never folded
    into mobility spread). Lognormal — Rc is positive and
    right-skewed in practice."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        rc_median_ohm: float = 5500.0,
        rc_sigma_ln: float = 0.2,
        min_contact_length_nm: float = 20.0,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.rc_median_ohm = rc_median_ohm
        self.rc_sigma_ln = rc_sigma_ln
        self.min_contact_length_nm = min_contact_length_nm
        self.source = source
        self.confidence = confidence
        self.notes = notes


class LithographyProcess(treeObject):
    """Feature-size + overlay spread. S3 uses the Lg (feature)
    axis; overlay enters with multi-layer layout work (S7)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        feature_sigma_nm: float = 1.0,
        overlay_sigma_nm: float = 2.0,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.feature_sigma_nm = feature_sigma_nm
        self.overlay_sigma_nm = overlay_sigma_nm
        self.source = source
        self.confidence = confidence
        self.notes = notes


class GateStackProcess(treeObject):
    """Gate-stack spread: t_ox, k_ox, and the threshold shift from
    interface/fixed charge (the Vt sigma every real CNT line
    fights)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        process_set: str = '',
        manufacturing_regime: str = '',
        tox_sigma_nm: float = 0.1,
        kox_sigma: float = 0.5,
        vt_sigma_v: float = 0.05,
        source: str = '',
        confidence: str = 'low',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.process_set = process_set
        self.manufacturing_regime = manufacturing_regime
        self.tox_sigma_nm = tox_sigma_nm
        self.kox_sigma = kox_sigma
        self.vt_sigma_v = vt_sigma_v
        self.source = source
        self.confidence = confidence
        self.notes = notes


class CNTFETMonteCarloRun(treeObject):
    """One MC population run: inputs, per-metric population
    statistics, yield breakdown, dominant limitation — a row."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        device: str = '',
        process_set: str = '',
        sample_count: int = 0,
        seed: int = 0,
        inputs_json: str = '{}',
        yield_json: str = '{}',
        population_json: str = '{}',
        dominant_limitation: str = '',
        verdict: str = '',
        ran_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device = device
        self.process_set = process_set
        self.sample_count = sample_count
        self.seed = seed
        self.inputs_json = inputs_json
        self.yield_json = yield_json
        self.population_json = population_json
        self.dominant_limitation = dominant_limitation
        self.verdict = verdict
        self.ran_at = ran_at
        self.notes = notes


_PRIOR = ('engineering prior — no measured capability yet; '
          'TUNABLE, replace with line data')

# The S1 target line: what we would need a line to do for the
# aggressively-scaled one-tube device. Purity is the ONE anchored
# number ([HIL19] DREAM context); everything else is a flagged
# prior.
SEED_ALIGNMENT_PROCESSES = [
    {'name': 's1-target-alignment', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'angle_sigma_deg': 3.0, 'source': _PRIOR,
     'confidence': 'low', 'notes': ''},
]
SEED_PLACEMENT_PROCESSES = [
    {'name': 's1-target-placement', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'pitch_mu_nm': 0.0, 'pitch_sigma_nm': 0.0,
     'missing_tube_prob': 0.02, 'source': _PRIOR,
     'confidence': 'low',
     'notes': 'pitch unused at tube_count = 1 (multi-tube arc)'},
]
SEED_PURIFICATION_PROCESSES = [
    {'name': 's1-target-purification',
     'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'semiconducting_purity': 0.9999,
     'diameter_mu_nm': 1.25, 'diameter_sigma_nm': 0.1,
     'rinse_applied': True, 'dream_design_context': False,
     'source': 'purity: [HIL19] DREAM working point pS ~ 99.99% '
               '(anchor hil19-cnts-per-cnfet context); diameter '
               'sigma: ' + _PRIOR,
     'confidence': 'medium',
     'notes': 'DREAM is a CIRCUIT mitigation — at one-tube scope '
              'a metallic tube is simply a dead device'},
]
SEED_CONTACT_PROCESSES = [
    {'name': 's1-target-contacts', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'rc_median_ohm': 5500.0, 'rc_sigma_ln': 0.2,
     'min_contact_length_nm': 20.0,
     'source': 'median: [VS1] extraction step (a) ([FC10] '
               'devices); sigma: ' + _PRIOR,
     'confidence': 'low',
     'notes': 'Franklin 2014 six-metal Rc(Lc) table = the S3+ '
              'upgrade path (anchor list item 11)'},
]
SEED_LITHOGRAPHY_PROCESSES = [
    {'name': 's1-target-litho', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'feature_sigma_nm': 1.0, 'overlay_sigma_nm': 2.0,
     'source': _PRIOR, 'confidence': 'low', 'notes': ''},
]
SEED_GATESTACK_PROCESSES = [
    {'name': 's1-target-gatestack', 'process_set': 's1-target-line',
     'manufacturing_regime': 'aggressively_scaled',
     'tox_sigma_nm': 0.1, 'kox_sigma': 0.5, 'vt_sigma_v': 0.05,
     'source': _PRIOR, 'confidence': 'low',
     'notes': 'vt sigma = interface/fixed charge; [HIL19] '
              'Extended Data distributions are the cited upgrade '
              'path once digitized'},
]
