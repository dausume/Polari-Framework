"""
@module mech.custom.freecad_motion

FreeCAD Motion as the KINEMATIC reference run (MECH_FREECAD_INTERCHANGE_PLAN
§2 "Verified headless on econ", §3.5, slice mxc-4). Tidied from
~/collab/mech-parts/freecad_motion_probe.py; its 2026-11-03 output is
custom/reference/mfx0_motion_econ.csv + REFERENCE.json.

Runs ONLY under FreeCAD's own interpreter:
    ~/opt/freecad/bin/freecadcmd modules/mech/custom/freecad_motion.py
with the run parameters in the environment (freecadcmd does not pass
script arguments):
    MFX_FORMULA='100*time' MFX_T_END=1.5 MFX_STEP=0.1 MFX_OUT=/path/out.csv
    [MFX_FCSTD=/path/out.FCStd]
`import FreeCAD` happens inside the functions so the framework can import
this module (for `freecad_command`, `csv_sha256`, `read_motion_csv`)
without FreeCAD installed.

What was learned (REFERENCE.json has the evidence):
- Frame 0 is the pre-motion placement; frame f ≥ 1 is t = (f − 1)·step.
  There is no start-up ramp — the plan's "ramp" was the probe's t_s
  column (frame / fps) read one frame off.
- The Motion solver does NOT honour the joint's LengthMax during the run
  (z reaches 300 at t = 3 s with LengthMax 250) — Polari's hard stop is
  the only stop.
- `min()` / `max()` are not in the formula language (0 frames, no error);
  jFramesPerSecond is playback only; joint.Distance is not updated per frame.
- The Python Simulation module is Qt-bound; the objects are built from
  properties (names a..j are the C++ side's property order).

FreeCAD knows no mass, friction or force: this is the position(t) check
of Polari's own engine, never a substitute for it (D-mxc-4). FEM is not
touched here or anywhere in mech (D-mxc-7).

@consumers mech.custom.motion_runs.compare_to_freecad, the FreeCAD worker (isle-core / econ)
"""
import csv
import hashlib
import os

FREECAD_CMD = os.path.expanduser('~/opt/freecad/bin/freecadcmd')
ENGINE_NAME = 'freecad_motion'


def build_slider_fixture(doc, rail_len=300.0, slide_len=50.0, travel_max=250.0, z0=20.0):
    """The mfx-0 probe fixture: a grounded rail box and a slide box joined
    by an Assembly Slider joint (LengthMin 0, LengthMax travel_max). Returns
    (asm, rail, slide, joint). The slide is placed at z0 before solving —
    that placement is what frame 0 of a Motion run shows."""
    import FreeCAD as App
    import JointObject
    rail = doc.addObject('Part::Box', 'Rail')
    rail.Length, rail.Width, rail.Height = rail_len, 20, 20
    slide = doc.addObject('Part::Box', 'Slide')
    slide.Length, slide.Width, slide.Height = slide_len, 20, 20
    slide.Placement.Base = App.Vector(0, 0, z0)
    doc.recompute()
    asm = doc.addObject('Assembly::AssemblyObject', 'Assembly')
    asm.addObject(rail)
    asm.addObject(slide)
    jg = asm.newObject('Assembly::JointGroup', 'Joints')
    g = jg.newObject('App::FeaturePython', 'GroundedJoint')
    JointObject.GroundedJoint(g, rail)
    j = jg.newObject('App::FeaturePython', 'Slider')
    JointObject.Joint(j, JointObject.JointTypes.index('Slider'))   # the INDEX, not the name
    j.Reference1 = [rail, ['Face6']]
    j.Reference2 = [slide, ['Face5']]
    j.Placement1 = App.Placement(App.Vector(0, 10, 20), App.Rotation(App.Vector(0, 1, 0), 90))
    j.Placement2 = App.Placement(App.Vector(0, 10, 0), App.Rotation(App.Vector(0, 1, 0), 90))
    j.EnableLengthMin, j.LengthMin = True, 0
    j.EnableLengthMax, j.LengthMax = True, travel_max
    doc.recompute()
    asm.solve()
    return asm, rail, slide, j


