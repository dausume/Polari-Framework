"""
@module cntfet.objects.cnt_ip.TechnologyIPRecord

Row class TechnologyIPRecord of the cntfet module — one class per file (design §7), split
from cnt_ip_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cntfet.objects.cnt_ip._shared import REVIEWED_AT

class TechnologyIPRecord(treeObject):
    """One technology (shape / material / process / cell / model /
    tool / format / chemistry) and the IP posture that governs it —
    verdict + reasoning + self-manufacture note as data."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        subject_kind: str = 'process',
        # the row name it governs ('finfet', 'cnt-gaa', 'siemens-tcs',
        # 'cfa', 'vs-model', 'liberty-format', ...)
        subject_ref: str = '',
        ip_kind: str = 'public-domain',
        verdict: str = 'green',
        # JSON list of {number, title, assignee, filed, expiry_est,
        # status, claims_gist, source_url}
        key_patents_json: str = '[]',
        # SPDX id or text (software / formats)
        licence: str = '',
        # our own implementation and ITS licence
        what_we_own: str = '',
        fto_reasoning: str = '',
        self_manufacture_note: str = '',
        jurisdiction: str = 'US',
        verify_next: str = '',
        sources_json: str = '[]',
        confidence: str = 'unverified',
        # Dustin 2026-08-29: 'open-chip-candidate' = something Polari /
        # the OSEB can actually BUILD WITH (subject to the proof);
        # 'reference-only' = cited to validate our processes and
        # simulations, never something we intend to build.
        intended_use: str = 'open-chip-candidate',
        reviewed_at: str = REVIEWED_AT,
        # JSON list of cnt_evidence.EvidenceItem names — the proof
        # chain is a JOIN onto those rows (pat-us-…, pub-…, book-…,
        # std-…, lic-…), never a re-derivation
        evidence_json: str = '[]',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.subject_kind = subject_kind
        self.subject_ref = subject_ref
        self.ip_kind = ip_kind
        self.verdict = verdict
        self.key_patents_json = key_patents_json
        self.licence = licence
        self.what_we_own = what_we_own
        self.fto_reasoning = fto_reasoning
        self.self_manufacture_note = self_manufacture_note
        self.jurisdiction = jurisdiction
        self.verify_next = verify_next
        self.sources_json = sources_json
        self.confidence = confidence
        self.intended_use = intended_use
        self.reviewed_at = reviewed_at
        self.evidence_json = evidence_json
        self.notes = notes
        self.is_prior = is_prior
