"""
@module collab.objects.collab.MeetingRecord

Row class MeetingRecord of the collab module — one class per file (design §7), split
from collab_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MeetingRecord(treeObject):
    """What a meeting DECIDED — the durable, consented trace.
    Participants, decisions, artifact links. No audio, by design."""

    @treeObjectInit
    def __init__(self, name='', session_name='', started_at='',
                 ended_at='', participants_json='[]',
                 decisions_json='[]', artifact_links_json='[]',
                 notes='', manager=None):
        self.name = name
        self.session_name = session_name
        self.started_at = started_at
        self.ended_at = ended_at
        # [{identity, source}] — who was present, per the token log,
        # not per anything that arrived over the media plane.
        self.participants_json = participants_json
        # [{decision, decided_by, ref}] — refs point at proposals/
        # provenance entries; the record CITES commits, it never IS one.
        self.decisions_json = decisions_json
        # [{kind, name}] — rows/assets a meeting produced or discussed.
        self.artifact_links_json = artifact_links_json
        self.notes = notes
