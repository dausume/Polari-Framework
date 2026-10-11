/*
 * variant app `light` (variant uno-light, slice ucd-light) — THE LIGHT TEST: one light, switched two ways, reported both
 * ways. The light is on D6. A person can switch it from a Polari screen (the SET_LED command, the led_on field of the
 * one wire struct, LightState); the pushbutton on D2 (INT0, debounced) switches the same light, and the board reports
 * the new state up in its next frame with source=button. Either way `toggles` counts the change and `source` says who
 * made it. PLAIN C on avr-libc (no Arduino core). `pol board gen` copies this file into the project as main.c.
 *
 * Atoms (each parsed from this file, never hand-listed into a graph): boot_session_mint (a number picked anew at every
 * start, kept in EEPROM), led_toggle (a button press flips the light), apply_command (SET_LED from the host),
 * telemetry_send (one LightState frame). The rest come from the shared hal: usart init, led init, button init, rx pop.
 * No clock, no second sensing pin, no event queue, no ADC.
 */
#include <avr/eeprom.h>
#include <avr/interrupt.h>
#include <avr/io.h>
#include <stdint.h>
#include <string.h>

#include "board_config.h"          /* knobs rendered by `pol board gen`: RIG_NAME, DEVICE_ID, pins, features */
#include "hal.h"
#include "lightstate_packets.h"    /* GENERATED (c_twin target=avr) — never edited by hand */
#include "light_defs.h"

POLARI_NODE(boot_session_mint, out(return, "", "the freshly-minted boot_session (1 on a virgin chip, else +1)"),
            role("mint this start's session number from EEPROM; it differs after every reset"))
static uint32_t boot_session_mint(void)
{
    uint32_t v = eeprom_read_dword(EEPROM_BOOT_SESSION_ADDR);
    if (v == 0xFFFFFFFFul) v = 0u;
    v++;
    eeprom_write_dword(EEPROM_BOOT_SESSION_ADDR, v);
    return v;
}

static LightState_t state;
static polari_rx_t rx;

/* a press of the board's button: flip the light, count it, say it was the button */
POLARI_NODE(led_toggle, uses(LED_PIN), role("on a debounced button press: flip the light, count the change, source = button"))
static void led_toggle(void)
{
#if HAL_INT0
    if (!hal_take_toggle_pending()) return;
    state.led_on = state.led_on ? 0u : 1u;
    hal_led(state.led_on);
    state.toggles++;
    state.source = LIGHTSTATE_SOURCE_BUTTON;
    state.status = LIGHTSTATE_STATUS_ACTIVE;
#endif
}

/* the host's SET_LED: the light follows the commanded value; a command that changes nothing is not a change */
POLARI_NODE(apply_command, in(r, "frame", "a parsed PolariPacket LightState command"), uses(LED_PIN),
            role("SET_LED: put the light where the host says; a real change counts and says source = command"))
static void apply_command(const polari_rx_t *r)
{
    LightState_t cmd;
    LightState_mask_t m;
    if (LightState_decode_rx(r, &cmd, &m) != 0) return;
    if (m & LIGHTSTATE_F_LED_ON) {
        uint8_t want = cmd.led_on ? 1u : 0u;
        if (want != state.led_on) {
            state.led_on = want;
            hal_led(want);
            state.toggles++;
            state.source = LIGHTSTATE_SOURCE_COMMAND;
            state.status = LIGHTSTATE_STATUS_ACTIVE;
        }
    }
}

POLARI_NODE(telemetry_send, role("one LightState frame: the light, how often it changed, who changed it last"))
static void telemetry_send(void)
{
    state.seq = (int64_t)g_seq;
    hal_usart_send(wire, LightState_frame(wire, DEVICE_ID, g_seq, payload, TX_ENCODE(&state, payload, TELEMETRY_MASK)));
    g_seq++;
}

int main(void)
{
    uint32_t next_ms = 0u, now;
    uint8_t b;

    hal_usart_init();
    hal_tick_init();
    hal_led_init();
    hal_button_init();
    memset(&state, 0, sizeof state);
    memset(&rx, 0, sizeof rx);
#if SEND_NAME
    strcpy(state.name, RIG_NAME);
#endif
    state.status = LIGHTSTATE_STATUS_IDLE;
    state.boot_session = (int64_t)boot_session_mint();
    sei();

    for (;;) {
        while (hal_rx_pop(&b))
            if (polari_rx_feed(&rx, b) && rx.msg_type == LIGHTSTATE_MSG_TYPE)
                apply_command(&rx);

        now = hal_millis();
        led_toggle();

        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        telemetry_send();
    }
}
