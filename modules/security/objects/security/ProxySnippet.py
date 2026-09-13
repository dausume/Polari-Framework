"""
@module security.objects.security.ProxySnippet

Row class ProxySnippet of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ProxySnippet(treeObject):
    """A per-app proxy snippet (modules/<app>/security/proxy/<scope>.conf.j2) composed into the proxy when the app goes up (sec-i-4). None exist yet: rows say 'absent' per app and scope so the gap is visible."""

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', scope: str = 'api', kind: str = 'location', template: str = '', rendered: str = '', enabled: bool = False, order: int = 100, requires: str = '', state: str = 'absent'):
        self.name = name
        self.app = app
        self.scope = scope
        self.kind = kind
        self.template = template
        self.rendered = rendered
        self.enabled = enabled
        self.order = order
        self.requires = requires
        self.state = state
