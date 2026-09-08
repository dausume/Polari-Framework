"""
@module climate.objects.climate.AmbientSettingProfile

Row class AmbientSettingProfile of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from climate.objects.climate._shared import LOCALITY_KINDS, SETTING_KINDS

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
