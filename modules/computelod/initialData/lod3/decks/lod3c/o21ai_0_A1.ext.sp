* sky130_fd_sc_hd__o21ai_0 pin A1 → Y (negative_unate) on sky130_fd_pr tt — Polari lod-3b/3d/2c
.option scale=1.0e-6
.temp 25.0
.include "/home/user/.cache/polari-lod/sky130_pr/sky130_fd_pr__nfet_01v8__mismatch.corner.spice"
.include "/home/user/.cache/polari-lod/sky130_pr/sky130_fd_pr__nfet_01v8__tt.corner.spice"
.include "/home/user/.cache/polari-lod/sky130_pr/sky130_fd_pr__pfet_01v8_hvt__mismatch.corner.spice"
.include "/home/user/.cache/polari-lod/sky130_pr/sky130_fd_pr__pfet_01v8_hvt__tt.corner.spice"
.include "/tmp/polari-lod3c/sky130_fd_sc_hd__o21ai_0_pex.spice"
VDD vpwr 0 1.8
VSS vgnd 0 0
VA2 a2 0 0
VB1 b1 0 1.8
Xdut a_in a2 b1 vgnd vgnd vpwr vpwr y sky130_fd_sc_hd__o21ai_0
Cload y 0 0.0146p
.save v(a_in) v(y)
Vin a_in 0 pwl(0 0 1.0n 0 1.083333333n 1.8 3.0n 1.8 3.083333333n 0 5.0n 0)
.tran 0.001n 5.0n
.control
run
meas tran tphl trig v(a_in) val=0.9 rise=1 targ v(y) val=0.9 fall=1
meas tran tplh trig v(a_in) val=0.9 fall=1 targ v(y) val=0.9 rise=1
meas tran tfall trig v(y) val=1.4400000000000002 fall=1 targ v(y) val=0.36000000000000004 fall=1
meas tran trise trig v(y) val=0.36000000000000004 rise=1 targ v(y) val=1.4400000000000002 rise=1
quit
.endc
.end
