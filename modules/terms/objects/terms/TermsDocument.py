"""
@module terms.objects.terms.TermsDocument

Row class TermsDocument of the terms module — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit

KINDS = ('demo', 'standard', 'privacy', 'custom')
SCOPES = ('global', 'app')


class TermsDocument(treeObject):
    """One terms-of-service (or notice) text an instance can require.

    What it is: a versioned document. `scope` global applies on every
    app of the instance; `scope` app applies only when `app_name` is the
    app in view. `active` + `requires_acceptance` decide whether a
    visitor is gated; `kind` demo also turns on the persistent
    "Demonstration instance" bar. `version` is what an acceptance is
    recorded against, so changing the text (bump the version) re-prompts
    everyone. Bodies are plain Markdown; the API serves them with their
    sha256 so an acceptance can prove which exact text was shown.
    Related concepts: TermsAcceptance (the records), the frontends' terms
    gate, the hub's /docs/demo-terms.html (the same demo text, published).
    How it is derived: seeded boilerplate (demo, standard, privacy) that an
    operator edits or clones per app through CRUDE; never legal advice.
    """

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', kind: str = 'custom',
                 scope: str = 'global', app_name: str = '', version: str = '',
                 active: bool = False, requires_acceptance: bool = True,
                 show_bar: bool = False, bar_text: str = '',
                 summary: str = '', body_md: str = '', effective_at: str = '',
                 contact: str = '', notes: str = ''):
        self.name = name
        self.title = title
        self.kind = kind
        self.scope = scope
        self.app_name = app_name
        self.version = version
        self.active = active
        self.requires_acceptance = requires_acceptance
        self.show_bar = show_bar
        self.bar_text = bar_text
        self.summary = summary
        self.body_md = body_md
        self.effective_at = effective_at
        self.contact = contact
        self.notes = notes
