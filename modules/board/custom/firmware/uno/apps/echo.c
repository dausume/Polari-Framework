/*
 * variant app `echo` (variant uno-echo) — the PROTOCOL test: no sensors, no actuators. A heartbeat SimRigState frame
 * at TELEMETRY_HZ (status 'ok'); a command that decodes is copied WHOLE into the state (every field, incl. temp_c,
 * which no sensor could produce here), status becomes 'echoed', and the next frames carry it back up with uptime_ms
 * still ticking. If a PUT's values come back unchanged, the wire, the header, the parser and the bridge all agree.
 * PLAIN C on avr-libc (RULE 2). Copied into the project as main.c by `pol board gen`.
 */
#include <stdint.h>
#include <string.h>
#include <avr/interrupt.h>

#include "board_config.h"
#include "hal.h"
#include "simrigstate_packets.h"   /* GENERATED (c_twin target=avr) — never edited by hand */

static SimRigState_t state;
static polari_rx_t rx;
static uint8_t payload[SIMRIGSTATE_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + SIMRIGSTATE_PAYLOAD_MAX + 4u];
static uint16_t echoes;

static void echo_command(const uint8_t *p, uint16_t len)
{
    SimRigState_t cmd;
    if (SimRigState_decode(p, len, &cmd) != 0) return;
    memcpy(&state, &cmd, sizeof state);                /* EVERY field, as sent */
    strcpy(state.name, RIG_NAME);                      /* …but the row it answers stays this board's */
    strcpy(state.status, "echoed");
    echoes++;
}

int main(void)
{
    uint32_t seq = 0u, next_ms = 0u, now;
    uint8_t b;

    hal_usart_init();
    hal_tick_init();
    memset(&state, 0, sizeof state);
    memset(&rx, 0, sizeof rx);
    strcpy(state.name, RIG_NAME);
    strcpy(state.status, "boot");
    sei();

    for (;;) {
        while (hal_rx_pop(&b))
            if (polari_rx_feed(&rx, b) && rx.msg_type == SIMRIGSTATE_MSG_TYPE)
                echo_command(rx.payload, rx.payload_len);

        now = hal_millis();
        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        state.uptime_ms = (int64_t)now;
        if (!echoes && state.status[0] == 'b' && now > 1000u) strcpy(state.status, "ok");
        hal_usart_send(wire, polari_packet_encode(wire, SIMRIGSTATE_MSG_TYPE, DEVICE_ID, seq++,
                                                  payload, SimRigState_encode(&state, payload)));
    }
}
