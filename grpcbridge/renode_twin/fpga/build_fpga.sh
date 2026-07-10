#!/bin/bash
# Build the verilated Polari register block (hwsim-3) as a Renode
# co-simulation binary (socket mode).
#
#   ./build_fpga.sh [POLARI_API_BASE] [RENODE_ROOT]
#
# Fetches the GENERATED artifacts (Verilog core + sim wrapper + the
# co-sim harness) from the running Polari — all derived from the
# RegisterMapDefinition/RegisterDefinition knob rows — then verilates
# them against Renode's own IntegrationLibrary (version-matched, it
# ships inside the Renode portable). Needs verilator on PATH
# (oss-cad-suite tarball works unprivileged).
set -e
cd "$(dirname "$0")"

BASE="${1:-https://api.prf.192.168.0.210.nip.io}"
RENODE_ROOT="${2:-$HOME/tools/renode_1.16.1_portable}"
IL="$RENODE_ROOT/plugins/IntegrationLibrary"

echo "== fetching generated artifacts from $BASE =="
for a in verilog sim-top sim-harness; do
    curl -skf "$BASE/api/hw/registermaps/hardware-runtime/$a" \
        -o "$a.tmp"
done
mv verilog.tmp polari_regblock.v
mv sim-top.tmp top.v
mv sim-harness.tmp sim_main.cpp
grep -q polari_regblock polari_regblock.v \
    || { echo "artifact fetch failed"; exit 1; }

echo "== verilating against $IL =="
# Renode 1.16 loads co-simulated peripherals as SHARED LIBRARIES
# (SimulationFilePathLinux dlopens; initialize_native/handle_request/
# reset_peripheral from renode_bus.cpp are the entry points) — build
# everything -fPIC and relink the objects as libVtop.so.
verilator --cc top.v polari_regblock.v --exe \
    sim_main.cpp \
    "$IL/src/renode_bus.cpp" \
    "$IL/src/buses/bus.cpp" \
    "$IL/src/buses/axilite.cpp" \
    "$IL/src/communication/socket_channel.cpp" \
    "$IL/libs/socket-cpp/Socket/Socket.cpp" \
    "$IL/libs/socket-cpp/Socket/TCPClient.cpp" \
    -CFLAGS "-fPIC -I$IL -I$IL/src -I$IL/src/communication -I$IL/libs/socket-cpp" \
    -o verilated_regblock
make -s -C obj_dir -f Vtop.mk
g++ -shared -o libVtop.so obj_dir/*.o
echo "== libVtop.so ready =="
