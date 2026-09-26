"""
@module mathproofs.objects.mathproofs.ProofMethodReference

Row class ProofMethodReference of the mathproofs module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ProofMethodReference(treeObject):
    """A CITED SOURCE FOR A PROOF METHOD (bp-2e, his ask 2026-09-25: "find academic sources establishing proof types
    are valid … cite them using our currently existing citation methods"). The same citation shape the suite already
    uses for evidence (cntfet's EvidenceItem: kind · title · parties · ref · date · url · proves · citation_key ·
    verified · verified_via): one row per publication, `proves` naming the TIER or VOCABULARY word it underwrites
    (`tier:z3`, `tier:lean`, `vocabulary:witnessed`, …) and `proves_detail` saying in one sentence what the source
    establishes and where it draws the line (a witness is not a proof; a symbolic check is not a theorem; a
    machine-checked proof rests on a small trusted kernel). `verified` is set only when the DOI / URL was resolved
    and the title read back — never on memory."""

    plain_words = ('Each row is a published book or paper that explains why one of our ways of checking a claim can be '
                   'trusted, and what it cannot do. The "proves" column says which checking method (or which word in our '
                   'vocabulary) the source backs up; "verified" says the link was actually opened and read back.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        kind: str = 'publication',   # publication | book | standard | note
        title: str = '',
        parties: str = '',           # authors
        ref: str = '',               # venue, volume, pages, year
        date: str = '',
        url: str = '',               # https://doi.org/… when there is a DOI
        proves: str = '',            # tier:<numeric|interval|sympy|z3|lean> | vocabulary:<word> (csv when several)
        proves_detail: str = '',
        citation_key: str = '',
        verified: bool = False,
        verified_via: str = '',
        verified_at: str = '',
        subjects_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.kind = kind
        self.title = title
        self.parties = parties
        self.ref = ref
        self.date = date
        self.url = url
        self.proves = proves
        self.proves_detail = proves_detail
        self.citation_key = citation_key
        self.verified = verified
        self.verified_via = verified_via
        self.verified_at = verified_at
        self.subjects_json = subjects_json
        self.notes = notes
