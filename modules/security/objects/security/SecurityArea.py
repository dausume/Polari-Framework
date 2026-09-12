"""
@module security.objects.security.SecurityArea

Row class SecurityArea — an area beneath a domain (dac, mac, firewall, tls, authentication, …).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SecurityArea(treeObject):
    """An area under a domain. `generated` says whether Polari renders the
    control from templates (profiles, firewall rules, proxy snippets) or only
    observes it (Keycloak, sVirt). `docs_page` is the public page."""

    @treeObjectInit
    def __init__(self, name: str = '', domain: str = '', title: str = '', description: str = '',
                 generated: bool = False, docs_page: str = ''):
        self.name = name
        self.domain = domain
        self.title = title
        self.description = description
        self.generated = generated
        self.docs_page = docs_page
