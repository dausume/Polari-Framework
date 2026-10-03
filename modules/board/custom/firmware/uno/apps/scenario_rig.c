/*
 * variant app `scenario_rig` — SCENARIO ONLY (sc-1, AI-Notes/plans/FIRMWARE_SCENARIO_PLAN.md §3a; module firmwarefaults).
 * A small rig (uptime + status telemetry, the command path, the LED) plus ONE behaviour per scenario, each chosen by a
 * build flag of a FirmwareVariant row (rendered into board_config.h by `pol board gen`, never hand-edited). Each flag has
 * a BEFORE value (the latent bug) and an AFTER value (the technique), so the pair differs in exactly that code:
 *
 *   SC_ACK_WAIT 1        scenario 2: at SC_ACK_AT_MS the board sends a REQUEST frame (msg_type 0x7F, empty payload) and
 *                        needs the host's ACK (msg_type 0x7F back) before it goes on.
 *     SC_ACK_TIMEOUT_MS 0   BEFORE: it waits for the ack in a loop with no way out — a lost ack = a hang (no telemetry)
 *     SC_ACK_TIMEOUT_MS N   AFTER: an explicit state machine (idle → waiting → acked | failed) polled from the main
 *                          loop: telemetry never stops, a request unanswered for N ms is sent again, up to
 *                          SC_ACK_RETRIES tries, then status 'fault' (Technique timeout+state-machine)
 *   SC_EEPROM_RECORD 1   scenario 5, BEFORE: a command's pwm_duty (low 32 bits) is written IN PLACE as a 4-byte record
 *                        at EEPROM 0; a reset between the byte writes leaves half old, half new
 *   SC_EEPROM_RECORD 2   AFTER (Technique write-then-commit): two slots {value[4], seq, crc8}; the new value goes into
 *                        the slot NOT in use, the crc (over value + seq) is written LAST; at boot the valid slot with
 *                        the newer seq wins — a torn write leaves the old record readable
 *   HAL_INT0 1           scenario 3: presses on D2 counted by hal.c (HAL_INT0_DEBOUNCE_MS picks BEFORE / AFTER)
 *
 * What the scenario reads is in named statics (g_ack_state, g_rec_boot, …) — the twin's --watch finds them by symbol in
 * this build's own ELF. PLAIN C on avr-libc (RULE 2). Copied into the project as main.c by `pol board gen`.
 */
#include <stdint.h>
#include <string.h>
#include <avr/interrupt.h>

#include "board_config.h"
#include "hal.h"
#include "simrigstate_packets.h"   /* GENERATED (c_twin target=avr) — never edited by hand */
#if SC_EEPROM_RECORD
#include <avr/eeprom.h>
#endif

#ifndef SC_ACK_WAIT
#define SC_ACK_WAIT 0
#endif
#ifndef SC_ACK_TIMEOUT_MS
#define SC_ACK_TIMEOUT_MS 0
#endif
#ifndef SC_ACK_RETRIES
#define SC_ACK_RETRIES 3
#endif
#ifndef SC_ACK_AT_MS
#define SC_ACK_AT_MS 500
#endif
#ifndef SC_EEPROM_RECORD
#define SC_EEPROM_RECORD 0
#endif
#define ACK_MSG_TYPE 0x7Fu

#ifdef SIMRIGSTATE_INDEX_WIDTH
#define TX_ENCODE(s, p, m) SimRigState_encode((s), (p), INSTANCE_INDEX, (m))
#else
#define TX_ENCODE(s, p, m) SimRigState_encode((s), (p), (m))
#endif

static SimRigState_t state;
static polari_rx_t rx;
static uint8_t payload[SIMRIGSTATE_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + SIMRIGSTATE_PAYLOAD_MAX + 4u];
static uint32_t seq;

#define TELEMETRY_MASK ((SimRigState_mask_t)(SIMRIGSTATE_F_UPTIME_MS | SIMRIGSTATE_F_STATUS | SIMRIGSTATE_F_NAME \
    | (FEATURE_LED ? SIMRIGSTATE_F_LED_ON : 0u)))

