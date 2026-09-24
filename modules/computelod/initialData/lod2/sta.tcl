read_liberty sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog rv32_add_sky130.v
link_design rv32_add
set_load 0.0146 [all_outputs]
set_input_transition 0.05 [all_inputs]
report_checks -unconstrained -path_delay max -fields {slew cap input_pins} -digits 4
report_checks -unconstrained -path_delay min -digits 4
