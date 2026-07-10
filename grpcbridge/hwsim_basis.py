"""
@module grpcbridge.hwsim_basis

hwsim-1 (HARDWARE_SIMULATION_PLAN.md): the first hardware-family
object — one row per physical/simulated rig, the digital twin the
Renode firmware streams into. Deliberately scalar-heavy (numbers +
one short status string) so the C-struct twin on a bare-metal MCU is
trivial; richer classes come with grpc-4's HardwareSignalDefinition.

The row IS the device to everything above the seam: telemetry frames
update it, and updating it over REST commands the device (grpc-j2's
proven Commands loop).

@consumers
  - polariServer (registration + seed)
  - grpcbridge.c_twin (generated <class>_packets.h for firmware)
  - the sim-rig / renode-rig Polari Hardware Bridges
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimRigState(treeObject):
    """State of one hardware rig (real, Renode-simulated, or the
    bridge's built-in synthetic MCU). Field set mirrors what a tiny
    MCU can maintain: uptime, one sensor, two actuator knobs."""

    @treeObjectInit
    def __init__(
        self,
        # Rig identity — Polari's unique-key convention AND the Push
        # match key (contracts usually don't carry the polari id).
        name: str = '',
        # Milliseconds since firmware boot (telemetry heartbeat).
        uptime_ms: int = 0,
        # The rig's one demo sensor.
        temp_c: float = 0.0,
        # Actuator knobs — commanding these over REST reaches the
        # device via the Commands stream.
        pwm_duty: int = 0,
        led_on: bool = False,
        # Firmware-reported status word ('boot', 'ok', 'commanded').
        status: str = '',
        manager=None,
    ):
        self.name = name
        self.uptime_ms = uptime_ms
        self.temp_c = temp_c
        self.pwm_duty = pwm_duty
        self.led_on = led_on
        self.status = status


#: Seed: the Renode rig row exists from boot so its schema can be
#: stabilized and exposed before the first telemetry frame arrives.
SEED_SIM_RIGS = [
    {'name': 'renode-rig', 'uptime_ms': 0, 'temp_c': 20.0,
     'pwm_duty': 0, 'led_on': False, 'status': 'seeded'},
]
