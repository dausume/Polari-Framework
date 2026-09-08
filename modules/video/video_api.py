"""
@cross-cutting
@module video.video_api
@tags @xc:bindings

HTTP surface for video-1 (self-hosted video). VideoAsset rows are plain
CRUDE (object-coherence) for create/list/read via the generic /VideoAsset
endpoint. Deletion is NOT plain CRUDE — see DELETE below. This module
adds what CRUDE can't:

  GET  /api/video/capability
        whether ffmpeg is available on this instance (capability-honest).
  GET  /api/video/assets/{name}/upload-url?ext=mp4
        a presigned PUT URL the browser uploads the source file to
        directly (bytes never pass through this backend).
  POST /api/video/assets/{name}/convert
        kicks off WebM + MP4 conversion (+ HLS if adaptive_enabled) in a
        background thread against the uploaded source; returns
        immediately with status='converting'. Poll status via CRUDE
        GET /VideoAsset (or GET .../status below).
  GET  /api/video/assets/{name}/status
        current VideoAsset status (thin CRUDE-equivalent convenience).
  GET  /api/video/assets/{name}/stream-url?format=webm|mp4|hls|poster
        the direct playback URL for a ready rendition.
  DELETE /api/video/assets/{name}
        THE way to delete a VideoAsset — removes its storage objects
        (source, webm, mp4, poster, every HLS segment under its hls/
        prefix) THEN the row itself, via manager.deleteTreeNode (the same
        mechanism generic CRUDE delete uses). The framework has no
        per-class delete hook (checked: polariCRUDE.on_delete is
        class-agnostic), so a raw CRUDE `DELETE /VideoAsset` bypasses
        this and orphans the asset's storage objects — always use this
        route, not the generic one.

The video bucket is public-read (see managedObjectStore.set_public_read_policy)
so HLS manifests/segments are directly fetchable without presigning every
segment; uploads still require the presigned PUT above. This is a
deliberate tradeoff for a content-hub use case, not a private-video store.

@consumers
  - PRF video-player Angular component (video.service.ts)
@see video.video_basis, video.custom.video_conversion, objectStorageAPI.py
"""

import os
import shutil
import tempfile
import threading

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from video.custom.video_conversion import (
    ffmpeg_available, probe_video, convert_to_webm, convert_to_mp4,
    extract_poster, convert_to_hls,
)

_UPLOAD_URL_EXPIRES_SECONDS = 3600


