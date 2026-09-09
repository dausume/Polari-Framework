"""@module printcam.printcam_page — /display/printcam (tables + structured panel only)."""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_PRINTCAM_PAGE_DISPLAYS = [
    _page('printcam', 'printcam',
          'Print camera: a USB camera passed into the Voron guest (an extension app) with a streamer, the Mainsail webcam entry and per-print timelapses.',
          'CameraDefinition',
          [_row(0, [_sapi('pc-summary', 0, 12, 'Cameras + readiness', '/api/printcam/summary', pick='cameras')]),
           _row(1, [_table('pc-cams', 0, 6, 'Cameras', 'CameraDefinition', columns='name,hardware_app,printer,streamer,device,width,height,fps,webcam_name,timelapse'),
                    _table('pc-timelapses', 1, 6, 'Timelapses', 'TimelapseRecord', columns='name,camera,print_job,frames,duration_s,sha256,created_at')])]),
]
