# hwsim-1 — the Renode MCU twin

Real compiled firmware on a Renode-simulated STM32F4, speaking the
universal PolariPacket over USART2, exposed to the host as a pty —
the EXISTING Polari Hardware Bridge (`source=serial`) reads it with
zero bridge changes. See `HARDWARE_SIMULATION_PLAN.md` (suite root).

Modularity: the firmware knows ONLY the one class its rig needs —
`simrigstate_packets.h` is fetched per class from
`/api/grpc/exposures/SimRigState/c-header` (generated from the SAME
contract field_map as the .proto and the Java codec).

## Run the ladder

```bash
# 1. firmware (needs arm-none-eabi-gcc; xPack tarball works unprivileged)
./firmware/build.sh https://api.prf.<ip>.nip.io

# 2. the simulated MCU (Renode portable tarball)
renode --disable-gui --console -e "include @sim_rig.resc"
#    -> /tmp/renode-rig-uart appears

# 3. point a bridge at it (the sim->real knob, one configure)
#    POST /api/grpc/bridges  {bridgeName: renode-rig,
#      classes: [SimRigState], source: serial,
#      serialDevice: /tmp/renode-rig-uart, grpcEnabled: true}
#    then download/build/run the bridge app as usual.
```

Loop proof: firmware telemetry updates the `renode-rig` SimRigState
row (Push matches on `name`); a REST PUT of `pwm_duty`/`led_on` rides
the Commands stream down; the firmware applies actuator fields only,
flips `status` to `commanded`, and the next frames echo it back up.
