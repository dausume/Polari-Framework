"""
@module video.objects.video.VideoAsset

Row class VideoAsset of the video module — one class per file (design §7), split
from video_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class VideoAsset(treeObject):
    """A self-hosted video: source upload + converted renditions."""

    @treeObjectInit
    def __init__(self, name='', display_name='', bucket='prf-videos',
                 source_key='', webm_key='', mp4_key='', poster_key='',
                 hls_master_key='', status='pending', error_message='',
                 duration_seconds=0.0, width=0, height=0,
                 adaptive_enabled=False, manager=None):
        self.name = name
        self.display_name = display_name
        self.bucket = bucket
        # Original uploaded file (browser -> MinIO via a presigned PUT URL).
        self.source_key = source_key
        # Converted renditions — populated by video_conversion once ready.
        self.webm_key = webm_key
        self.mp4_key = mp4_key
        self.poster_key = poster_key
        # Only populated when adaptive_enabled and conversion has run.
        self.hls_master_key = hls_master_key
        self.status = status  # STATUS_VALUES
        self.error_message = error_message
        self.duration_seconds = duration_seconds
        self.width = width
        self.height = height
        # The adaptive-streaming knob: explicit, off by default, never
        # auto-applied. Flip to True to have conversion also produce an
        # HLS rendition for this asset.
        self.adaptive_enabled = adaptive_enabled
