/*
 * variant app `analog` (variant uno-adc-sweep) — raw ADC on A0, A1, A2 as three fields of a SECOND class,
 * UnoAnalogState (a0, a1, a2 = 10-bit counts, AVcc reference: count = mV·1024/5000), at TELEMETRY_HZ. No actuators and
 * no command path: it tests the analog front end (a pot, a photoresistor, the TMP36 — whatever is wired) and that the
 * header generator handles a class other than SimRigState. PLAIN C on avr-libc (RULE 2). Copied into the project as
 * main.c by `pol board gen`.
 */
#include <stdint.h>
#include <string.h>
#include <avr/interrupt.h>

#include "board_config.h"
#include "hal.h"
/* this variant decodes no commands: the header's decoder + parser are unused, and dropped by the compiler */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "unoanalogstate_packets.h"   /* GENERATED (c_twin target=avr) — never edited by hand */
#pragma GCC diagnostic pop

/* brd-wire (his ruling 2026-10-02): the instance index exists ONLY when the bridge binds several boards — the header
 * then defines UNOANALOGSTATE_INDEX_WIDTH and board_config.h INSTANCE_INDEX; a single-instance build has no index anywhere */
#ifdef UNOANALOGSTATE_INDEX_WIDTH
#define TX_ENCODE(s, p, m) UnoAnalogState_encode((s), (p), INSTANCE_INDEX, (m))
#else
#define TX_ENCODE(s, p, m) UnoAnalogState_encode((s), (p), (m))
#endif

#if !FEATURE_ADC
#error "uno-adc-sweep needs FEATURE_ADC"
#endif
#if FEATURE_COMMANDS
#error "the analog app has no command path (FEATURE_COMMANDS 0)"
#endif

#define TELEMETRY_MASK ((UnoAnalogState_mask_t)(UNOANALOGSTATE_F_ALL & ~(SEND_NAME ? 0u : UNOANALOGSTATE_F_NAME)))

static UnoAnalogState_t state;
static uint8_t payload[UNOANALOGSTATE_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + UNOANALOGSTATE_PAYLOAD_MAX + 4u];

int main(void)
{
    uint32_t seq = 0u, next_ms = 0u, now;

    hal_usart_init();
    hal_tick_init();
    hal_adc_init();
    memset(&state, 0, sizeof state);
    strcpy(state.name, RIG_NAME);
    state.status = UNOANALOGSTATE_STATUS_BOOT;
    sei();

    for (;;) {
        now = hal_millis();
        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        state.uptime_ms = (int64_t)now;
        state.a0 = (int64_t)hal_adc_read(0u);
        state.a1 = (int64_t)hal_adc_read(1u);
        state.a2 = (int64_t)hal_adc_read(2u);
        if (state.status == UNOANALOGSTATE_STATUS_BOOT && now > 1000u) state.status = UNOANALOGSTATE_STATUS_OK;
        hal_usart_send(wire, UnoAnalogState_frame(wire, DEVICE_ID, seq++, payload,
                                                  TX_ENCODE(&state, payload, TELEMETRY_MASK)));
    }
}
