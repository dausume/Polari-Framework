* sky130_fd_pr__nfet_01v8 DC sweeps — Polari lod-4c (Ion / Ioff / Vt / DIBL / SS at stated conditions)
.option scale=1.0e-6
.temp 25.0
.include "/home/user/.cache/polari-lod/sky130_pr/sky130_fd_pr__nfet_01v8__mismatch.corner.spice"
.include "/home/user/.cache/polari-lod/sky130_pr/sky130_fd_pr__nfet_01v8__tt.corner.spice"
Vd d 0 1.8
Vg g 0 0
X1 d g 0 0 sky130_fd_pr__nfet_01v8 w=1000000u l=150000u
.control
dc Vg 0 1.8 0.01
wrdata sat.dat i(Vd)
alter Vd 0.05
dc Vg 0 1.8 0.01
wrdata lin.dat i(Vd)
quit
.endc
.end
