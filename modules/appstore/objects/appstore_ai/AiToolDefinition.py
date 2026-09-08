"""
@module appstore.objects.appstore_ai.AiToolDefinition

Row class AiToolDefinition of the appstore module — one class per file (design §7), split
from appstore_ai_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AiToolDefinition(treeObject):
    """One AI tool as a store citizen: hosting + API family + its
    honest linkage claims + sovereignty facts. Live readiness is
    NEVER stored here — it joins at read time from the managed
    reasoning config (decision 4)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('claude', 'localai').
        name: str = '',
        title: str = '',
        description: str = '',
        # HOSTING_KINDS entry.
        hosting: str = 'remote-intermediary',
        # API_FAMILIES entry.
        api_family: str = 'none',
        # PROVIDER_REGISTRY key when this tool IS a reasoning
        # provider ('' otherwise) — the join key for live readiness.
        provider_name: str = '',
        # JSON list of {kind, status, note} — kind from AI_LINKAGES,
        # status from LINKAGE_STATUSES.
        linkages_json: str = '[]',
        # Decision 6 — sovereignty stated on every tile.
        internet_required: bool = False,
        data_leaves_isle: bool = False,
        # API domain (remote) or container image (local-hosted);
        # '' for built-in.
        source_ref: str = '',
        # ai-6: what HOSTING this tool takes, as data —
        # {"profiles": [{name, cores, ram_mb, disk_mb, gpu, note}]}.
        # '' = nothing to host (remote intermediaries, built-in).
        # Guidance, not guarantees — notes say what each profile
        # actually buys.
        requirements_json: str = '',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.hosting = hosting
        self.api_family = api_family
        self.provider_name = provider_name
        self.linkages_json = linkages_json
        self.internet_required = internet_required
        self.data_leaves_isle = data_leaves_isle
        self.source_ref = source_ref
        self.requirements_json = requirements_json
        self.published = published
        self.is_prior = is_prior
        self.notes = notes
