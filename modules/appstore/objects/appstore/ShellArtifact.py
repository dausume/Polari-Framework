"""
@module appstore.objects.appstore.ShellArtifact

Row class ShellArtifact of the appstore module — one class per file (design §7), split
from appstore_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ShellArtifact(treeObject):
    """One deliverable artifact record — the bytes live in MinIO (or
    are overlaid on demand); this row is the manifest + hashes."""

    @treeObjectInit
    def __init__(
        self,
        # '<shell>@<platform>@<version>'.
        name: str = '',
        shell_name: str = '',
        # PLATFORM_KEYS entry.
        platform: str = 'gradle-project',
        version: str = '',
        # 'source-archive' (srcDistTar upload the store overlays) |
        # 'prebuilt-binary' (installDist/apk/... served as-is).
        kind: str = 'source-archive',
        # MinIO location; '' until an upload is committed.
        bucket: str = '',
        object_key: str = '',
        sha256: str = '',
        size_bytes: int = 0,
        # Overlay manifest (path -> sha256) of the last download —
        # the grpcbridge stamp idiom: record what was generated, the
        # artifact itself is rebuilt deterministically.
        manifest_json: str = '{}',
        # Keycloak sub of the admin who uploaded a prebuilt.
        uploaded_by: str = '',
        uploaded_at: str = '',
        last_generated_at: str = '',
        is_prior: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.shell_name = shell_name
        self.platform = platform
        self.version = version
        self.kind = kind
        self.bucket = bucket
        self.object_key = object_key
        self.sha256 = sha256
        self.size_bytes = size_bytes
        self.manifest_json = manifest_json
        self.uploaded_by = uploaded_by
        self.uploaded_at = uploaded_at
        self.last_generated_at = last_generated_at
        self.is_prior = is_prior
        self.notes = notes
