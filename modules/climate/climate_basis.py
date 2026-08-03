"""
@module climate.climate_basis

THE OBJECT MODEL for the Climate Change & Atmosphere app
(CO2_HEALTH_PLAN.md §1). Every measurement series, source span,
threshold, room archetype and projection is a treeObject row — so
a simulation defined tomorrow can bind it without a code change,
and so the CRUDE pages exist for free.

The test the plan sets for every class here: *could a simulation
bind this without a code change?* If not, it is in the wrong place.

⚠ SOURCE TRACING IS STRUCTURAL, NOT A NOTE FIELD (Dustin
2026-08-02: "the sources for all of this data should be traced",
and "you can tell when one source covered one range of the data
and another covered another range"). So:

    AtmosphericObservation.span_ref
      -> SourceCoverageSpan (which instrument/archive, which years)
        -> APIEndpoint (how it was fetched — polariApiProfiler)
          -> a SOURCE row (who publishes it) — government,
             nonprofit, academic article or credentialed press
             piece; `find_source` resolves across all of them,
             because "source" was never a synonym for "government"
            -> SourceRetrieval (when WE copied it, sha256, rows)

A point on a graph can therefore always answer "who says so, how
did it get here, and what covered THIS part of the x-axis" — which
is the difference between a spliced record and a smooth lie. The
800 kyr CO2 curve is ice cores until ~1958 and Mauna Loa after;
that seam is DATA, not a footnote, and the renderer draws it.

@consumers climate.series_ingest, climate.co2_trend,
climate.co2_indoor, climate.climate_views, climate.climate_api,
polariServer (registration + seed)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: What a series measures. Kept open-ended on purpose — the app is
#: "Climate Change & Atmosphere", not "CO2 only".
MEASURE_KINDS = ('co2-mole-fraction', 'co2-growth-rate',
                 'co2-partial-pressure', 'carbon-sink',
                 'population-biomarker', 'life-expectancy',
                 'population-symptom-score', 'temperature', 'other')

#: HOW the value was obtained — the provenance that matters most
#: when two spans meet on one axis.
MEASUREMENT_KINDS = ('direct-instrument', 'ice-core', 'firn-air',
                     'proxy', 'survey-lab', 'survey-questionnaire',
                     'vital-statistics', 'modelled', 'budget-estimate')

#: Engines REFUSE to project from anything but 'ingested'. A seeded
#: placeholder is 'prior'; a hand-entered literature value is
#: 'literature'. (The DigitizedDataset status discipline, applied
#: here — plan's top rule.)
SERIES_STATUS = ('prior', 'ingested', 'literature', 'modelled',
                 'provisional-low-confidence')

#: Evidence grading for health thresholds. The plan's §5 rule: a
#: ventilation standard is NOT a health study, and averaging them
#: together is how a page becomes confidently wrong.
EVIDENCE_GRADES = ('controlled-human-study',
                   'contested-controlled-study',
                   'observational', 'standard-or-guideline',
                   'occupational-limit',
                   #: A credentialed author REPORTING on primary
                   #: research. The expertise is real and the piece
                   #: is not peer reviewed - two different
                   #: guarantees, and collapsing them into "expert
                   #: says" is how a magazine paragraph acquires
                   #: the authority of a trial.
                   'secondary-reporting',
                   'expert-judgement')


class AtmosphericSeriesDefinition(treeObject):
    """One named measured series. A simulation binds THIS, not a
    chart — the chart is a view over it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', measure='other',
                 unit='ppm', cadence='annual', location='',
                 source_ref='', endpoint_ref='', status='prior',
                 first_year=0.0, last_year=0.0, value_field='value',
                 uncertainty_unit='', description='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.measure = (measure if measure in MEASURE_KINDS
                        else 'other')
        self.unit = unit
        self.cadence = cadence
        #: 'Mauna Loa', 'global marine surface', 'Antarctica
        #: (composite)', 'United States' …
        self.location = location
        #: GovSource.name that publishes it.
        self.source_ref = source_ref
        #: APIEndpoint.name that fetches it (polariApiProfiler).
        self.endpoint_ref = endpoint_ref
        #: SERIES_STATUS — engines gate on this.
        self.status = (status if status in SERIES_STATUS
                       else 'prior')
        #: Calendar years (negative = BCE). Derived on ingest, not
        #: asserted — a seeded range that disagrees with the rows
        #: is exactly the drift this project guards against.
        self.first_year = first_year
        self.last_year = last_year
        self.value_field = value_field
        self.uncertainty_unit = uncertainty_unit
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class SourceCoverageSpan(treeObject):
    """WHICH source covered WHICH stretch of a series' x-axis.

    The ice-core-vs-direct-measure seam, as data. One series may
    have many spans; a renderer colours/segments by span, a
    citation list is built from the spans a plotted window actually
    touches, and an overlap between two spans is a CROSS-CHECK
    opportunity, not a conflict to hide.
    """

    @treeObjectInit
    def __init__(self, name='', series_ref='', display_name='',
                 measurement_kind='direct-instrument',
                 from_year=0.0, to_year=0.0, source_ref='',
                 endpoint_ref='', archive_name='', instrument='',
                 resolution_years=0.0, citation_text='',
                 doi_or_url='', color='#888888',
                 typical_uncertainty=0.0, is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.series_ref = series_ref
        self.display_name = display_name
        self.measurement_kind = (
            measurement_kind if measurement_kind in MEASUREMENT_KINDS
            else 'direct-instrument')
        #: calendar years CE; negative = BCE. An ice core span runs
        #: from -803719 to 1950-ish; Mauna Loa from 1959.
        self.from_year = from_year
        self.to_year = to_year
        self.source_ref = source_ref
        self.endpoint_ref = endpoint_ref
        #: 'EPICA Dome C', 'Law Dome DE08', 'Mauna Loa Observatory'
        self.archive_name = archive_name
        self.instrument = instrument
        #: mean spacing between samples — an 800 kyr ice core is
        #: NOT annual data, and a chart that implies it is lying.
        self.resolution_years = resolution_years
        self.citation_text = citation_text
        self.doi_or_url = doi_or_url
        self.color = color
        self.typical_uncertainty = typical_uncertainty
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class AtmosphericObservation(treeObject):
    """One (series, year, value) point, with its span and its
    uncertainty. The actual data — queryable, re-ingestible."""

    @treeObjectInit
    def __init__(self, name='', series_ref='', span_ref='',
                 year=0.0, value=0.0, uncertainty=0.0,
                 sample_count=0, revision='', retrieval_ref='',
                 is_prior=False, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.series_ref = series_ref
        #: the SourceCoverageSpan this point came from — so any
        #: single point can name its instrument and archive.
        self.span_ref = span_ref
        #: calendar year CE as a float (ice-core points are not
        #: integers; -803719.4 is a real x value).
        self.year = year
        self.value = value
        self.uncertainty = uncertainty
        self.sample_count = sample_count
        self.revision = revision
        #: SourceRetrieval.name — when WE copied it.
        self.retrieval_ref = retrieval_ref
        #: observations are MEASUREMENTS, never priors — the seed
        #: pass must not invent them.
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class AtmosphericTrendFit(treeObject):
    """A fit over a series: a CLAIM with a method, stored so a
    later fit can disagree with it."""

    @treeObjectInit
    def __init__(self, name='', series_ref='', method='quadratic',
                 window_from_year=0.0, window_to_year=0.0,
                 level=0.0, velocity=0.0, acceleration=0.0,
                 velocity_stderr=0.0, acceleration_stderr=0.0,
                 residual_rms=0.0, n_points=0, unit='ppm',
                 fitted_at='', horizon_year=0.0,
                 is_prior=False, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.series_ref = series_ref
        #: 'linear' | 'quadratic' | 'source-growth-rate'
        self.method = method
        self.window_from_year = window_from_year
        self.window_to_year = window_to_year
        #: value at the window's END (the projection's C0).
        self.level = level
        self.velocity = velocity
        self.acceleration = acceleration
        self.velocity_stderr = velocity_stderr
        self.acceleration_stderr = acceleration_stderr
        self.residual_rms = residual_rms
        self.n_points = n_points
        self.unit = unit
        self.fitted_at = fitted_at
        #: beyond this year the fit refuses to print a number.
        self.horizon_year = horizon_year
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class CO2HealthThreshold(treeObject):
    """One CO2 level at which something is claimed to happen to a
    person — WITH the grade of the evidence behind the claim.

    The grading IS the honesty (plan §5). A ventilation standard's
    1000 ppm and a controlled-exposure study's 1000 ppm are not the
    same kind of number and must never be averaged or drawn as one
    band.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', ppm=0.0,
                 unit='ppm', effect='', population='general',
                 exposure='chronic', evidence_grade='expert-judgement',
                 source_ref='', citation_text='', doi_or_url='',
                 is_differential=False, differential_over='',
                 contested_by='', color='#888888',
                 replaces_with='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.ppm = ppm
        self.unit = unit
        self.effect = effect
        #: 'general' | 'occupational' | 'sensitive' | 'children'
        self.population = population
        #: 'acute' | 'hours' | 'chronic'
        self.exposure = exposure
        self.evidence_grade = (
            evidence_grade if evidence_grade in EVIDENCE_GRADES
            else 'expert-judgement')
        self.source_ref = source_ref
        self.citation_text = citation_text
        self.doi_or_url = doi_or_url
        #: 🔑 ASHRAE's criterion is "700 ppm ABOVE OUTDOOR" — a
        #: DIFFERENTIAL, not an absolute. A differential threshold
        #: rises with outdoor CO2, which is why a fully compliant
        #: room can cross an absolute line without anything about
        #: the room changing. Engines must not mix the two.
        self.is_differential = is_differential
        self.differential_over = differential_over
        #: the studies that FAILED to replicate this one. A page
        #: that lists only supporting citations is advocacy.
        self.contested_by = contested_by
        self.color = color
        self.replaces_with = replaces_with
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


#: How bad is it, on a scale a ladder can be ORDERED by. Prose
#: cannot be sorted, and a page that lists "headache" beside
#: "unconsciousness" without ranking them is not a ladder.
SYMPTOM_SEVERITY = {
    1: 'subclinical - detectable by instrument, not felt',
    2: 'discomfort - noticed, tolerated',
    3: 'impairment - performance or judgement affected',
    4: 'acute distress - the person wants out of the room',
    5: 'incapacitation - the person cannot remove themselves',
    6: 'life-threatening - death follows without rescue',
}


class HealthSymptomDefinition(treeObject):
    """One symptom, as a row.

    Symptoms are their own objects because the SAME symptom
    appears at several concentrations from several sources -
    headache is reported at 700 ppm by epidemiology and at 4
    percent by occupational medicine - and a page that restates it
    per threshold cannot show that, nor rank the ladder.

    `is_reversible` matters more here than anywhere: OSHA states
    that low-level CO2 intoxication is "sudden and reversible" and
    dissipates within minutes of leaving the exposure. A ladder
    that lists convulsions next to headache without saying which
    ones undo themselves is frightening rather than informative.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', body_system='',
                 severity_rank=1, is_reversible=True,
                 description='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: 'central-nervous' | 'respiratory' | 'cardiovascular' |
        #: 'metabolic' | 'sensory' | 'general'
        self.body_system = body_system
        #: SYMPTOM_SEVERITY key. Orders the ladder.
        self.severity_rank = severity_rank
        self.is_reversible = is_reversible
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class SymptomOnsetClaim(treeObject):
    """ONE SOURCE SAYS ONE SYMPTOM APPEARS AT ONE LEVEL.

    This is the join that makes the ladder citable. It is
    deliberately not a field on the threshold row: two sources
    disagree about where a symptom starts, and the object model
    has to be able to hold both claims at once rather than forcing
    a page to pick a winner silently.

    A claim carries its own evidence grade, because the grade
    belongs to the CLAIM and not to the symptom - "headache at
    700 ppm" (epidemiological association) and "headache at 40000
    ppm" (occupational medicine) are not equally certain and are
    not equally severe.
    """

    @treeObjectInit
    def __init__(self, name='', symptom_ref='', ppm_from=0.0,
                 ppm_to=0.0, source_ref='',
                 evidence_grade='expert-judgement', exposure='',
                 onset_note='', population='general',
                 quote='', is_lethal=False, is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.symptom_ref = symptom_ref
        #: the band this source attributes the symptom to. ppm_to
        #: of 0 means "and above".
        self.ppm_from = ppm_from
        self.ppm_to = ppm_to
        self.source_ref = source_ref
        self.evidence_grade = (
            evidence_grade if evidence_grade in EVIDENCE_GRADES
            else 'expert-judgement')
        self.exposure = exposure
        self.onset_note = onset_note
        self.population = population
        #: the source's OWN words where they are short enough to
        #: quote. A paraphrase of a health claim is a new claim.
        self.quote = quote
        self.is_lethal = is_lethal
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


#: THE 2x2 THIS APP WAS MISSING. Every CO2 number a person
#: actually breathes sits in one of these, and the app had only
#: two of them: a clean-air outdoor BASELINE and a room. "Outdoor"
#: is not one number - a city street and a mountain observatory
#: differ by more than a century of global rise.
SETTING_KINDS = ('outdoor', 'indoor')
LOCALITY_KINDS = ('remote-background', 'rural', 'suburban',
                  'urban-residential', 'urban-core',
                  'street-canyon')


class AmbientSettingProfile(treeObject):
    """WHERE the air is, as a row: the local outdoor level a room
    actually sits on top of.

    🔑 THE CORRECTION THIS CLASS EXISTS FOR. Every indoor
    projection in this app previously added a room's ventilation
    offset to the MAUNA LOA background - a deliberately
    clean-air, mid-Pacific, high-altitude baseline chosen by NOAA
    precisely because nothing local contaminates it. Almost nobody
    breathes that air. A classroom in a city sits on urban
    outdoor, which is measurably higher, so every indoor crossing
    computed against the global background arrived LATE.

    The enhancement is a BAND, not a number, because it swings
    with wind speed, season, hour and how far up the street
    canyon you stand.

    ⚠ SURFACE MEASUREMENTS ONLY. Satellite column (XCO2) urban
    enhancements are single-digit ppm because a column averages
    through kilometres of clean air above the city; surface in
    situ enhancements are tens of ppm. They are different
    quantities and must never be put on one axis. This class holds
    the SURFACE kind, and says so.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', setting='outdoor',
                 locality='rural', enhancement_ppm=0.0,
                 enhancement_ppm_low=0.0, enhancement_ppm_high=0.0,
                 measurement_kind='surface-in-situ',
                 source_ref='', citation_text='', basis='',
                 replaces_with='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.setting = (setting if setting in SETTING_KINDS
                        else 'outdoor')
        self.locality = (locality if locality in LOCALITY_KINDS
                         else 'rural')
        #: ppm ABOVE the global background, not an absolute level -
        #: so the row stays true as the background rises.
        self.enhancement_ppm = enhancement_ppm
        self.enhancement_ppm_low = enhancement_ppm_low
        self.enhancement_ppm_high = enhancement_ppm_high
        #: 'surface-in-situ' | 'satellite-column'. Never mix.
        self.measurement_kind = measurement_kind
        self.source_ref = source_ref
        self.citation_text = citation_text
        self.basis = basis
        self.replaces_with = replaces_with
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ObservedLevelReference(treeObject):
    """A MEASURED typical range for a kind of place - the reality
    check the modelled numbers are scored against.

    The coupled model computes what a room SHOULD sit at from
    volume, occupancy and air changes. This class holds what
    people have actually MEASURED in rooms like it. When the two
    disagree the model is wrong, and without these rows there is
    nothing to notice that with.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', setting='indoor',
                 locality='', space_kind='', ppm_low=0.0,
                 ppm_high=0.0, ppm_typical=0.0, source_ref='',
                 citation_text='', measurement_note='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.setting = (setting if setting in SETTING_KINDS
                        else 'indoor')
        self.locality = locality
        #: 'bedroom' | 'classroom' | 'office' | 'car-cabin' | ...
        self.space_kind = space_kind
        self.ppm_low = ppm_low
        self.ppm_high = ppm_high
        self.ppm_typical = ppm_typical
        self.source_ref = source_ref
        self.citation_text = citation_text
        self.measurement_note = measurement_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class IndoorSpaceProfile(treeObject):
    """A room archetype — the coupling's inputs, and directly
    bindable by an indoor-air simulation."""

    @treeObjectInit
    def __init__(self, name='', display_name='', volume_m3=0.0,
                 occupancy=1.0, activity_met=1.2,
                 co2_per_person_l_min=0.0, air_changes_per_hour=0.0,
                 atmosphere_ref='', category='', basis='',
                 setting_ref='outdoor-suburban',
                 replaces_with='', is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.volume_m3 = volume_m3
        self.occupancy = occupancy
        #: metabolic rate; CO2 output scales with it.
        self.activity_met = activity_met
        self.co2_per_person_l_min = co2_per_person_l_min
        self.air_changes_per_hour = air_changes_per_hour
        #: an AtmosphereDefinition (aquaponics) row this REFERENCES
        #: rather than duplicating volume/ACH into.
        self.atmosphere_ref = atmosphere_ref
        self.category = category
        self.basis = basis
        #: WHICH OUTDOOR this room sits on top of. Every indoor
        #: level in this app used to be computed against the
        #: Mauna Loa background, i.e. against air almost nobody
        #: breathes. A room in a city is seated on urban outdoor,
        #: and the difference is tens of ppm before anyone opens
        #: a door.
        self.setting_ref = setting_ref
        #: every room archetype retires the same way: measure it
        #: with a CO2 meter.
        self.replaces_with = replaces_with
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ExposureProjection(treeObject):
    """A computed crossing — STORED, not just returned, so the next
    ingest's answer can be compared against this one and the page
    can show its own answers moving."""

    @treeObjectInit
    def __init__(self, name='', threshold_ref='', space_ref='',
                 series_ref='', fit_ref='', method='quadratic',
                 crossing_year=0.0, crossing_year_low=0.0,
                 crossing_year_high=0.0, already_crossed=False,
                 outdoor_ppm_at_crossing=0.0, indoor_offset_ppm=0.0,
                 ventilation_knob_note='', refused=False,
                 refusal='', computed_at='', is_prior=False,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.threshold_ref = threshold_ref
        #: '' means the OUTDOOR crossing (no room).
        self.space_ref = space_ref
        self.series_ref = series_ref
        self.fit_ref = fit_ref
        self.method = method
        self.crossing_year = crossing_year
        #: the linear/quadratic bracket. One number with no band is
        #: the failure mode here (plan §7.5).
        self.crossing_year_low = crossing_year_low
        self.crossing_year_high = crossing_year_high
        self.already_crossed = already_crossed
        self.outdoor_ppm_at_crossing = outdoor_ppm_at_crossing
        self.indoor_offset_ppm = indoor_offset_ppm
        self.ventilation_knob_note = ventilation_knob_note
        self.refused = refused
        self.refusal = refusal
        self.computed_at = computed_at
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class PopulationBiomarkerSeries(treeObject):
    """An NHANES-style biomarker/symptom series by survey cycle.

    Separate from AtmosphericSeriesDefinition because a survey
    cycle is not a year: it is a 2-year window with a sample
    design, and pretending otherwise is how a correlation becomes
    a fabrication.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', biomarker='',
                 unit='', source_ref='', endpoint_ref='',
                 xpt_column='', codebook_url='', status='prior',
                 population_note='', assay_note='',
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.biomarker = biomarker
        self.unit = unit
        self.source_ref = source_ref
        self.endpoint_ref = endpoint_ref
        #: 🔑 the opaque NHANES column ('LBXSC3SI'). The reader
        #: NEVER guesses what a column means — the mapping lives
        #: here, in a row, with the codebook that defines it.
        self.xpt_column = xpt_column
        self.codebook_url = codebook_url
        self.status = (status if status in SERIES_STATUS
                       else 'prior')
        self.population_note = population_note
        #: assay methods change between cycles; an unremarked
        #: method change looks exactly like a population trend.
        self.assay_note = assay_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class BiomarkerCycleObservation(treeObject):
    """One survey cycle's summary statistic for one biomarker."""

    @treeObjectInit
    def __init__(self, name='', series_ref='', cycle='',
                 cycle_start_year=0.0, cycle_end_year=0.0,
                 mean=0.0, std_dev=0.0, median=0.0, n=0,
                 pct_5=0.0, pct_95=0.0, retrieval_ref='',
                 is_prior=False, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.series_ref = series_ref
        #: 'BIOPRO_D' / '2005-2006'
        self.cycle = cycle
        self.cycle_start_year = cycle_start_year
        self.cycle_end_year = cycle_end_year
        self.mean = mean
        self.std_dev = std_dev
        self.median = median
        self.n = n
        self.pct_5 = pct_5
        self.pct_95 = pct_95
        self.retrieval_ref = retrieval_ref
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class CarbonSinkSeries(treeObject):
    """Land/ocean sink capacity and the sink FRACTION over time."""

    @treeObjectInit
    def __init__(self, name='', display_name='', sink_kind='land',
                 unit='GtC/yr', source_ref='', endpoint_ref='',
                 status='prior', description='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: 'land' | 'ocean' | 'atmospheric-fraction'
        self.sink_kind = sink_kind
        self.unit = unit
        self.source_ref = source_ref
        self.endpoint_ref = endpoint_ref
        self.status = (status if status in SERIES_STATUS
                       else 'prior')
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class HumanEraDefinition(treeObject):
    """A named stretch of human history/prehistory, so the CO2
    record can be read as "what did people actually breathe".

    ⚠ The era boundaries are archaeological consensus RANGES, not
    measurements, and life expectancy before vital registration is
    a skeletal-demography ESTIMATE with enormous error bars and a
    known bias (high infant mortality drags the mean far below
    adult lifespan). Both carry `is_prior` and a citation; the
    engines must never regress one against CO2 and call it a
    finding.
    """

    @treeObjectInit
    def __init__(self, name='', display_name='', from_year=0.0,
                 to_year=0.0, description='',
                 life_expectancy_at_birth=0.0,
                 life_expectancy_basis='',
                 life_expectancy_is_estimate=True,
                 population_estimate=0.0, citation_text='',
                 doi_or_url='', color='#888888', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: calendar years CE, negative = BCE.
        self.from_year = from_year
        self.to_year = to_year
        self.description = description
        self.life_expectancy_at_birth = life_expectancy_at_birth
        self.life_expectancy_basis = life_expectancy_basis
        self.life_expectancy_is_estimate = life_expectancy_is_estimate
        self.population_estimate = population_estimate
        self.citation_text = citation_text
        self.doi_or_url = doi_or_url
        self.color = color
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
