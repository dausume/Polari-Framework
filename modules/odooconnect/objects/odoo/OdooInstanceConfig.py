"""
@module odooconnect.objects.odoo.OdooInstanceConfig

Row class OdooInstanceConfig of the odooconnect module — one class per file (design §7), split
from odoo_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from odooconnect.objects.odoo._shared import ODOO_MODES

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
