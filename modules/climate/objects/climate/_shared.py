"""@module climate.objects.climate._shared — what the climate row classes share (constants, seeds, helpers); split from climate_basis.py (sap-2c)."""

MEASURE_KINDS = ('co2-mole-fraction', 'co2-growth-rate',
                 'co2-partial-pressure', 'carbon-sink',
                 'population-biomarker', 'life-expectancy',
                 'population-symptom-score', 'temperature', 'other')
MEASUREMENT_KINDS = ('direct-instrument', 'ice-core', 'firn-air',
                     'proxy', 'survey-lab', 'survey-questionnaire',
                     'vital-statistics', 'modelled', 'budget-estimate')
SERIES_STATUS = ('prior', 'ingested', 'literature', 'modelled',
                 'provisional-low-confidence')
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
SYMPTOM_SEVERITY = {
    1: 'subclinical - detectable by instrument, not felt',
    2: 'discomfort - noticed, tolerated',
    3: 'impairment - performance or judgement affected',
    4: 'acute distress - the person wants out of the room',
    5: 'incapacitation - the person cannot remove themselves',
    6: 'life-threatening - death follows without rescue',
}
SETTING_KINDS = ('outdoor', 'indoor')
LOCALITY_KINDS = ('remote-background', 'rural', 'suburban',
                  'urban-residential', 'urban-core',
                  'street-canyon')
