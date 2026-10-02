# UNO firmware template (brd-1; brd-fi: variants) — plain C on avr-libc

The Arduino UNO R3 (ATmega328P, 16 MHz) as a Polari device — RULE 2: C only, no Arduino core, no sketch.

`pol board gen uno --variant <name>` copies `hal.c` + `hal.h` + `Makefile` and the variant's app `apps/<app>.c` (as
`main.c`) into a project, renders `board_config.h` from the variant's knobs (board.custom.variants) and writes one
`<class>_packets.h` per class it speaks (c_twin `target=avr`; live from the server with `--api`, from the server's own
exposure when the installer generates, else the pinned snapshot in `custom/contracts/`). This README and the template's
own `board_config.h` (the uno-sim-rig defaults) are not copied — a generated project holds only `.c/.h` + `Makefile`.

| app | variant | class | what it does |
|---|---|---|---|
| `apps/sim_rig.c` | uno-sim-rig | SimRigState | brd-1's rig: TMP36 → temp_c, led_on → LED_PIN, pwm_duty → PWM_PIN, commands apply actuators only, status boot → ok → commanded |
| `apps/blink.c` | uno-blink-only | SimRigState | LED toggles every BLINK_MS by itself; telemetry only (receiver off) |
| `apps/analog.c` | uno-adc-sweep | UnoAnalogState | raw ADC of A0, A1, A2; telemetry only (receiver off) |
| `apps/echo.c` | uno-echo | SimRigState | no peripherals; a command is copied back WHOLE, status echoed |

| peripheral (`hal.c`) | use | fact |
|---|---|---|
| USART0 115200 8N1, RX ISR → 64-B ring → the header's resync-safe parser (only with FEATURE_COMMANDS) | the PolariPacket wire | UBRR0 = 16 with U2X0 (+2.1 %), knob `USART_U2X 0` → UBRR0 = 8 (−3.5 %) — ATmega328P DS40002061B Table 20-7 p.199 |
| Timer2 CTC /128, OCR2A = 124 | 1 ms tick → `uptime_ms` | 16 MHz / 128 / 125 = 1000 Hz |
| ADC channel 0..5, AVcc reference, /128 | the TMP36 (`temp_c = (mV − 500) / 10`) or raw counts | ADC = Vin·1024/Vref (§24.7 p.256); TMP36 10 mV/°C, 750 mV at 25 °C |
| LED_PIN (D2..D13; D13 = the on-board LED) | `led_on` | D0..D7 = PORTD, D8..D13 = PORTB |
| PWM_PIN: D6/D5 (Timer0 fast PWM) or D9/D10 (Timer1 8-bit fast PWM), /64 ≈ 976 Hz | `pwm_duty` 0..100 % → OCR = duty·255/100 | D3/D11 are Timer2's (the tick) — refused |

Knobs (`board_config.h`): RIG_NAME, DEVICE_ID, USART_U2X, TELEMETRY_HZ (1..50), FEATURE_LED / PWM / ADC / COMMANDS,
LED_PIN, PWM_PIN, ADC_CHANNEL, TEMP_TMP36, BLINK_MS, plus a variant's own `NAME=integer` build defines. An unused
peripheral is not compiled, so a smaller variant is a smaller .hex.

Measured (avr-gcc 14.2.0, `-Os`, the live v1 contracts): uno-sim-rig 4532 / 763 B, uno-blink-only 1514 / 501 B,
uno-adc-sweep 1394 / 528 B, uno-echo 3152 / 763 B (flash / static RAM; the stack is not counted). brd-1's single-file
main.c measured 4442 B against the pinned v2 header; the same header now gives 4518 B — the split into hal.c costs +76 B (cross-unit calls, the ADC channel argument). Field order changes size too: the live v1 header builds 4532 B.

With a local toolchain: `make` (all `*.c`, firmware.elf, firmware.hex, `avr-size -A`). Through Polari: `pol board build uno`.

**brd-wire (wire v2, grpc-j4).** The generated header is the wire v2 one: `status` is an EnumMapping
(`SIMRIGSTATE_STATUS_BOOT/OK/COMMANDED/ECHOED/FAULT`, one byte), `<C>_encode(s, p, [INSTANCE_INDEX,] mask)` (the apps' `TX_ENCODE`) sends only the
fields set in `mask` (an app's TELEMETRY_MASK: what it has, never what it compiled out), `<C>_decode_rx` writes only the
present fields and reports the frame's index (a command for another index is ignored), `<C>_frame()` frames with the
class's version byte. With ONE board on the bridge there is no index anywhere (his ruling 2026-10-02): the header has no
`<C>_index_t` / `_INDEX_*`, encode/decode take no index, `board_config.h` has no `INSTANCE_INDEX`; with several, those
appear with the computed width and `INSTANCE_INDEX` is this board's index. `SEND_NAME` (0: the
binding is the identity, the frame omits `name`).

