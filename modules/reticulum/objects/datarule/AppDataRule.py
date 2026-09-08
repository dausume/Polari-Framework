"""
@module reticulum.objects.datarule.AppDataRule

Row class AppDataRule of the reticulum module — one class per file (design §7), split
from datarule_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AppDataRule(treeObject):
    """What one consumer may submit to one app, per unit time —
    the inbound admission policy of the mesh tier. No enabled
    rule = nothing accepted (refused, not defaulted)."""

    @treeObjectInit
    def __init__(self, name='', app_name='', relay_name='',
                 max_submission_bytes=2048,
                 max_submissions_per_window=10, window_seconds=3600,
                 schema_json='{}', allow_extra_fields=False,
                 dedupe_field='', enabled=False, notes='',
                 manager=None):
        self.name = name
        self.app_name = app_name
        self.relay_name = relay_name
        self.max_submission_bytes = max_submission_bytes
        self.max_submissions_per_window = max_submissions_per_window
        self.window_seconds = window_seconds
        # {'field': 'str|int|float|bool|dict|list', ...} — STRICT:
        # unmatched fields refuse unless allow_extra_fields.
        self.schema_json = schema_json
        self.allow_extra_fields = allow_extra_fields
        # ballot-box semantics: one submission per identity per value
        # of this payload field ('' = no dedupe).
        self.dedupe_field = dedupe_field
        self.enabled = enabled
        self.notes = notes
