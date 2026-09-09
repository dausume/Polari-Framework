"""printcam_selftest — the extension's rows, its provisioner refusals and render, its store plan."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from printcam.printcam_basis import PRINTCAM_CLASSES, SEED_CAMERAS, SEED_PRINTCAM_HARDWARE_APPS, SEED_PRINTCAM_CATALOG, CameraDefinition
    from printcam.custom.provision import render_provision
    from islemesh.islemesh_catalog import install_plan
    check('two row classes', len(PRINTCAM_CLASSES) == 2)
    cam = CameraDefinition(**SEED_CAMERAS[0])
    d = dict(SEED_PRINTCAM_HARDWARE_APPS[0])
    _, r = render_provision(d)
    check('no camera context → refusal naming the host guest', r and 'CameraDefinition' in r[0])
    d['camera'] = {k: getattr(cam, k) for k in vars(cam) if not k.startswith('_') and k != 'manager'}
    _, r = render_provision(d)
    check('no port + unpinned timelapse → two named refusals', len(r) == 2 and 'hwmap' in r[0] and 'PIN ME' in r[1])
    s, r = render_provision(dict(d, passthrough_json='["cam-port"]', allow_unpinned=True))
    check('renders ustreamer unit, moonraker webcam, nginx /webcam/, timelapse include', not r and all(t in s for t in ('ustreamer.service', '[webcam printcam]', 'location /webcam/', 'include timelapse.cfg', '--resolution=1280x720')))
    plan = install_plan(SEED_PRINTCAM_CATALOG[0])
    check('store plan = isle vm extend voron-printer --with printcam', plan['ok'] and 'isle vm extend voron-printer --with printcam' in plan['steps'])
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
