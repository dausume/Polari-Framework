"""
@cross-cutting
@module video.video_conversion
@tags @xc:bindings

ffmpeg wrapper for video-1: convert an uploaded source clip to the
fully open-source WebM (VP9+Opus) rendition and an MP4 (H.264+AAC)
fallback, plus an optional single-rendition HLS manifest when a
VideoAsset's adaptive_enabled knob is on.

Capability-honest (materialsScience/ase idiom): ffmpeg is a system
binary (apk add ffmpeg in Dockerfile/Dockerfile.test), not baked into
every environment by assumption. ffmpeg_available() is checked before
any conversion attempt; a missing binary is reported plainly, never
silently skipped or crashed on.

HLS_VARIANTS is a plain list of (name, width, max_bitrate_kbps) rungs.
Today it holds one rendition — the adaptive ladder is designed to grow
by appending rungs here, not by redesigning the conversion or API shape.
"""

import shutil
import subprocess
import json
import os

#: The adaptive-streaming ladder. One rung today (source resolution,
#: no re-scale, capped bitrate) — append more (name, width, kbps) rungs
#: here later for real multi-bitrate ABR; the HLS conversion below
#: already loops over this list.
HLS_VARIANTS = [
    ('src', 0, 2500),  # width=0 means "keep source width" (no scaling)
]

#: ffmpeg exits are checked; the conversion itself is expected to take
#: real wall-clock time for anything beyond a short clip, hence no
#: aggressive timeout here — the caller (video_api) runs this off the
#: request thread.
_FFMPEG_TIMEOUT_SECONDS = 3600


def ffmpeg_available():
    """Whether the ffmpeg binary is on PATH. Check before converting."""
    return shutil.which('ffmpeg') is not None


def probe_video(input_path):
    """Duration (seconds), width, height via ffprobe. Returns a dict;
    zeros + an 'error' key if ffprobe is unavailable or the file can't
    be read — callers treat that as 'unknown', not a hard failure."""
    if shutil.which('ffprobe') is None:
        return {'duration_seconds': 0.0, 'width': 0, 'height': 0,
                'error': 'ffprobe not available'}
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'error', '-print_format', 'json',
             '-show_format', '-show_streams', input_path],
            capture_output=True, text=True, timeout=60, check=True,
        )
        data = json.loads(out.stdout or '{}')
        duration = float((data.get('format') or {}).get('duration', 0.0) or 0.0)
        width = height = 0
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                width = int(stream.get('width', 0) or 0)
                height = int(stream.get('height', 0) or 0)
                break
        return {'duration_seconds': duration, 'width': width, 'height': height}
    except Exception as err:
        return {'duration_seconds': 0.0, 'width': 0, 'height': 0, 'error': str(err)}


def convert_to_webm(input_path, output_path):
    """VP9 video + Opus audio — the fully open-source codec stack.
    Raises RuntimeError with ffmpeg's stderr on failure."""
    _run_ffmpeg([
        'ffmpeg', '-y', '-i', input_path,
        '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '32', '-row-mt', '1',
        '-c:a', 'libopus', '-b:a', '128k',
        output_path,
    ])


def convert_to_mp4(input_path, output_path):
    """H.264 video + AAC audio — the universal-compatibility fallback.
    +faststart moves the moov atom forward so playback can start before
    the full file downloads (progressive Range-based streaming)."""
    _run_ffmpeg([
        'ffmpeg', '-y', '-i', input_path,
        '-c:v', 'libx264', '-crf', '23', '-preset', 'medium',
        '-c:a', 'aac', '-b:a', '128k',
        '-movflags', '+faststart',
        output_path,
    ])


def extract_poster(input_path, output_path, at_seconds=1.0):
    """A single JPEG frame near the start, for the player's poster image."""
    _run_ffmpeg([
        'ffmpeg', '-y', '-ss', str(at_seconds), '-i', input_path,
        '-frames:v', '1', '-q:v', '3',
        output_path,
    ])


def convert_to_hls(input_path, output_dir, variants=None):
    """Single- (or, once HLS_VARIANTS grows, multi-) rendition HLS: one
    .m3u8 master playlist + per-variant playlists/segments under
    output_dir. Returns the master playlist's filename (relative to
    output_dir) to upload alongside the segments.

    Only called when a VideoAsset's adaptive_enabled knob is True —
    this is the expandable-later half of the adaptive capability; the
    ladder (HLS_VARIANTS) is the extension point, not this function.
    """
    os.makedirs(output_dir, exist_ok=True)
    variants = variants or HLS_VARIANTS
    master_entries = []
    for variant_name, width, max_kbps in variants:
        variant_dir = os.path.join(output_dir, variant_name)
        os.makedirs(variant_dir, exist_ok=True)
        scale_args = [] if width <= 0 else ['-vf', f'scale={width}:-2']
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            *scale_args,
            '-c:v', 'libx264', '-crf', '23', '-preset', 'medium',
            '-b:v', f'{max_kbps}k', '-maxrate', f'{max_kbps}k',
            '-bufsize', f'{max_kbps * 2}k',
            '-c:a', 'aac', '-b:a', '128k',
            '-hls_time', '6', '-hls_playlist_type', 'vod',
            '-hls_segment_filename', os.path.join(variant_dir, 'seg_%04d.ts'),
            os.path.join(variant_dir, 'playlist.m3u8'),
        ]
        _run_ffmpeg(cmd)
        master_entries.append(
            f'#EXT-X-STREAM-INF:BANDWIDTH={max_kbps * 1000},NAME="{variant_name}"\n'
            f'{variant_name}/playlist.m3u8\n'
        )

    master_path = os.path.join(output_dir, 'master.m3u8')
    with open(master_path, 'w') as fh:
        fh.write('#EXTM3U\n#EXT-X-VERSION:3\n')
        fh.writelines(master_entries)
    return 'master.m3u8'


def _run_ffmpeg(cmd):
    if not ffmpeg_available():
        raise RuntimeError(
            'ffmpeg is not available on this instance — video conversion '
            'is disabled until the ffmpeg package is installed.')
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=_FFMPEG_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg failed ({" ".join(cmd)}): {result.stderr[-2000:]}')
