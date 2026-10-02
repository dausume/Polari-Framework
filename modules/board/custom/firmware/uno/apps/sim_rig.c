/*
 * variant app `sim_rig` (brd-1's firmware; variant uno-sim-rig) — the Arduino UNO R3 (ATmega328P, 16 MHz) as one Polari
 * rig — PLAIN C on avr-libc (RULE 2: no Arduino core, no sketch). The same fields and the same frame loop as the Renode
 * twin (grpcbridge/custom/renode_twin/firmware/main.c), so the existing bridge config works with serialDevice swapped.
 * `pol board gen` copies this file into the project as main.c.
 *
 * It speaks the universal PolariPacket over USART0 (the ATmega16U2's USB-CDC on a real UNO, a TCP→pty bridge on the
 * simavr twin) through the GENERATED simrigstate_packets.h, rendered with c_twin target=avr (avr-gcc's double is
 * 4 bytes; the header converts binary32↔binary64 in software, the wire is unchanged):
 *
 *   Up:   SimRigState telemetry at TELEMETRY_HZ — uptime_ms from the Timer2 1 ms tick, temp_c from ADC_CHANNEL (the
 *         TMP36 formula, or the raw ADC count when TEMP_TMP36 is 0), the actuator state, the status word
 *         ('boot' → 'ok' after 1 s → 'commanded'; an EnumMapping: one byte on the wire).
 *   Down: SimRigState commands decode into a scratch struct; ONLY the actuator fields that are PRESENT apply
 *         (led_on → LED_PIN, pwm_duty → PWM_PIN); identity and sensors stay the firmware's own; status becomes
 *         'commanded' and the next frame carries it back up (the provable loop).
 *
 * brd-wire (wire v2, grpc-j4): every frame carries INSTANCE_INDEX in the prelude (the width the bridge's bindings imply:
 * 0 bits alone, 1 bit for a pair) and a presence bit per field — a feature compiled out is simply not sent, and a false
 * led_on IS sent. A command whose index is not this board's is ignored (a shared bus later). With SEND_NAME 0 the frame
 * omits `name`: the bridge's binding is this board's identity.
 *
 * TMP36 (Analog Devices TMP35/TMP36/TMP37 datasheet): 10 mV/°C, 750 mV at 25 °C → T = (mV − 500) / 10.
 *   https://www.analog.com/media/en/technical-documentation/data-sheets/TMP35_36_37.pdf
 */
#include <stdint.h>
#include <string.h>
#include <avr/interrupt.h>

#include "board_config.h"          /* knobs rendered by `pol board gen`: RIG_NAME, DEVICE_ID, pins, features */
#include "hal.h"
#include "simrigstate_packets.h"   /* GENERATED (c_twin target=avr) — never edited by hand */

#if FEATURE_ADC
static polari_avr_double_t sensor_value(uint16_t adc)
{
#if TEMP_TMP36
    /* the TMP36: mV = ADC·5000/1024 (AVcc = 5 V); °C = (mV − 500)/10 */
    polari_avr_double_t mv = (polari_avr_double_t)adc * (5000.0 / 1024.0);
    return (mv - 500.0) / 10.0;
#else
    return (polari_avr_double_t)adc;   /* raw 10-bit count, 0..1023 */
#endif
}
#endif

/* static, so avr-size counts them (the RAM budget is measured, not guessed) */
static SimRigState_t state;
static polari_rx_t rx;
static uint8_t payload[SIMRIGSTATE_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + SIMRIGSTATE_PAYLOAD_MAX + 4u];

/* what telemetry carries: the fields this build has, never one it compiled out */
#define TELEMETRY_MASK ((SimRigState_mask_t)(SIMRIGSTATE_F_UPTIME_MS | SIMRIGSTATE_F_STATUS \
    | (FEATURE_ADC ? SIMRIGSTATE_F_TEMP_C : 0u) | (FEATURE_LED ? SIMRIGSTATE_F_LED_ON : 0u) \
    | (FEATURE_PWM ? SIMRIGSTATE_F_PWM_DUTY : 0u) | (SEND_NAME ? SIMRIGSTATE_F_NAME : 0u)))

static void apply_command(const polari_rx_t *r)
{
    SimRigState_t cmd;
    SimRigState_mask_t m;
    SimRigState_index_t idx;
    if (SimRigState_decode_rx(r, &cmd, &idx, &m) != 0 || idx != INSTANCE_INDEX) return;
#if FEATURE_LED
    if (m & SIMRIGSTATE_F_LED_ON) {                    /* ACTUATORS only, and only when present */
        state.led_on = cmd.led_on ? 1u : 0u;
        hal_led(state.led_on);
    }
#endif
#if FEATURE_PWM
    if (m & SIMRIGSTATE_F_PWM_DUTY) state.pwm_duty = hal_pwm_apply(cmd.pwm_duty);
#endif
    (void)m;
    state.status = SIMRIGSTATE_STATUS_COMMANDED;
}

int main(void)
{
    uint32_t seq = 0u, next_ms = 0u, now;
    uint8_t b;

    hal_usart_init();
    hal_tick_init();
#if FEATURE_LED
    hal_led_init();
#endif
#if FEATURE_PWM
    hal_pwm_init();
#endif
#if FEATURE_ADC
    hal_adc_init();
#endif
    memset(&state, 0, sizeof state);
    memset(&rx, 0, sizeof rx);
    strcpy(state.name, RIG_NAME);                      /* the Push match key of an UNBOUND board (SEND_NAME 1) */
    state.status = SIMRIGSTATE_STATUS_BOOT;
    sei();

    for (;;) {
        while (hal_rx_pop(&b))
            if (polari_rx_feed(&rx, b) && rx.msg_type == SIMRIGSTATE_MSG_TYPE)
                apply_command(&rx);

        now = hal_millis();
        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        state.uptime_ms = (int64_t)now;
#if FEATURE_ADC
        state.temp_c = sensor_value(hal_adc_read(ADC_CHANNEL));
#endif
        if (state.status == SIMRIGSTATE_STATUS_BOOT && now > 1000u) state.status = SIMRIGSTATE_STATUS_OK;
        hal_usart_send(wire, SimRigState_frame(wire, DEVICE_ID, seq++, payload,
                                                  SimRigState_encode(&state, payload, INSTANCE_INDEX, TELEMETRY_MASK)));
    }
}