/* ------------------------------------------------------------------ scenario 5: the EEPROM record */
#if SC_EEPROM_RECORD
/* volatile: nothing in the firmware reads them back — the twin's --watch does, so the compiler must keep them */
static volatile uint32_t g_rec_boot;   /* the record as read at boot */
static volatile uint8_t g_rec_valid;   /* 1 = a record was found (AFTER: a slot whose crc matched) */
static volatile uint8_t g_rec_writes;  /* records written since boot */

#if SC_EEPROM_RECORD == 2
static uint8_t g_rec_slot, g_rec_seq;

static uint8_t crc8(const uint8_t *d, uint8_t n)  /* CRC-8, poly 0x07, init 0 */
{
    uint8_t c = 0u;
    while (n--) {
        c ^= *d++;
        for (uint8_t k = 0u; k < 8u; k++) c = (uint8_t)((c & 0x80u) ? (uint8_t)(c << 1) ^ 0x07u : (uint8_t)(c << 1));
    }
    return c;
}

static uint8_t slot_read(uint8_t s, uint32_t *v, uint8_t *sq)
{
    uint8_t b[6];
    eeprom_read_block(b, (const void *)(uintptr_t)(s * 8u), sizeof b);
    if (b[4] == 0xFFu || crc8(b, 5u) != b[5]) return 0u;
    *v = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    *sq = b[4];
    return 1u;
}
#endif

static void record_boot(void)
{
#if SC_EEPROM_RECORD == 1
    g_rec_boot = eeprom_read_dword((const uint32_t *)0);
    g_rec_valid = 1u;              /* nothing to check it against: that is the bug */
#else
    uint32_t v0 = 0u, v1 = 0u;
    uint8_t s0 = 0u, s1 = 0u, ok0 = slot_read(0u, &v0, &s0), ok1 = slot_read(1u, &v1, &s1);
    if (ok0 && (!ok1 || (int8_t)(s0 - s1) > 0)) { g_rec_boot = v0; g_rec_slot = 0u; g_rec_seq = s0; g_rec_valid = 1u; }
    else if (ok1) { g_rec_boot = v1; g_rec_slot = 1u; g_rec_seq = s1; g_rec_valid = 1u; }
    else { g_rec_valid = 0u; g_rec_slot = 1u; g_rec_seq = 0u; }
#endif
}

static void record_write(uint32_t v)
{
#if SC_EEPROM_RECORD == 1
    for (uint8_t k = 0u; k < 4u; k++) eeprom_write_byte((uint8_t *)(uintptr_t)k, (uint8_t)(v >> (8u * k)));
#else
    uint8_t b[6], s = (uint8_t)(g_rec_slot ^ 1u);
    for (uint8_t k = 0u; k < 4u; k++) b[k] = (uint8_t)(v >> (8u * k));
    b[4] = (uint8_t)(g_rec_seq + 1u) == 0xFFu ? 0u : (uint8_t)(g_rec_seq + 1u);
    b[5] = crc8(b, 5u);
    for (uint8_t k = 0u; k < 6u; k++) eeprom_write_byte((uint8_t *)(uintptr_t)(s * 8u + k), b[k]);   /* crc LAST = commit */
    g_rec_slot = s;
    g_rec_seq = b[4];
#endif
    g_rec_writes++;
}
#endif

/* ------------------------------------------------------------------ scenario 2: request / ack */
#if SC_ACK_WAIT
static volatile uint8_t g_ack_state;   /* 0 idle, 1 waiting, 2 acked, 3 failed (gave up) */
static volatile uint8_t g_ack_tries;   /* requests sent */
static volatile uint8_t g_ack_seen;    /* an ack frame was parsed */

static void send_request(void)
{
    hal_usart_send(wire, polari_packet_encode_v(wire, POLARI_VERSION, ACK_MSG_TYPE, DEVICE_ID, seq++, payload, 0u));
    g_ack_tries++;
}
#endif

