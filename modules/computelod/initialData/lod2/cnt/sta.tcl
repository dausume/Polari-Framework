read_liberty polari_cnt_lib.lib
read_verilog rv32_add_cnt.v
link_design rv32_add
set_load 0.0417 [all_outputs]
set_input_transition 1.0178 [all_inputs]
report_checks -unconstrained -path_delay max -fields {slew cap input_pins} -digits 4
report_checks -unconstrained -path_delay min -digits 4
