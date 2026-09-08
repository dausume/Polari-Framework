"""
@cross-cutting
@module video.video_basis
@tags @xc:bindings

Self-hosted video (video-1): a VideoAsset is a source clip uploaded to
object storage (MinIO/S3-compatible) plus its converted renditions.
Conversion produces the fully open-source WebM (VP9+Opus) rendition and
a widely-compatible MP4 (H.264+AAC) fallback; both stream progressively
via HTTP Range requests, no extra player infrastructure required.

Adaptive (HLS) delivery is an explicit per-asset knob (adaptive_enabled),
off by default — never auto-applied. When turned on, conversion also
produces a single-rendition HLS manifest; the ladder is a plain list
(HLS_VARIANTS in video_conversion.py) so more bitrate rungs can be added
later without changing this class or the API shape.

One treeObject (auto-CRUDE + persisted — object-coherence):

  VideoAsset   a video's identity, storage location, per-format
               readiness, and the adaptive knob.

@consumers
  - polariApiServer.polariServer.defClassList (auto-CRUDE + persistence)
  - video.video_api (presigned URLs, conversion trigger)
  - video.custom.video_conversion (ffmpeg wrapper)
@see objectStorageAPI.py, polariDBmanagement/managedObjectStore.py
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Lifecycle of a VideoAsset's conversion.
STATUS_VALUES = ('pending', 'converting', 'ready', 'failed')


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
