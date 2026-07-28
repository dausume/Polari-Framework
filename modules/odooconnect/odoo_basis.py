"""
@module odooconnect.odoo_basis

OdooInstanceConfig — one row per Odoo endpoint the framework may talk
to (ODOO_INTEGRATION_PLAN.md od-3). THE HARD INVARIANT lives here as
data: every row carries mode 'simulation' | 'operations', and the
client layer (odoo_client) refuses writes on any handle whose row does
not explicitly allow them. Secrets NEVER sit in a row — auth_password_env
names the environment variable that holds the RPC password/api-key.

@consumers
  - polariServer defClassList + seed_pairs (SEED_ODOO_INSTANCES)
  - odooconnect.odoo_client (handles), odooconnect.odoo_analysis
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: The two legal modes — nothing that holds an operations handle may
#: ever be driven by a simulation.
ODOO_MODES = ('simulation', 'operations')


class OdooInstanceConfig(treeObject):
    """A named Odoo endpoint: where it is, which database, which mode,
    and the write knobs. push_enabled defaults False; operations rows
    ALSO require the typed confirmation phrase on every write call
    (the gm-6 discipline) — flipping the knob alone is not enough."""

    @treeObjectInit
    def __init__(self, name='', display_name='', base_url='', db='',
                 mode='simulation', url_env='', auth_login='',
                 auth_password_env='', push_enabled=False,
                 read_only=False, is_prior=True, provenance_id='',
                 notes='', manager=None):
        self.name = name
        self.display_name = display_name
        #: In-network default (compose DNS); url_env names an env var
        #: that OVERRIDES it when set (knob beats row, engines ladder).
        self.base_url = base_url
        self.db = db
        self.mode = mode if mode in ODOO_MODES else 'simulation'
        self.url_env = url_env
        self.auth_login = auth_login
        #: NAME of the env var holding the secret — never the secret.
        self.auth_password_env = auth_password_env
        self.push_enabled = push_enabled
        self.read_only = read_only
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
