"""
@module security.objects.security.ProxyConfig

Row class ProxyConfig of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ProxyConfig(treeObject):
    """One proxy configuration per (route, env): the template, the rendered file, the guard verdict, the hardening flags read from the template text (TLS versions, HSTS, headers, rate limits), and the server names it fronts."""

    @treeObjectInit
    def __init__(self, name: str = '', route: str = 'suite-proxy', env: str = '', template: str = '', rendered: str = '', server_names: str = '', upstreams: str = '', tls_versions: str = '', hsts: bool = False, headers: str = '', rate_limits: str = '', guard_verdict: str = 'not-run', snippets_included: int = 0):
        self.name = name
        self.route = route
        self.env = env
        self.template = template
        self.rendered = rendered
        self.server_names = server_names
        self.upstreams = upstreams
        self.tls_versions = tls_versions
        self.hsts = hsts
        self.headers = headers
        self.rate_limits = rate_limits
        self.guard_verdict = guard_verdict
        self.snippets_included = snippets_included
