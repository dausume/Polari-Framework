"""
@module terms.objects.terms.TermsAcceptance

Row class TermsAcceptance of the terms module — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit

SUBJECT_KINDS = ('user', 'anonymous')
METHODS = ('clickwrap',)


class TermsAcceptance(treeObject):
    """One recorded acceptance of one TermsDocument version — the
    clickwrap evidence row. Append-only: never edited, never reused.

    What it records (the elements a clickwrap acceptance is usually
    judged on — this is engineering, not legal advice): WHO (`subject`:
    the logged-in user's id when there is one, else the browser's
    anonymous terms session id; `subject_kind` says which), WHAT
    (`terms_name` + `terms_version` + `body_sha256` of the exact text
    that was displayed), WHEN (`accepted_at`, UTC ISO), HOW (`method`
    clickwrap: an affirmative click on a control that named the terms),
    WHERE (`app_name`, `client_session` for the session it was given in),
    plus a hashed client fingerprint (`client_hash`: sha256 of remote
    address + user agent — never the raw values; the demo terms forbid
    holding personal information, so this module does not either).
    Related concepts: TermsDocument, the terms gate in the frontends.
    """

    @treeObjectInit
    def __init__(self, name: str = '', terms_name: str = '', terms_version: str = '',
                 body_sha256: str = '', subject: str = '', subject_kind: str = 'anonymous',
                 client_session: str = '', app_name: str = '', accepted_at: str = '',
                 method: str = 'clickwrap', client_hash: str = '', notes: str = ''):
        self.name = name
        self.terms_name = terms_name
        self.terms_version = terms_version
        self.body_sha256 = body_sha256
        self.subject = subject
        self.subject_kind = subject_kind
        self.client_session = client_session
        self.app_name = app_name
        self.accepted_at = accepted_at
        self.method = method
        self.client_hash = client_hash
        self.notes = notes
