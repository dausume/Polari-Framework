"""
@module terms.terms_page

/display/terms — the documents an instance requires and the acceptance
ledger. Configured tables + one structured panel; no raw JSON.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_TERMS_PAGE_DISPLAYS = [
    _page(
        'terms', 'terms',
        'Terms of service: the documents this instance requires (global or per app, '
        'versioned; kind demo also turns on the demonstration bar) and the append-only '
        'ledger of acceptances — who (user or anonymous session), which version, the '
        'sha256 of the exact text shown, when, how. Edit a document\'s text, bump its '
        'version, and every visitor is asked again.',
        'TermsDocument',
        [
            _row(0, [
                _sapi('terms-active', 0, 12, 'What a visitor of this instance is asked to accept right now',
                      '/api/terms/active', pick='documents,pending,show_bar'),
            ], min_height=220),
            _row(1, [
                _table('terms-documents', 0, 12, 'Documents (seeded boilerplate: demo active; standard and privacy templates off)',
                       'TermsDocument',
                       columns='name,title,kind,scope,app_name,version,active,requires_acceptance,show_bar,effective_at,contact'),
            ]),
            _row(2, [
                _table('terms-acceptances', 0, 12, 'Acceptances (append-only evidence rows)',
                       'TermsAcceptance',
                       columns='terms_name,terms_version,subject_kind,subject,client_session,app_name,accepted_at,method,body_sha256'),
            ]),
        ]),
]