static void apply_command(const polari_rx_t *r)
{
    SimRigState_t cmd;
    SimRigState_mask_t m;
#ifdef SIMRIGSTATE_INDEX_WIDTH
    SimRigState_index_t idx;
    if (SimRigState_decode_rx(r, &cmd, &idx, &m) != 0 || idx != INSTANCE_INDEX) return;
#else
    if (SimRigState_decode_rx(r, &cmd, &m) != 0) return;
#endif
#if FEATURE_LED
    if (m & SIMRIGSTATE_F_LED_ON) { state.led_on = cmd.led_on ? 1u : 0u; hal_led(state.led_on); }
#endif
#if SC_EEPROM_RECORD
    if (m & SIMRIGSTATE_F_PWM_DUTY) record_write((uint32_t)cmd.pwm_duty);
#endif
    (void)m;
    state.status = SIMRIGSTATE_STATUS_COMMANDED;
}

static void drain_rx(void)
{
    uint8_t b;
    while (hal_rx_pop(&b))
        if (polari_rx_feed(&rx, b)) {
            if (rx.msg_type == SIMRIGSTATE_MSG_TYPE) apply_command(&rx);
#if SC_ACK_WAIT
            else if (rx.msg_type == ACK_MSG_TYPE) g_ack_seen = 1u;
#endif
        }
}

#if SC_ACK_WAIT && SC_ACK_TIMEOUT_MS
/* AFTER: the explicit state machine, one step per main-loop pass (noinline so the twin's --fn-cycles prices one step) */
static uint32_t g_ack_deadline;

__attribute__((noinline)) static void ack_step(uint32_t now)
{
    switch (g_ack_state) {
    case 0:
        if ((int32_t)(now - (uint32_t)SC_ACK_AT_MS) < 0) return;
        send_request();
        g_ack_deadline = now + (uint32_t)SC_ACK_TIMEOUT_MS;
        g_ack_state = 1u;
        return;
    case 1:
        if (g_ack_seen) { g_ack_state = 2u; return; }
        if ((int32_t)(now - g_ack_deadline) < 0) return;
        if (g_ack_tries >= (uint8_t)SC_ACK_RETRIES) { g_ack_state = 3u; state.status = SIMRIGSTATE_STATUS_FAULT; return; }
        send_request();
        g_ack_deadline = now + (uint32_t)SC_ACK_TIMEOUT_MS;
        return;
    default:
        return;
    }
}
#endif

int main(void)
{
    uint32_t next_ms = 0u, now;

    hal_usart_init();
    hal_tick_init();
#if FEATURE_LED
    hal_led_init();
#endif
#if HAL_INT0
    hal_button_init();
#endif
    memset(&state, 0, sizeof state);
    memset(&rx, 0, sizeof rx);
    strcpy(state.name, RIG_NAME);
    state.status = SIMRIGSTATE_STATUS_BOOT;
#if SC_EEPROM_RECORD
    record_boot();
#endif
#if HAL_WDT
    hal_wdt_init();
#endif
    sei();

    for (;;) {
#if HAL_WDT
        hal_wdt_kick();
#endif
        drain_rx();
        now = hal_millis();
#if SC_ACK_WAIT && SC_ACK_TIMEOUT_MS
        ack_step(now);
#elif SC_ACK_WAIT
        if (g_ack_state == 0u && (int32_t)(now - (uint32_t)SC_ACK_AT_MS) >= 0) {
            send_request();
            g_ack_state = 1u;
            while (!g_ack_seen) drain_rx();            /* BEFORE: no timeout — a lost ack never lets go */
            g_ack_state = 2u;
            now = hal_millis();
        }
#endif
        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        state.uptime_ms = (int64_t)now;
        if (state.status == SIMRIGSTATE_STATUS_BOOT && now > 1000u) state.status = SIMRIGSTATE_STATUS_OK;
        hal_usart_send(wire, SimRigState_frame(wire, DEVICE_ID, seq++, payload, TX_ENCODE(&state, payload, TELEMETRY_MASK)));
    }
}
