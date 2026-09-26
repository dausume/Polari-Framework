current_design rv32_add
# a purely combinational adder: ONE virtual clock so the flow constrains and reports the input → output paths (10 ns, generous:
# no setup violation is ever asked for — the flow's repairs are for slew / capacitance / fanout, and hold at the ports)
create_clock -name vclk -period 10.0
set_input_delay 0.0 -clock vclk [all_inputs]
set_output_delay 0.0 -clock vclk [all_outputs]
set_load 0.0146 [all_outputs]
set_input_transition 0.05 [all_inputs]
