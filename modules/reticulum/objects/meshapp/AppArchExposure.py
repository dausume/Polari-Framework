"""
@module reticulum.objects.meshapp.AppArchExposure

Row class AppArchExposure of the reticulum module — one class per file (design §7), split
from meshapp_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AppArchExposure(treeObject):
    """One app's participation at ONE level: scope + which
    archipelago + our ROLE there. An app may hold several exposure
    rows (one per level). Default isle + observer + disabled —
    raising a rung, or claiming a bigger role, is always a
    deliberate act."""

    @treeObjectInit
    def __init__(self, name='', app_name='', scope='isle',
                 arch_name='', role='observer', enabled=False,
                 exposed_by='', exposed_at='', notes='',
                 manager=None):
        self.name = name
        self.app_name = app_name
        self.scope = scope
        # WHICH archipelago carries it at 'arch' scope and above —
        # a farmer's market is a specific market, not all markets.
        self.arch_name = arch_name
        # what WE are for this app at this level: observer (receive-
        # only presence), user (submits under the data rules),
        # relay-only (forwards state, holds no authority), server
        # (the app's authoritative core — the lighthouse keeper).
        self.role = role
        self.enabled = enabled
        # who raised the rung, and when — exposure is provenance.
        self.exposed_by = exposed_by
        self.exposed_at = exposed_at
        self.notes = notes
