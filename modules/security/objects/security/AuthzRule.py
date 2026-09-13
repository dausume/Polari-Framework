"""
@module security.objects.security.AuthzRule

Row class AuthzRule of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class AuthzRule(treeObject):
    """Who may call what — a VIEW over the accessControl permission sets, roles and the CRUDE gate; the accessControl module stays the authority."""

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', resource: str = '', role: str = '', verbs: str = '', source: str = 'accessControl', gate: str = '', notes: str = ''):
        self.name = name
        self.app = app
        self.resource = resource
        self.role = role
        self.verbs = verbs
        self.source = source
        self.gate = gate
        self.notes = notes
