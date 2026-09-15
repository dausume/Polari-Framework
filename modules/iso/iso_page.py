"""
@module iso.iso_page

/display/iso — the ISO arc's screen inside Polari (configured tables and structured readings, no raw JSON): the
bases and their cache state, the probed computers with their verdicts and suggested roles, the images built and
their pool holds. The human door for the public is /downloads/iso (server-rendered, logged out).
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_ISO_PAGE_DISPLAYS = [
    _page('iso', 'iso', 'New computers: probe, choose, install', 'IsoBuild', [
        _row(0, [
            _sapi('iso-summary', 0, 4, 'Bases cached, probes, images, the ISO pool and the tools on this instance', '/api/iso', pick='bases,probes,builds,pool,tools,platform_debs'),
            _table('iso-probes', 1, 8, 'Probed computers: what the stick found, the derived verdict, the suggested role', 'DeviceProbe',
                   columns='label,os_name,cpu,memory_gb,firmware,secure_boot,tpm,disk_encryption,verdict,verdict_text,suggested_role,probed_at'),
        ]),
        _row(1, [
            _table('iso-builds', 0, 8, 'Images: role, shape, options, state, file', 'IsoBuild',
                   columns='name,base,role,shape,posture,look,encryption,secure_boot,target_hash,state,step,refusal,bytes,requested_at'),
            _table('iso-bases', 1, 4, 'Ubuntu bases this instance can build from', 'IsoBase', columns='name,release,arch,default,note'),
        ]),
    ]),
]
