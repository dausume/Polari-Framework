"""
@module reticulum.objects.meshapp.KitProfile

Row class KitProfile of the reticulum module — one class per file (design §7), split
from meshapp_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class KitProfile(treeObject):
    """A named per-person equipment CONFIGURATION (§5q, Dustin
    2026-08-13): counts of devices one person carries — the unit the
    population sims count PEOPLE by. Percentages are analytics;
    counts of people per profile are the configuration."""

    @treeObjectInit
    def __init__(self, name='', display_name='', devices_json='{}',
                 intent='custom', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        # {'lora': 1, 'ham-rx': 1, 'wifi-halow': 1} — builds from the
        # population vocabulary, counts per person.
        self.devices_json = devices_json
        # everyday | broadcaster | backbone | custom — what this kit
        # is FOR, so a planner reads intent, not just parts.
        self.intent = intent
        self.notes = notes
