"""
@module security.objects.security.SecurityDomain

Row class SecurityDomain — one of the three fixed roots of the security taxonomy (SECURITY_INTERFACES_PLAN §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit

DOMAINS = ('app', 'network', 'os')


class SecurityDomain(treeObject):
    """A root of the taxonomy: app (who may call what, how an app proves itself),
    network (how bytes get in, between and out), os (what a process can touch).
    Seeded, read-only; an operator does not add roots. Each domain is also one
    security topology view (/display/security-<domain>)."""

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', description: str = '', order: int = 0, view_route: str = ''):
        self.name = name
        self.title = title
        self.description = description
        self.order = order
        self.view_route = view_route
