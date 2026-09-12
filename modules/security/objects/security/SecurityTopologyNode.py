"""
@module security.objects.security.SecurityTopologyNode

Row class SecurityTopologyNode — a node of one security topology view for one scenario.
"""
from objectTreeDecorators import treeObject, treeObjectInit

KINDS = ('process', 'guest', 'target', 'network', 'service', 'actor', 'means', 'resource', 'boundary')


class SecurityTopologyNode(treeObject):
    """A node in a view: for the os view a process (a container, a module inside
    the core, a guest) or a target (the host kernel, the host's files, another
    container, a device, the docker socket); for the network view a network, a
    host service or a listening container; for the app view an actor (a
    visitor, a Keycloak user, a group member, root, an app), a means (a login,
    ssh, sudo, the docker socket, a door) or a resource. `layer` orders the
    columns of the drawing; `system` names the boundary a boundary node stands for."""

    @treeObjectInit
    def __init__(self, name: str = '', view: str = '', scenario: str = '', node: str = '', kind: str = '',
                 layer: int = 0, title: str = '', description: str = '', system: str = ''):
        self.name = name
        self.view = view
        self.scenario = scenario
        self.node = node
        self.kind = kind
        self.layer = layer
        self.title = title
        self.description = description
        self.system = system
