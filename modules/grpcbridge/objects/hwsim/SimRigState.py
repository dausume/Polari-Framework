"""
@module grpcbridge.objects.hwsim.SimRigState

Row class SimRigState of the grpcbridge module — one class per file (design §7), split
from hwsim_basis.py (sap-2c). The class docstring below is the explanation.
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
