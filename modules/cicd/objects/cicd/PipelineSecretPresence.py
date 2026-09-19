"""
@module cicd.objects.cicd.PipelineSecretPresence

Row class PipelineSecretPresence of the cicd module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PipelineSecretPresence(treeObject):
    """PRESENCE, NEVER A VALUE (ci-7 (C), his ask 2026-09-19: *"the secrets involved in it are only
    accessible via either sudo or the pipeline process itself, never a third party."*).

    One row per secret NAME the pipeline can need. `present` is a BOOLEAN the device reports; the value
    itself never leaves `/etc/polari-jenkins/secrets` (root:polari-ci 0640) and never reaches Polari, a log,
    a page or an API answer. `where_to_get` is the URL or the generate command from `pol jenkins setup`
    step 4 — the one thing a person actually needs from a screen.

    THE CLASS CARRIES NO COLUMN THAT COULD HOLD A VALUE, and that is asserted rather than assumed: the
    selftest walks `__init__`'s parameters and fails on any name matching value/token/key/secret/password/
    credential (except the presence booleans and the *names* themselves), and the ingest door refuses any
    body carrying such a field instead of quietly dropping it. A dropped field is a leak that happened to
    miss; a refusal is a leak that could not start.
    """

    #: how a person obtains one
    KINDS = ('paste', 'generated', 'optional', 'blocked')

    @treeObjectInit
    def __init__(self, name: str = '', device: str = '', area: str = '', secret_name: str = '',
                 present: bool = False, kind: str = 'paste', needed_by_json: str = '[]',
                 where_to_get: str = '', how_to_make: str = '', blocked_why: str = '',
                 last_checked: str = '', posted_by: str = ''):
        self.name = name                    # the row id — <device>:<area>/<secret_name>
        self.device = device                # PipelineDevice.name
        self.area = area                    # github | registries | signing | ssh | admin
        self.secret_name = secret_name      # the file NAME inside the area — never its content
        self.present = present              # the device saw a non-empty file. That is ALL this row knows.
        self.kind = kind                    # KINDS
        self.needed_by_json = needed_by_json    # the routes that go DRY without it
        self.where_to_get = where_to_get    # a URL (paste) — pol jenkins setup step 4's table
        self.how_to_make = how_to_make      # a generate command (generated) — never its output
        self.blocked_why = blocked_why      # why it may not be armed yet (the Keycloak rotation, CICD §5.4)
        self.last_checked = last_checked
        self.posted_by = posted_by
