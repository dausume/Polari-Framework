/*
 * variant app `blink` (variant uno-blink-only) — the smallest thing worth flashing: the LED on LED_PIN toggles every
 * BLINK_MS by itself, and a SimRigState frame at TELEMETRY_HZ says so (led_on mirrors the pin, uptime_ms ticks,
 * status 'ok'). No ADC, no PWM, and NO command path: it tests "does a frame reach the row, does the pin move" with
 * nothing else in the way. brd-wire (wire v2): the frame carries only uptime_ms, led_on, status (+ name) — temp_c and
 * pwm_duty are absent, not zero — and led_on = false IS present, so the row toggles back (brd-fi finding (1) fixed). PLAIN C on avr-libc (RULE 2). `pol board gen` copies this file into the project as main.c.
 */
#include <stdint.h>
#include <string.h>
#include <avr/interrupt.h>

#include "board_config.h"
#include "hal.h"
/* this variant decodes no commands: the header's decoder + parser are unused, and dropped by the compiler */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "simrigstate_packets.h"   /* GENERATED (c_twin target=avr) — never edited by hand */
#pragma GCC diagnostic pop

/* brd-wire (his ruling 2026-10-02): the instance index exists ONLY when the bridge binds several boards — the header
 * then defines SIMRIGSTATE_INDEX_WIDTH and board_config.h INSTANCE_INDEX; a single-instance build has no index anywhere */
#ifdef SIMRIGSTATE_INDEX_WIDTH
#define TX_ENCODE(s, p, m) SimRigState_encode((s), (p), INSTANCE_INDEX, (m))
#else
#define TX_ENCODE(s, p, m) SimRigState_encode((s), (p), (m))
#endif

#if !FEATURE_LED
#error "uno-blink-only needs FEATURE_LED"
#endif
#if FEATURE_COMMANDS
#error "the blink app has no command path (FEATURE_COMMANDS 0)"
#endif

#define TELEMETRY_MASK ((SimRigState_mask_t)(SIMRIGSTATE_F_UPTIME_MS | SIMRIGSTATE_F_LED_ON | SIMRIGSTATE_F_STATUS \
    | (SEND_NAME ? SIMRIGSTATE_F_NAME : 0u)))

static SimRigState_t state;
static uint8_t payload[SIMRIGSTATE_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + SIMRIGSTATE_PAYLOAD_MAX + 4u];

int main(void)
{
    uint32_t seq = 0u, next_ms = 0u, next_blink = BLINK_MS, now;

    hal_usart_init();
    hal_tick_init();
    hal_led_init();
    memset(&state, 0, sizeof state);
    strcpy(state.name, RIG_NAME);
    state.status = SIMRIGSTATE_STATUS_BOOT;
    sei();

    for (;;) {
        now = hal_millis();
        if (BLINK_MS && (int32_t)(now - next_blink) >= 0) {
            next_blink += BLINK_MS;
            state.led_on = state.led_on ? 0u : 1u;
            hal_led(state.led_on);
        }
        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        state.uptime_ms = (int64_t)now;
        if (state.status == SIMRIGSTATE_STATUS_BOOT && now > 1000u) state.status = SIMRIGSTATE_STATUS_OK;
        hal_usart_send(wire, SimRigState_frame(wire, DEVICE_ID, seq++, payload,
                                                  TX_ENCODE(&state, payload, TELEMETRY_MASK)));
    }
}