class VideoAPI(treeObject):
    """video-1 endpoints."""

    @treeObjectInit
    def __init__(self, polServer, manager=None):
        self.polServer = polServer
        self.apiName = '/api/video'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/video/capability', self, suffix='capability')
            add('/api/video/assets/{name}/upload-url', self, suffix='upload_url')
            add('/api/video/assets/{name}/convert', self, suffix='convert')
            add('/api/video/assets/{name}/status', self, suffix='status')
            add('/api/video/assets/{name}/stream-url', self, suffix='stream_url')
            add('/api/video/assets/{name}', self, suffix='asset')

    # ---- helpers ----------------------------------------------------

    def _store(self):
        return getattr(self.manager, 'objectStore', None)

    def _table(self):
        return (self.manager.objectTables or {}).get('VideoAsset', {})

    def _find(self, name):
        for row in self._table().values():
            if getattr(row, 'name', '') == name:
                return row
        return None

    def _save(self, row):
        try:
            self.manager.db.saveInstanceInDB(row)
        except Exception:
            pass  # in-memory row stays authoritative until next save

    def _refuse(self, response, error, status=falcon.HTTP_400):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def _public_url(self, bucket, object_name):
        base = (os.environ.get('MINIO_PUBLIC_URL') or '').rstrip('/')
        if not base:
            return None
        return f'{base}/{bucket}/{object_name}'

    def _key(self, asset, *parts):
        return '/'.join(['videos', asset.name, *parts])

    # ---- routes -------------------------------------------------------

    def on_get_capability(self, request, response):
        response.media = {'ok': True, 'ffmpegAvailable': ffmpeg_available()}

    def on_get_upload_url(self, request, response, name):
        store = self._store()
        if store is None or not store.connected:
            return self._refuse(response, 'Object storage not connected', falcon.HTTP_503)
        asset = self._find(name)
        if asset is None:
            return self._refuse(response, f'no VideoAsset named {name!r}', falcon.HTTP_404)

        ext = (request.params or {}).get('ext', 'mp4').lstrip('.')
        source_key = self._key(asset, f'source.{ext}')
        try:
            store.ensure_bucket(asset.bucket)
            store.set_public_read_policy(asset.bucket)
            upload_url = store.presigned_put_url(
                asset.bucket, source_key, expires_seconds=_UPLOAD_URL_EXPIRES_SECONDS)
        except Exception as err:
            return self._refuse(response, str(err), falcon.HTTP_500)

        asset.source_key = source_key
        asset.status = 'pending'
        self._save(asset)
        response.media = {'ok': True, 'uploadUrl': upload_url, 'sourceKey': source_key}

    def on_get_status(self, request, response, name):
        asset = self._find(name)
        if asset is None:
            return self._refuse(response, f'no VideoAsset named {name!r}', falcon.HTTP_404)
        response.media = {
            'ok': True, 'status': asset.status, 'errorMessage': asset.error_message,
            'durationSeconds': asset.duration_seconds, 'width': asset.width,
            'height': asset.height,
        }

    def on_get_stream_url(self, request, response, name):
        asset = self._find(name)
        if asset is None:
            return self._refuse(response, f'no VideoAsset named {name!r}', falcon.HTTP_404)
        fmt = (request.params or {}).get('format', 'mp4')
        key_by_format = {
            'webm': asset.webm_key, 'mp4': asset.mp4_key,
            'poster': asset.poster_key,
            'hls': self._key(asset, 'hls', asset.hls_master_key) if asset.hls_master_key else '',
        }
        key = key_by_format.get(fmt, '')
        if not key:
            return self._refuse(response, f'{fmt!r} rendition not ready for {name!r}', falcon.HTTP_404)
        url = self._public_url(asset.bucket, key)
        if not url:
            return self._refuse(
                response,
                'MINIO_PUBLIC_URL is not configured on this instance — '
                'cannot construct a browser-reachable playback URL.',
                falcon.HTTP_500)
        response.media = {'ok': True, 'url': url, 'format': fmt}

    def on_delete_asset(self, request, response, name):
        asset = self._find(name)
        if asset is None:
            return self._refuse(response, f'no VideoAsset named {name!r}', falcon.HTTP_404)

        store = self._store()
        removed = 0
        if store is not None and store.connected:
            for key in (asset.source_key, asset.webm_key, asset.mp4_key, asset.poster_key):
                if key and store.remove_object(asset.bucket, key):
                    removed += 1
            removed += store.remove_prefix(asset.bucket, self._key(asset, 'hls') + '/')

        try:
            instances_deleted, migrated = self.manager.deleteTreeNode(
                className='VideoAsset', nodePolariId=asset.id)
        except Exception as err:
            return self._refuse(
                response, f'storage objects removed ({removed}) but row delete '
                f'failed: {err}', falcon.HTTP_500)

        response.media = {
            'ok': True, 'objectsRemoved': removed,
            'instancesDeleted': instances_deleted, 'migratedInstances': migrated,
        }

    def on_post_convert(self, request, response, name):
        if not ffmpeg_available():
            return self._refuse(
                response, 'ffmpeg is not available on this instance', falcon.HTTP_503)
        store = self._store()
        if store is None or not store.connected:
            return self._refuse(response, 'Object storage not connected', falcon.HTTP_503)
        asset = self._find(name)
        if asset is None:
            return self._refuse(response, f'no VideoAsset named {name!r}', falcon.HTTP_404)
        if not asset.source_key:
            return self._refuse(response, 'no source uploaded yet', falcon.HTTP_400)
        if asset.status == 'converting':
            response.media = {'ok': True, 'status': 'converting', 'note': 'already running'}
            return

        asset.status = 'converting'
        asset.error_message = ''
        self._save(asset)

        thread = threading.Thread(
            target=self._run_conversion, args=(asset.name,), daemon=True)
        thread.start()
        response.media = {'ok': True, 'status': 'converting'}

    # ---- background conversion ----------------------------------------

    def _run_conversion(self, asset_name):
        """Runs off the request thread — downloads the source, converts,
        uploads renditions, updates the VideoAsset row. Never raises past
        this point; failures are recorded on the row (status='failed',
        error_message set) rather than lost in a background exception.
        """
        store = self._store()
        asset = self._find(asset_name)
        if asset is None or store is None:
            return
        workdir = tempfile.mkdtemp(prefix='video-convert-')
        try:
            _, ext = os.path.splitext(asset.source_key)
            source_path = os.path.join(workdir, f'source{ext or ".mp4"}')
            store.download_file(asset.bucket, asset.source_key, source_path)

            probe = probe_video(source_path)
            asset.duration_seconds = probe.get('duration_seconds', 0.0)
            asset.width = probe.get('width', 0)
            asset.height = probe.get('height', 0)

            webm_path = os.path.join(workdir, 'video.webm')
            convert_to_webm(source_path, webm_path)
            webm_key = self._key(asset, 'video.webm')
            store.upload_file(asset.bucket, webm_key, webm_path, content_type='video/webm')
            asset.webm_key = webm_key

            mp4_path = os.path.join(workdir, 'video.mp4')
            convert_to_mp4(source_path, mp4_path)
            mp4_key = self._key(asset, 'video.mp4')
            store.upload_file(asset.bucket, mp4_key, mp4_path, content_type='video/mp4')
            asset.mp4_key = mp4_key

            poster_path = os.path.join(workdir, 'poster.jpg')
            extract_poster(source_path, poster_path)
            poster_key = self._key(asset, 'poster.jpg')
            store.upload_file(asset.bucket, poster_key, poster_path, content_type='image/jpeg')
            asset.poster_key = poster_key

            if asset.adaptive_enabled:
                hls_dir = os.path.join(workdir, 'hls')
                master_name = convert_to_hls(source_path, hls_dir)
                for root, _dirs, files in os.walk(hls_dir):
                    for fname in files:
                        local_path = os.path.join(root, fname)
                        rel = os.path.relpath(local_path, hls_dir)
                        content_type = 'application/vnd.apple.mpegurl' if fname.endswith('.m3u8') \
                            else 'video/mp2t'
                        store.upload_file(
                            asset.bucket, self._key(asset, 'hls', rel), local_path,
                            content_type=content_type)
                asset.hls_master_key = master_name

            store.set_public_read_policy(asset.bucket)
            asset.status = 'ready'
            asset.error_message = ''
        except Exception as err:
            asset.status = 'failed'
            asset.error_message = str(err)
        finally:
            self._save(asset)
            shutil.rmtree(workdir, ignore_errors=True)
