# UNO firmware template (brd-1) — plain C on avr-libc

The Arduino UNO R3 (ATmega328P, 16 MHz) as one Polari rig speaking `SimRigState` — RULE 2: C only, no Arduino core,
no sketch. Same fields and frame loop as the Renode twin (`grpcbridge/custom/renode_twin/firmware/main.c`), so the
existing bridge config works with `serialDevice` swapped.

`pol board gen uno --class SimRigState [--api URL]` copies `main.c` + `Makefile` into a project, renders
`board_config.h` from the knobs and writes `simrigstate_packets.h` (c_twin `target=avr`; live from the server with
`--api`, else the pinned contract snapshot `custom/contracts/SimRigState.v2.json`). This README and the template's own
`board_config.h` (the defaults) are not copied — a generated project holds only `.c/.h` + `Makefile`.

| peripheral | use | fact |
|---|---|---|
| USART0 115200 8N1, RX ISR → 64-B ring → the header's resync-safe parser | the PolariPacket wire | UBRR0 = 16 with U2X0 (+2.1 %), knob `USART_U2X 0` → UBRR0 = 8 (−3.5 %) — ATmega328P DS40002061B Table 20-7 p.199 |
| Timer2 CTC /128, OCR2A = 124 | 1 ms tick → `uptime_ms` | 16 MHz / 128 / 125 = 1000 Hz |
| ADC0, AVcc reference, /128 | the kit's TMP36 on A0 → `temp_c = (mV − 500) / 10` | ADC = Vin·1024/Vref (§24.7 p.256); TMP36 10 mV/°C, 750 mV at 25 °C |
| PORTB5 (D13, the on-board LED) | `led_on` | |
| Timer0 fast PWM, OC0A = PD6 (D6), /64 ≈ 976 Hz | `pwm_duty` as a percentage 0..100 → OCR0A = duty·255/100 | |

Telemetry: one `SimRigState` frame (msg_type 1, device_id = `DEVICE_ID`, default 3) every 100 ms. `status` is `boot`,
then `ok` after 1 s, then `commanded` once a command arrives. A command applies ACTUATOR fields only (`led_on`,
`pwm_duty`); `name`, `uptime_ms`, `temp_c` stay the firmware's own.

Measured (avr-gcc 14.2.0, `-Os`, default knobs): `.text` 4416 B, `.data` 26 B, `.bss` 737 B → flash 4442 / 32256 B,
static RAM 763 / 2048 B (the stack is not counted).

With a local toolchain: `make` (firmware.elf, firmware.hex, `avr-size -A`). Through Polari: `pol board build uno`.
