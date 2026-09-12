"""
@module security.objects.security.SecurityControl

Row class SecurityControl — one concrete protecting system per scenario, with its provenance and state.
"""
from objectTreeDecorators import treeObject, treeObjectInit

PROVENANCES = ('stock', 'qemu', 'polari')
STATES = ('absent', 'stock', 'rendered', 'complain', 'enforce', 'live')


class SecurityControl(treeObject):
    """One row per (system, scenario): which domain/area it belongs to, who
    provides it (stock = docker/the kernel give it to every container already;
    qemu = libvirt/qemu give it to every guest; polari = rendered by os-security
    or the proxy), and its state on that scenario today (absent, stock,
    rendered only, loaded in complain, enforced, live). Never hand-typed: the
    seed derives it from security_facts and the render manifests."""

    @treeObjectInit
    def __init__(self, name: str = '', system: str = '', scenario: str = '', domain: str = '', area: str = '',
                 title: str = '', provenance: str = 'stock', state: str = 'absent', protects: str = '',
                 evidence: str = '', notes: str = ''):
        self.name = name
        self.system = system
        self.scenario = scenario
        self.domain = domain
        self.area = area
        self.title = title
        self.provenance = provenance
        self.state = state
        self.protects = protects
        self.evidence = evidence
        self.notes = notes
