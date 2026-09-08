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

@consumers climate.custom.series_ingest, climate.custom.co2_trend,
climate.co2_indoor_seed, climate.climate_views_seed, climate.climate_api,
polariServer (registration + seed)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/climate/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from climate.objects.climate._shared import EVIDENCE_GRADES, LOCALITY_KINDS, MEASUREMENT_KINDS, MEASURE_KINDS, SERIES_STATUS, SETTING_KINDS, SYMPTOM_SEVERITY  # noqa: F401
from climate.objects.climate.AtmosphericSeriesDefinition import AtmosphericSeriesDefinition  # noqa: F401
from climate.objects.climate.SourceCoverageSpan import SourceCoverageSpan  # noqa: F401
from climate.objects.climate.AtmosphericObservation import AtmosphericObservation  # noqa: F401
from climate.objects.climate.AtmosphericTrendFit import AtmosphericTrendFit  # noqa: F401
from climate.objects.climate.CO2HealthThreshold import CO2HealthThreshold  # noqa: F401
from climate.objects.climate.HealthSymptomDefinition import HealthSymptomDefinition  # noqa: F401
from climate.objects.climate.SymptomOnsetClaim import SymptomOnsetClaim  # noqa: F401
from climate.objects.climate.AmbientSettingProfile import AmbientSettingProfile  # noqa: F401
from climate.objects.climate.ObservedLevelReference import ObservedLevelReference  # noqa: F401
from climate.objects.climate.IndoorSpaceProfile import IndoorSpaceProfile  # noqa: F401
from climate.objects.climate.ExposureProjection import ExposureProjection  # noqa: F401
from climate.objects.climate.PopulationBiomarkerSeries import PopulationBiomarkerSeries  # noqa: F401
from climate.objects.climate.BiomarkerCycleObservation import BiomarkerCycleObservation  # noqa: F401
from climate.objects.climate.CarbonSinkSeries import CarbonSinkSeries  # noqa: F401
from climate.objects.climate.HumanEraDefinition import HumanEraDefinition  # noqa: F401
