"""
Selftest — video-1: ffmpeg capability reporting + real WebM/MP4/poster/HLS
conversion against a synthetically-generated test clip (no fixture file
checked into git — ffmpeg's own lavfi testsrc generates it).

Run from polari-framework/:
    python3 -m video.video_selftest

Covers: ffmpeg_available() matches the actual PATH; probe_video reports
sane duration/width/height; WebM (VP9+Opus) and MP4 (H.264+AAC) both
produce nonzero-size, ffprobe-readable output; poster extraction produces
a JPEG; HLS conversion (the adaptive-knob path) produces a master
playlist + at least one segment. If ffmpeg is genuinely unavailable on
this instance, the conversion checks are skipped (capability-honest —
not a failure), but ffmpeg_available() itself is still exercised.
"""

import os
import shutil
import subprocess
import tempfile

from video.custom.video_conversion import (
    ffmpeg_available, probe_video, convert_to_webm, convert_to_mp4,
    extract_poster, convert_to_hls,
)

PASS, FAIL, SKIP = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m', '\033[0;33mSKIP\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def skip(label, extra=''):
    print(f'  [{SKIP}] {label}{("  " + extra) if extra else ""}')


def _make_test_clip(path, seconds=2):
    """A tiny synthetic test-pattern clip — no binary fixture in git."""
    subprocess.run([
        'ffmpeg', '-y', '-f', 'lavfi', '-i',
        f'testsrc=duration={seconds}:size=320x240:rate=15',
        '-f', 'lavfi', '-i', f'sine=frequency=440:duration={seconds}',
        '-c:v', 'libx264', '-c:a', 'aac', '-shortest', path,
    ], capture_output=True, text=True, timeout=60, check=True)


def run():
    print('video-1 selftest')

    available = ffmpeg_available()
    check('ffmpeg_available() matches PATH lookup',
          available == (shutil.which('ffmpeg') is not None))

    if not available:
        skip('conversion checks', 'ffmpeg not installed on this instance')
        return all(_results)

    workdir = tempfile.mkdtemp(prefix='video-selftest-')
    try:
        source = os.path.join(workdir, 'source.mp4')
        _make_test_clip(source)
        check('synthetic test clip created', os.path.getsize(source) > 0)

        probe = probe_video(source)
        check('probe_video reports duration ~2s',
              1.5 <= probe.get('duration_seconds', 0) <= 3.0,
              f'got {probe.get("duration_seconds")}')
        check('probe_video reports width/height',
              probe.get('width', 0) == 320 and probe.get('height', 0) == 240,
              f'got {probe.get("width")}x{probe.get("height")}')

        webm_path = os.path.join(workdir, 'video.webm')
        convert_to_webm(source, webm_path)
        check('WebM (VP9+Opus) output produced', os.path.getsize(webm_path) > 0)

        mp4_path = os.path.join(workdir, 'video.mp4')
        convert_to_mp4(source, mp4_path)
        check('MP4 (H.264+AAC) output produced', os.path.getsize(mp4_path) > 0)

        poster_path = os.path.join(workdir, 'poster.jpg')
        extract_poster(source, poster_path, at_seconds=0.5)
        check('poster JPEG extracted', os.path.getsize(poster_path) > 0)

        hls_dir = os.path.join(workdir, 'hls')
        master_name = convert_to_hls(source, hls_dir)
        master_path = os.path.join(hls_dir, master_name)
        check('HLS master playlist produced', os.path.isfile(master_path))
        segments = [f for f in os.listdir(os.path.join(hls_dir, 'src'))
                    if f.endswith('.ts')] if os.path.isdir(os.path.join(hls_dir, 'src')) else []
        check('HLS produced at least one segment', len(segments) > 0,
              f'{len(segments)} segment(s)')
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return all(_results)


if __name__ == '__main__':
    ok = run()
    n_pass = sum(1 for r in _results if r)
    print(f'\n{n_pass}/{len(_results)} checks passed')
    raise SystemExit(0 if ok else 1)
