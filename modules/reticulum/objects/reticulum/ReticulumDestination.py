"""
@module reticulum.objects.reticulum.ReticulumDestination

Row class ReticulumDestination of the reticulum module — one class per file (design §7), split
from reticulum_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ReticulumDestination(treeObject):
    """name ⇄ RNS destination hash. The row §3's name registry is made
    of: the gateway refuses unmapped addresses BY NAME."""

    @treeObjectInit
    def __init__(self, name='', identity_name='', app_name='polari',
                 aspects='', dest_hash='', dest_type='single',
                 scope='local', direction='both', notes='',
                 manager=None):
        self.name = name
        self.identity_name = identity_name
        self.app_name = app_name
        # Dot-joined aspect list ('ret0.gossip') — scalar on purpose.
        self.aspects = aspects
        self.dest_hash = dest_hash
        self.dest_type = dest_type
        self.scope = scope
        self.direction = direction
        self.notes = notes
