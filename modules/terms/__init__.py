"""
@module terms

Terms of service, configurable and recorded (his ask 2026-09-09): versioned
TermsDocument rows — global or per app, boilerplate seeded (demo active;
standard and privacy templates off) — and an append-only TermsAcceptance
ledger (who, which version, sha256 of the exact text shown, when, how:
clickwrap). The frontends' terms gate reads /api/terms/active and posts
/api/terms/accept; /terms/<name> serves any document as a plain page.
Requires nothing from other feature modules.
"""
from terms.terms_basis import TERMS_CLASSES, TermsAcceptance, TermsDocument  # noqa: F401
from terms.terms_seed import SEED_TERMS_DOCUMENTS, TERMS_SEED_PAIRS  # noqa: F401
from terms.terms_page import SEED_TERMS_PAGE_DISPLAYS  # noqa: F401