def run_motion(doc, asm, joint, moving_part, formula, t_end, step,
               motion_type='Linear', tolerance=1e-6):
    """Build Simulation + Motion from properties, generate and walk every
    frame. Returns a list of dicts {frame, t_s, x, y, z, joint_distance,
    note}: frame 0 has t_s None and note 'pre-motion placement'; frame
    f ≥ 1 has t_s = (f − 1)·step."""
    sg = asm.newObject('Assembly::SimulationGroup', 'Simulations')
    sim = sg.newObject('App::FeaturePython', 'Simulation')
    sim.addExtension('App::GroupExtensionPython')
    sim.addProperty('App::PropertyTime', 'aTimeStart', 'Simulation', '')
    sim.aTimeStart = 0.0
    sim.addProperty('App::PropertyTime', 'bTimeEnd', 'Simulation', '')
    sim.bTimeEnd = float(t_end)
    sim.addProperty('App::PropertyTime', 'cTimeStepOutput', 'Simulation', '')
    sim.cTimeStepOutput = float(step)
    sim.addProperty('App::PropertyFloat', 'fGlobalErrorTolerance', 'Simulation', '')
    sim.fGlobalErrorTolerance = tolerance
    sim.addProperty('App::PropertyInteger', 'jFramesPerSecond', 'Simulation', '')
    sim.jFramesPerSecond = max(1, int(round(1.0 / float(step))))
    mo = asm.newObject('App::FeaturePython', 'Motion')
    mo.addProperty('App::PropertyXLinkSubHidden', 'Joint', 'Motion', '')
    mo.Joint = joint
    mo.addProperty('App::PropertyString', 'Formula', 'Motion', '')
    mo.Formula = formula
    mo.addProperty('App::PropertyEnumeration', 'MotionType', 'Motion', '')
    mo.MotionType = ['Angular', 'Linear']
    mo.MotionType = motion_type
    grp = sim.Group
    grp.append(mo)
    sim.Group = grp
    doc.recompute()
    rc = asm.generateSimulation(sim)
    n = asm.numberOfFrames()
    if rc != 0 or n == 0:
        raise RuntimeError(f'generateSimulation rc={rc} frames={n} — formula {formula!r} '
                           f'refused? (min/max are not in the formula language)')
    rows = []
    for f in range(n):
        asm.updateForFrame(f)
        doc.recompute()
        b = moving_part.Placement.Base
        rows.append({
            'frame': f,
            't_s': None if f == 0 else round((f - 1) * float(step), 9),
            'x': round(b.x, 6), 'y': round(b.y, 6), 'z': round(b.z, 6),
            'joint_distance': str(joint.Distance),
            'note': 'pre-motion placement' if f == 0 else '',
        })
    return rows


CSV_COLUMNS = ('frame', 't_s', 'x', 'y', 'z', 'joint_distance', 'note')


def write_csv(rows, path):
    with open(path, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: ('' if r.get(k) is None else r.get(k, '')) for k in CSV_COLUMNS})
    return path


def read_motion_csv(path, step_s=None):
    """Read a motion CSV (this module's or the 2026-11-03 probe's). Returns
    a list of {frame, t_s, x, y, z}: t_s is ALWAYS re-derived as
    (frame − 1)·step_s for frame ≥ 1 and None for frame 0, because the
    probe's own t_s column was frame / fps (REFERENCE.json). step_s is
    required for the probe's layout; this module's CSV carries it implicitly."""
    out = []
    with open(path, newline='') as fh:
        for r in csv.DictReader(fh):
            f = int(r['frame'])
            if step_s is None:
                t = None if r.get('t_s', '') in ('', None) else float(r['t_s'])
                if f == 0:
                    t = None
            else:
                t = None if f == 0 else round((f - 1) * float(step_s), 9)
            out.append({'frame': f, 't_s': t, 'x': float(r['x']), 'y': float(r['y']),
                        'z': float(r['z'])})
    return out


def csv_sha256(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def freecad_command(script_path=None, formula='100*time', t_end=1.5, step=0.1, out_csv='motion.csv', fcstd=''):
    """The shell command a worker runs for this reference (econ / isle-core)."""
    script_path = script_path or os.path.abspath(__file__)
    env = (f"MFX_FORMULA='{formula}' MFX_T_END={t_end} MFX_STEP={step} MFX_OUT='{out_csv}'"
           + (f" MFX_FCSTD='{fcstd}'" if fcstd else ''))
    return f'{env} {FREECAD_CMD} {script_path}'


def main():
    import FreeCAD as App
    formula = os.environ.get('MFX_FORMULA', '100*time')
    t_end = float(os.environ.get('MFX_T_END', '1.5'))
    step = float(os.environ.get('MFX_STEP', '0.1'))
    out = os.environ.get('MFX_OUT', 'mfx0_motion.csv')
    doc = App.newDocument('mfx0')
    asm, rail, slide, j = build_slider_fixture(doc)
    rows = run_motion(doc, asm, j, slide, formula, t_end, step)
    write_csv(rows, out)
    for r in rows:
        print('frame %2d t=%s z=%.3f %s' % (r['frame'], r['t_s'], r['z'], r['note']))
    print('csv written', out, csv_sha256(out))
    fcstd = os.environ.get('MFX_FCSTD', '')
    if fcstd:
        doc.saveAs(fcstd)


if __name__ == '__main__' or os.environ.get('MFX_OUT'):
    # freecadcmd executes the script with __name__ != '__main__'; MFX_OUT is
    # the explicit "run me" signal there.
    if os.environ.get('MFX_OUT'):
        main()
