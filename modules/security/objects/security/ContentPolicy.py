"""
@module security.objects.security.ContentPolicy

Row class ContentPolicy of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ContentPolicy(treeObject):
    """The payload policy for one class: a JSON Schema derived from the class's typing and limits (body bytes, array and string lengths, content types); mode derived → observe → enforce (sec-i-3). Derived rows only today."""

    @treeObjectInit
    def __init__(self, name: str = '', app: str = '', target: str = '', mode: str = 'derived', schema_json: str = '', fields: int = 0, max_body_bytes: int = 1048576, max_array: int = 10000, max_string: int = 65536, content_types: str = 'application/json', violations_observed: int = 0, last_tested: str = '', test_verdict: str = ''):
        self.name = name
        self.app = app
        self.target = target
        self.mode = mode
        self.schema_json = schema_json
        self.fields = fields
        self.max_body_bytes = max_body_bytes
        self.max_array = max_array
        self.max_string = max_string
        self.content_types = content_types
        self.violations_observed = violations_observed
        self.last_tested = last_tested
        self.test_verdict = test_verdict
