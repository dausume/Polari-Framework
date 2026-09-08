"""
@module polariapps.objects.apps_permissions.AppPermissionProfile

Row class AppPermissionProfile of the polariapps module — one class per file (design §7), split
from apps_permissions_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class AppPermissionProfile(treeObject):
    """One reusable grant bundle: WHICH app (its modules' classes),
    WHICH verbs, granted to WHICH KC groups/roles."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key ('wax-print-shop-operator').
        name: str = '',
        title: str = '',
        description: str = '',
        # PolariAppDefinition.name whose module closure this profile
        # covers ('' = no app derivation; extra_classes_json only).
        app_name: str = '',
        # JSON list of KC group names (leading '/' tolerated) AND/OR
        # realm/client role names that GRANT this profile.
        kc_groups_json: str = '[]',
        # JSON list of CRUDE_VERBS entries this profile allows.
        verbs_json: str = '["read"]',
        # JSON list of class names covered BEYOND the app derivation
        # (or instead of it when app_name is '').
        extra_classes_json: str = '[]',
        published: bool = True,
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.description = description
        self.app_name = app_name
        self.kc_groups_json = kc_groups_json
        self.verbs_json = verbs_json
        self.extra_classes_json = extra_classes_json
        self.published = published
        self.is_prior = is_prior
        self.notes = notes
