"""
@module scoring.objects.credibility_bases.CredibilityClaim

Row class CredibilityClaim of the scoring module — one class per file (design §7), split
from credibility_bases_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CredibilityClaim(treeObject):
    """One person's declared basis for speaking on a domain — a
    credential, a lived-experience relation, a methodological
    competence, an institutional role, or a locality tie. The
    AFFILIATIONS AND CONFLICTS RIDE THE CLAIM and surface inline on
    every stance that speaks from it."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # Contributor row — the person whose standing this is.
        contributor_name: str = '',
        # BASIS_KINDS entry.
        basis_kind: str = '',
        # Optional refinement under the kind (the kind:qualifier
        # convention): professional:'structural-engineering',
        # locality:'resident', impact:'displaced-tenant'.
        qualifier: str = '',
        # ScoreContext / issue names this basis COVERS — professional
        # credibility is PER DOMAIN (an economist's basis does not
        # cover epidemiology); readings mark out-of-scope use.
        domain_scope_json: str = '[]',
        # The claim itself: credential / lived-experience relation /
        # competence statement.
        statement: str = '',
        evidence_url: str = '',
        # The company-scientist disclosure:
        # [{'org', 'relation', 'since'}] — employers, funders.
        affiliations_json: str = '[]',
        # Plain conflict statements.
        declared_conflicts_json: str = '[]',
        # '' or the affirmative ABSENCE claim ('no professional or
        # financial background related to <domain>') — attestable
        # like any claim; readings say 'attested absence of ties'.
        independence_note: str = '',
        status: str = 'claimed',
        status_history_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.contributor_name = contributor_name
        self.basis_kind = basis_kind
        self.qualifier = qualifier
        self.domain_scope_json = domain_scope_json
        self.statement = statement
        self.evidence_url = evidence_url
        self.affiliations_json = affiliations_json
        self.declared_conflicts_json = declared_conflicts_json
        self.independence_note = independence_note
        self.status = status
        self.status_history_json = status_history_json
        self.notes = notes
