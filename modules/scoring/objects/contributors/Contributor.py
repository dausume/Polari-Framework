"""
@module scoring.objects.contributors.Contributor

Row class Contributor of the scoring module — one class per file (design §7), split
from contributors_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class Contributor(treeObject):
    """One accountable contribution identity (real or pseudonymous)."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key — for pseudonymous contributors this
        # IS the pseudonym ('watchdog-42').
        name: str = '',
        display_name: str = '',
        # CONTRIBUTOR_KINDS entry.
        kind: str = 'individual',
        # Pseudonymous = no real-world identity attached; the track
        # record still accrues to this row. Default True — identity
        # disclosure is opt-in, never assumed.
        pseudonymous: bool = True,
        # Optional identity anchor when disclosed (JSON objectRef or
        # {'kind': 'external', 'url'/'orcid'/'ein': ...}). Empty for
        # pseudonymous rows.
        identity_ref_json: str = '',
        # Other contributor names this one is affiliated with (JSON
        # list) — an individual funded by / working for a lobby is a
        # visible edge, not hidden.
        affiliations_json: str = '[]',
        description: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.kind = kind
        self.pseudonymous = pseudonymous
        self.identity_ref_json = identity_ref_json
        self.affiliations_json = affiliations_json
        self.description = description
        self.notes = notes
