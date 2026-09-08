"""
@module appstore.objects.appstore.ShellInstallation

Row class ShellInstallation of the appstore module — one class per file (design §7), split
from appstore_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ShellInstallation(treeObject):
    """Audit receipt written at redeem: one registered install."""

    @treeObjectInit
    def __init__(
        self,
        # 'inst-<12 hex>'.
        name: str = '',
        enrollment_name: str = '',
        shell_name: str = '',
        instance_name: str = '',
        platform: str = '',
        device_label: str = '',
        user_sub: str = '',
        registered_at: str = '',
        last_seen_at: str = '',
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.enrollment_name = enrollment_name
        self.shell_name = shell_name
        self.instance_name = instance_name
        self.platform = platform
        self.device_label = device_label
        self.user_sub = user_sub
        self.registered_at = registered_at
        self.last_seen_at = last_seen_at
        self.is_prior = is_prior
        self.notes = notes
