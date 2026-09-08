"""
@module climate.objects.climate.IndoorSpaceProfile

Row class IndoorSpaceProfile of the climate module — one class per file (design §7), split
from climate_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
