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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/video/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from video.objects.video._shared import STATUS_VALUES  # noqa: F401
from video.objects.video.VideoAsset import VideoAsset  # noqa: F401
