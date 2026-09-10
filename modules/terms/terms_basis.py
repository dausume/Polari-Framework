"""
@module terms.terms_basis

The INDEX of terms rows (design §7): classes live one-per-file under
objects/terms/; this file re-exports them and names the class list.
"""
from terms.objects.terms._shared import KINDS, METHODS, SCOPES, SUBJECT_KINDS  # noqa: F401
from terms.objects.terms.TermsDocument import TermsDocument  # noqa: F401
from terms.objects.terms.TermsAcceptance import TermsAcceptance  # noqa: F401

TERMS_CLASSES = [TermsDocument, TermsAcceptance]
