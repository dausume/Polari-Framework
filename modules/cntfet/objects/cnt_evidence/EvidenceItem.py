"""
@module cntfet.objects.cnt_evidence.EvidenceItem

Row class EvidenceItem of the cntfet module — one class per file (design §7), split
from cnt_evidence_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.objects.cnt_evidence._shared import JURISDICTION

class EvidenceItem(treeObject):
    """One piece of evidence (patent / publication / textbook /
    standard / licence / prior-art) with what it PROVES, whether it
    was verified, and which subjects it supports."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        kind: str = 'publication',
        title: str = '',
        parties: str = '',
        ref: str = '',            # patent number / DOI / ISBN / SPDX
        date: str = '',           # ISO (filing / publication / release)
        url: str = '',
        proves: str = 'prior-art-before',
        proves_detail: str = '',
        expiry: str = '',
        jurisdiction: str = JURISDICTION,
        verified: bool = False,
        verified_via: str = '',
        verified_at: str = '',
        licence_bucket: str = '',
        subjects_json: str = '[]',
        citation_key: str = '',   # '[VS1]' etc. — reverse lookup
        # Dustin 2026-08-29 binary: 'reference' = proves our processes /
        # sims make sense (patents, papers, textbooks); 'usable' = an
        # artefact we actually build with (open licences, formats).
        role: str = 'reference',
        role_reason: str = '',
        notes: str = '',
        is_prior: bool = True,
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
        self.expiry = expiry
        self.jurisdiction = jurisdiction
        self.verified = verified
        self.verified_via = verified_via
        self.verified_at = verified_at
        self.licence_bucket = licence_bucket
        self.subjects_json = subjects_json
        self.citation_key = citation_key
        self.notes = notes
        self.role = role
        self.role_reason = role_reason
        self.is_prior = is_prior
