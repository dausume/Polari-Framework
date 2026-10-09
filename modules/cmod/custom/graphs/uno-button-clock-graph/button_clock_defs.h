/*
 * button_clock_defs.h — ucd-0e2b. The button_clock.c app's own file-scope macros/typedef/globals that several of
 * its POLARI_NODE atoms reference directly (TX_ENCODE_S/E, the telemetry masks, the shared wire buffer, the event
 * queue, the sync bookkeeping, the status-restore global, the on-board L LED's local macros). Pulled OUT of
 * button_clock.c and into this header for ONE reason: `cmod.custom.glue.extract()` copies an atom's FUNCTION BODY
 * verbatim but refuses to copy one that uses a macro the APP FILE defines itself (cmod-1's own rule — a copied atom
 * must compile from headers alone); moving them into a header the app #includes makes every atom whose body touches
 * these macros/globals copyable by the no-code glue (ucd-0e2b's graph `uno-button-clock-graph`), with NO change to
 * compiled bytes (this is a straight relocation: same text, same values, same order of declaration).
 *
 * `state` and `rx` are NOT here: the hand-written button_clock.c still declares its own (this header is included by
 * it too, so nothing is duplicated); the GENERATED glue (cmod.custom.glue._render_c) declares its OWN `state`/`rx`
 * under those exact names for its class/parser graph nodes — the two builds never share a translation unit.
 */
#ifndef BUTTON_CLOCK_DEFS_H
#define BUTTON_CLOCK_DEFS_H

#include <stdint.h>

#include "board_config.h"
#include "buttonclockstate_packets.h"
/* ButtonClockEvent is telemetry-only (no command path): its decode()/decode_rx() are unused and dropped by the
 * compiler — the same pragma button_clock.c itself wraps this same include with. */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "buttonclockevent_packets.h"
#pragma GCC diagnostic pop

/* brd-wire: the instance index exists ONLY when the bridge binds several boards of a class — a single-instance
 * build (uno-button-clock is not paired, unlike uno-pair) has no index anywhere. Kept for parity with
 * sim_rig.c/echo.c so a future `uno-button-clock` pairing costs nothing here. */
#ifdef BUTTONCLOCKSTATE_INDEX_WIDTH
#define TX_ENCODE_S(s, p, m) ButtonClockState_encode((s), (p), INSTANCE_INDEX, (m))
#else
#define TX_ENCODE_S(s, p, m) ButtonClockState_encode((s), (p), (m))
#endif
#ifdef BUTTONCLOCKEVENT_INDEX_WIDTH
#define TX_ENCODE_E(s, p, m) ButtonClockEvent_encode((s), (p), INSTANCE_INDEX, (m))
#else
#define TX_ENCODE_E(s, p, m) ButtonClockEvent_encode((s), (p), (m))
#endif

/* the on-board L LED (D13 = PB5) always mirrors led_on — "free, nothing to wire" (plan §1). Never wired through
 * hal.h's single-pin FEATURE_LED abstraction (which already owns LED_PIN = D6 here): D13 is not a configurable
 * knob of this demo, it is the fixed second indicator (l_led_init/l_led_set, button_clock.c). */
#define L_LED_DDR  DDRB
#define L_LED_PORT PORTB
#define L_LED_BIT  PB5

/* boot_session persists across resets in EEPROM (avr-libc <avr/eeprom.h> eeprom_read_dword/eeprom_write_dword —
 * their own busy-wait on EEPE). Address 0x0000 of the ATmega328P's 1 KiB EEPROM (DS40002061B §4); nothing else in
 * this firmware touches EEPROM. */
#define EEPROM_BOOT_SESSION_ADDR ((uint32_t *)0x0000)

/* static, so avr-size counts them (the RAM budget is measured, not guessed). ONE shared payload/wire buffer, sized
 * to the bigger class (ButtonClockState) — a state frame and an event frame are never being built at once. */
#define WIRE_PAYLOAD_MAX (BUTTONCLOCKSTATE_PAYLOAD_MAX > BUTTONCLOCKEVENT_PAYLOAD_MAX ? BUTTONCLOCKSTATE_PAYLOAD_MAX : BUTTONCLOCKEVENT_PAYLOAD_MAX)
static uint8_t payload[WIRE_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + WIRE_PAYLOAD_MAX + 4u];
static uint32_t g_seq_s, g_seq_e;   /* per-msg_type wire frame sequence (ucd-0e3: the bridge tracks gaps per msg_type) */
/* the status telemetry reports once a SNAPSHOT frame's one-shot override ends. Initialised here (not assigned in
 * main()) so the GENERATED glue, which never copies main(), still starts with the right value — avr-libc's crt0
 * copies a non-zero initialiser out of .data before main() runs either way. */
static uint8_t g_status_base = BUTTONCLOCKSTATE_STATUS_IDLE;

/* events.queue: a bounded ring of what a ButtonClockEvent needs beyond identity/framing (those are filled in at
 * send time) — kept small (not a full ButtonClockEvent_t, which carries a 64-byte name) so EVENT_QUEUE_LEN entries
 * cost little RAM. */
typedef struct { uint8_t kind; uint32_t uptime_ms; int32_t epoch_s; uint16_t ms; } qevent_t;
static qevent_t g_queue[EVENT_QUEUE_LEN];
static uint8_t g_qhead, g_qtail, g_qcount;

/* what telemetry carries: every telemetry field, never a command field (set_* / snapshot are input-only) */
#define STATE_TELEMETRY_MASK ((ButtonClockState_mask_t)(BUTTONCLOCKSTATE_F_ALL \
    & ~(BUTTONCLOCKSTATE_F_SET_EPOCH_S | BUTTONCLOCKSTATE_F_SET_MS | BUTTONCLOCKSTATE_F_SET_SYNC_GENERATION \
        | BUTTONCLOCKSTATE_F_SET_LED | BUTTONCLOCKSTATE_F_SNAPSHOT) \
    & (SEND_NAME ? ~(ButtonClockState_mask_t)0 : ~BUTTONCLOCKSTATE_F_NAME)))
#define EVENT_TELEMETRY_MASK ((ButtonClockEvent_mask_t)(BUTTONCLOCKEVENT_F_ALL & (SEND_NAME ? ~(ButtonClockEvent_mask_t)0 : ~BUTTONCLOCKEVENT_F_NAME)))

/* the sync bookkeeping clock_tick reads — not on the wire itself (the wire carries the DERIVED epoch_s/ms/drift_ms/
 * sync_generation/sync_uncertainty_ms fields, assembled into `state` by clock_set). */
static int64_t g_sync_base_epoch_s;
static uint16_t g_sync_base_ms;
static uint32_t g_sync_base_uptime_ms;

#endif /* BUTTON_CLOCK_DEFS_H */
