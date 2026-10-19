/*
 * variant app `light_v2` (variant uno-light-v2, slice fgm-6a, FIRMWARE_GENERATION_MODULE_PLAN.md section 10) - THE LIGHT TEST WITH
 * COMMAND CONFIRMATION. The same light as `light` (D6, switched from a Polari screen by SET_LED and by the board's own pushbutton
 * on D2), on a NEW wire struct, LightStateV2, that numbers every command:
 *
 *   down  command_id          the number the sender picked (1..65535); led_on is the light value asked for
 *   up    last_command_id     the number of the last command this board ANSWERED (0 = none since it started)
 *   up    last_command_result applied | rejected-invalid | rejected-busy (0 = unknown / none yet)
 *
 * The board answers a command in a report sent AT ONCE (not at the next 10 Hz tick), so a burst of commands is answered one by one.
 *   - a command with no command_id, an id of 0 or above 65535, or a payload that does not decode  -> rejected-invalid, and
 *     last_command_id is left alone (there is no number to echo)
 *   - a command with a good number but no led_on                                                   -> rejected-invalid WITH its number
 *   - a command whose number equals last_command_id                                                 -> a repeat: nothing is applied
 *     again (a stale whole-row resend can never flip the light twice); the report is simply sent again
 *   - anything else                                                                                  -> applied (the light follows;
 *     a command that changes nothing is not a change); source = command only when the light really changed
 * rejected-busy is part of the contract and understood by the backend; this firmware has no busy state (it never emits it).
 * A press of the board's button changes the light, counts it, says source = button, and leaves last_command_id and
 * last_command_result exactly as they were - so a report caused by the button can never be read as an answer to a command.
 * PLAIN C on avr-libc (no Arduino core). `pol board gen` copies this file into the project as main.c.
 */
#include <avr/eeprom.h>
#include <avr/interrupt.h>
#include <avr/io.h>
#include <stdint.h>
#include <string.h>

#include "board_config.h"          /* knobs rendered by `pol board gen`: RIG_NAME, DEVICE_ID, pins, features */
#include "hal.h"
#include "lightstatev2_packets.h"  /* GENERATED (c_twin target=avr) - never edited by hand */
#include "light_v2_defs.h"

static uint32_t boot_session_mint(void)
{
    uint32_t v = eeprom_read_dword(EEPROM_BOOT_SESSION_ADDR);
    if (v == 0xFFFFFFFFul) v = 0u;
    v++;
    eeprom_write_dword(EEPROM_BOOT_SESSION_ADDR, v);
    return v;
}

static LightStateV2_t state;
static polari_rx_t rx;

/* a press of the board's button: flip the light, count it, say it was the button. last_command_* are NOT touched. */
static void led_toggle(void)
{
#if HAL_INT0
    if (!hal_take_toggle_pending()) return;
    state.led_on = state.led_on ? 0u : 1u;
    state.toggles++;
    state.source = LIGHTSTATEV2_SOURCE_BUTTON;
    state.status = LIGHTSTATEV2_STATUS_ACTIVE;
#endif
}

/* THE STRUCT CONTROLS THE LIGHT (slice scl): the mutators only alter state.led_on; this, called every pass, is the only thing that drives D6 */
static void led_follow_state(void)
{
    static uint8_t pin = 0u;
    if (state.led_on == pin) return;
    pin = state.led_on ? 1u : 0u;
    hal_led(pin);
}

static void telemetry_send(void)
{
    state.seq = (int64_t)g_seq;
    hal_usart_send(wire, LightStateV2_frame(wire, DEVICE_ID, g_seq, payload, TX_ENCODE(&state, payload, TELEMETRY_MASK)));
    g_seq++;
}

/* the host's SET_LED: validate, answer by number, apply, and report at once */
static void apply_command(const polari_rx_t *r)
{
    LightStateV2_t cmd;
    LightStateV2_mask_t m = 0;
    uint8_t want;

    memset(&cmd, 0, sizeof cmd);
    if (LightStateV2_decode_rx(r, &cmd, &m) != 0
        || !(m & LIGHTSTATEV2_F_COMMAND_ID) || cmd.command_id < 1 || cmd.command_id > COMMAND_ID_MAX) {
        state.last_command_result = LIGHTSTATEV2_LAST_COMMAND_RESULT_REJECTED_INVALID;   /* no number to echo */
    } else if (cmd.command_id == state.last_command_id) {
        /* a repeat of the command already answered: nothing to apply, the report below repeats the answer */
    } else {
        state.last_command_id = cmd.command_id;
        if (!(m & LIGHTSTATEV2_F_LED_ON)) {
            state.last_command_result = LIGHTSTATEV2_LAST_COMMAND_RESULT_REJECTED_INVALID;
        } else {
            want = cmd.led_on ? 1u : 0u;
            if (want != state.led_on) {
                state.led_on = want;
                state.toggles++;
                state.source = LIGHTSTATEV2_SOURCE_COMMAND;
                state.status = LIGHTSTATEV2_STATUS_ACTIVE;
            }
            state.last_command_result = LIGHTSTATEV2_LAST_COMMAND_RESULT_APPLIED;
        }
    }
    telemetry_send();
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
    state.status = LIGHTSTATEV2_STATUS_IDLE;
    state.boot_session = (int64_t)boot_session_mint();
    sei();

    for (;;) {
        while (hal_rx_pop(&b))
            if (polari_rx_feed(&rx, b) && rx.msg_type == LIGHTSTATEV2_MSG_TYPE)
                apply_command(&rx);

        now = hal_millis();
        led_toggle();
        led_follow_state();

        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        telemetry_send();
    }
}
