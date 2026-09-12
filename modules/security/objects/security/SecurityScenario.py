"""
@module security.objects.security.SecurityScenario

Row class SecurityScenario — mirrors os-security/scenarios/<name>.yml, read-only.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SecurityScenario(treeObject):
    """One deployment scenario: which route (isle = the app route with debs, KVM
    guests and hardware; swarm = the server route), which rings apply, how the
    MAC ring attaches (per container via security_opt, or the node-wide
    docker-default replacement because swarm services cannot carry a profile),
    whether modules are containers or run inside the core, and the fixed pieces."""

    @treeObjectInit
    def __init__(self, name: str = '', route: str = '', title: str = '', rings: str = '', mode: str = 'complain',
                 mac_attach: str = 'security_opt', apps_run: str = 'containers', fixed_pieces: str = '',
                 guests: bool = False, hardware: bool = False, description: str = ''):
        self.name = name
        self.route = route
        self.title = title
        self.rings = rings
        self.mode = mode
        self.mac_attach = mac_attach
        self.apps_run = apps_run
        self.fixed_pieces = fixed_pieces
        self.guests = guests
        self.hardware = hardware
        self.description = description
