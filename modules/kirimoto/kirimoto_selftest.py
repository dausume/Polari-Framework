"""kirimoto_selftest — the isle-app rows, the store row, the pin gate."""
import sys

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    from kirimoto.kirimoto_basis import KIRIMOTO_CLASSES, KIRIMOTO_UPSTREAM, SEED_KIRIMOTO_CATALOG, SEED_SLICER_PROFILES, SlicerProfile
    from kirimoto.custom.build_image import build_command
    from islemesh.islemesh_catalog import install_plan
    check('two row classes', len(KIRIMOTO_CLASSES) == 2)
    cmd, ref = build_command()
    pinned = KIRIMOTO_UPSTREAM['commit'] != '<PIN ME>'
    check('pinned upstream → docker build command with the sha', pinned and cmd and not ref and KIRIMOTO_UPSTREAM['commit'] in ' '.join(cmd))
    check('store row is a mesh-app (container), unpublished while unpinned', SEED_KIRIMOTO_CATALOG[0]['kind'] == 'mesh-app' and SEED_KIRIMOTO_CATALOG[0]['published'] == pinned)
    plan = install_plan(SEED_KIRIMOTO_CATALOG[0])
    check('install plan = isle app deploy with the image + domain', plan['ok'] and any('isle app deploy kirimoto' in s for s in plan['steps']) and any('kirimoto.isle' in s for s in plan['steps']))
    p = SlicerProfile(**SEED_SLICER_PROFILES[0])
    check('device profile derived from the seeded Voron bed, klipper flavour', p.bed_x_mm == 350.0 and p.gcode_flavor == 'klipper')
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
