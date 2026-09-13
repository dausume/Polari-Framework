"""
@module security.objects.security.SecurityProposal

Row class SecurityProposal — a proposed stanza change for one app, derived from a warn-only harvest; waits for an operator.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SecurityProposal(treeObject):
    """The write-back pass: what an app actually did under its warn-only profile, reduced to the stanza
    change that would allow it (writable paths, capabilities from the allow-list, seccomp additions) and
    the accesses the stanza cannot express (never widened into silently). `status` proposed → accepted
    (written into the manifest, re-rendered) | refused (with a reason). Nothing applies by itself."""

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', source: str = '', status: str = 'proposed', observed: int = 0,
                 add_writable: str = '', add_capabilities: str = '', add_syscalls: str = '', not_expressible: str = '',
                 apparmor_lines: str = '', proposed_stanza: str = '', reading: str = '', accepted_by: str = '', notes: str = ''):
        self.name = name
        self.app = app
        self.source = source
        self.status = status
        self.observed = observed
        self.add_writable = add_writable
        self.add_capabilities = add_capabilities
        self.add_syscalls = add_syscalls
        self.not_expressible = not_expressible
        self.apparmor_lines = apparmor_lines
        self.proposed_stanza = proposed_stanza
        self.reading = reading
        self.accepted_by = accepted_by
        self.notes = notes
