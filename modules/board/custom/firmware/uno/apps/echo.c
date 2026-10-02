/*
 * variant app `echo` (variant uno-echo) — the PROTOCOL test: no sensors, no actuators. A heartbeat SimRigState frame
 * at TELEMETRY_HZ (status 'ok'); a command that decodes is copied WHOLE into the state (every field, incl. temp_c,
 * which no sensor could produce here), status becomes 'echoed', and the next frames carry it back up with uptime_ms
 * still ticking. If a PUT's values come back unchanged, the wire, the header, the parser and the bridge all agree.
 * PLAIN C on avr-libc (RULE 2). Copied into the project as main.c by `pol board gen`.
 * brd-wire (wire v2): the command's PRESENT fields are copied (a partial command echoes what it carried); every frame
 * carries every field back, and the command must name this board's INSTANCE_INDEX.
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

static void echo_command(const polari_rx_t *r)
{
    SimRigState_t cmd;
    SimRigState_index_t idx;
    memcpy(&cmd, &state, sizeof cmd);                  /* fields the command does not carry stay as they are */
    if (SimRigState_decode_rx(r, &cmd, &idx, 0) != 0 || idx != INSTANCE_INDEX) return;
    memcpy(&state, &cmd, sizeof state);                /* EVERY present field, as sent */
    strcpy(state.name, RIG_NAME);                      /* …but the row it answers stays this board's */
    state.status = SIMRIGSTATE_STATUS_ECHOED;
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
    state.status = SIMRIGSTATE_STATUS_BOOT;
    sei();

    for (;;) {
        while (hal_rx_pop(&b))
            if (polari_rx_feed(&rx, b) && rx.msg_type == SIMRIGSTATE_MSG_TYPE)
                echo_command(&rx);

        now = hal_millis();
        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        state.uptime_ms = (int64_t)now;
        if (!echoes && state.status == SIMRIGSTATE_STATUS_BOOT && now > 1000u) state.status = SIMRIGSTATE_STATUS_OK;
        hal_usart_send(wire, SimRigState_frame(wire, DEVICE_ID, seq++, payload,
                                                  SimRigState_encode(&state, payload, INSTANCE_INDEX,
                                                                     SIMRIGSTATE_F_ALL & ~(SEND_NAME ? 0u : SIMRIGSTATE_F_NAME))));
    }
}
