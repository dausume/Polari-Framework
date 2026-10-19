/*
 * variant app `button_clock` (variant uno-button-clock, ucd-0e2 — UNO_CORE_DEMO_PLAN.md §1/§5f/§5g) — THE CORE DEMO:
 * a button on D2 toggles an LED on D6 (+ D13); a jumper D6->D3 lets the MCU independently witness the LED line
 * switching; a software wall clock is synced from the host (SET_TIME) and its drift measured from the SECOND sync;
 * every press / LED change / sensed edge / sync is queued as a ButtonClockEvent (bounded, drop-oldest). PLAIN C on
 * avr-libc (RULE 2: no Arduino core). `pol board gen` copies this file into the project as main.c.
 *
 * The six POLARI_NODE atoms (each parsed from this file, never hand-listed into a graph — ucd-0e2b adds the graph):
 *   clock_tick     uptime_ms (hal_millis, wrap-safe) -> the device's wall-clock ESTIMATE (sync offset + elapsed)
 *   clock_set      a SET_TIME: records the sync, bumps sync_generation, sets sync_uncertainty_ms, measures drift_ms
 *                  from the SECOND sync on
 *   led_toggle     on the button atom's (hal.c HAL_INT0) toggle-pending flag: flips D6 + D13, stamps led_changed_at
 *   sense_isr      drains the sense atom's (hal.c HAL_INT1) rise/fall counters + last-edge stamp; the real ISR only
 *                  counts (hal.c ISR(INT1_vect)) — this main-loop task emits the sense_rise/sense_fall events
 *   events_queue   the bounded ButtonClockEvent ring: drop-oldest on overflow, counted in dropped_events
 *   telemetry_send every TELEMETRY_HZ: one ButtonClockState frame (an ATOMIC_BLOCK snapshot — §5e "Adopted":
 *                  acquisition and publication as separate atoms), then drains the queue as ButtonClockEvent frames
 *
 * The time model (§5g, adopted): uptime_ms is the device's own monotonic clock, never reset by a sync; epoch_s/ms is
 * the device's ESTIMATE (the last sync's host time + elapsed uptime since it, wrap-safe: unsigned subtraction, the
 * same idiom as hal_millis()'s own callers); sync_generation is whatever the host's latest SET_TIME said; drift_ms is
 * measured ONLY at a sync (device estimate just before the set, minus the host's new time) and only from the SECOND
 * sync on (the first sync has nothing to compare against); sync_uncertainty_ms is the frame period — an honest, cheap
 * bound on how far the estimate may have wandered since that sync (no oscillator-drift model is claimed).
 *
 * boot_session (§5g "Boot session != packet sequence") is minted once at reset from an EEPROM counter (avr-libc
 * <avr/eeprom.h>: eeprom_read_dword / eeprom_write_dword) and stamped on every frame of both classes: a NEW
 * boot_session on an otherwise-live link means the device rebooted; the SAME boot_session with a seq gap means the
 * transport lost frames — never confused (ucd-0e3's bridge already reads this field this way).
 */
#include <avr/eeprom.h>
#include <avr/interrupt.h>
#include <avr/io.h>
#include <stdint.h>
#include <string.h>
#include <util/atomic.h>

#include "board_config.h"          /* knobs rendered by `pol board gen`: RIG_NAME, DEVICE_ID, pins, features, EVENT_QUEUE_LEN */
#include "hal.h"
#include "buttonclockstate_packets.h"   /* GENERATED (c_twin target=avr) — never edited by hand */
/* ButtonClockEvent is telemetry-only (no command path): its decode()/decode_rx() are unused and dropped by the
 * compiler — the same idiom analog.c uses for UnoAnalogState (also telemetry-only). */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "buttonclockevent_packets.h"   /* GENERATED (c_twin target=avr) — never edited by hand */
#pragma GCC diagnostic pop
/* ucd-0e2b: the macros/typedef/globals several atoms below share, moved into their own header so cmod.custom.glue's
 * no-code graph can copy those atoms' bodies verbatim (its one rule: a copied atom compiles from headers alone,
 * never a macro the app .c file defines itself) — a pure relocation, same text, same compiled bytes. */
#include "button_clock_defs.h"

static void l_led_init(void)
{
#ifndef POLARI_PIN_CONFIG
    L_LED_DDR |= _BV(L_LED_BIT);
#endif
}

/* ucd-0e2b: uses(L_LED_PIN) is a FIXED label (D13, never a knob — see l_led_init's own comment above), so
 * cmod.custom.targets can bind this task to D13 directly, by name; l_led_init (no ports of its own to infer a
 * direction from) inherits D13 + this atom's 'digital-out' kind through its runtime counterpart, the same
 * init/counterpart convention hal_led_init already uses via hal_led. Annotation only. */
POLARI_NODE(l_led_set, in(on, "bool", "0 = off, anything else = on"), uses(L_LED_PIN),
            role("mirror led_on onto the on-board L LED (D13, fixed — never a configurable knob)"))
static void l_led_set(uint8_t on)
{
    if (on) L_LED_PORT |= _BV(L_LED_BIT); else L_LED_PORT &= (uint8_t)~_BV(L_LED_BIT);
}

/* ucd-0e2: boot_session persists across resets in EEPROM (avr-libc <avr/eeprom.h> eeprom_read_dword/eeprom_write_dword
 * — their own busy-wait on EEPE, no extra code here). EEPROM_BOOT_SESSION_ADDR (button_clock_defs.h): address 0x0000
 * of the ATmega328P's 1 KiB EEPROM (DS40002061B §4, the memory map); nothing else in this firmware touches EEPROM. A
 * virgin chip reads 0xFFFFFFFF — treated as "no prior session" (0), so the first boot_session minted on a fresh chip
 * is 1, never 0 (0 would read as "falsy" on a backend that treats the field loosely). */
POLARI_NODE(boot_session_mint, out(return, "", "the freshly-minted boot_session (1 on a virgin chip, else +1)"),
            role("mint this boot's session counter from EEPROM (ucd-0e2b: wired as an init field into state.boot_session, after the class memset, before sei)"))
static uint32_t boot_session_mint(void)
{
    uint32_t v = eeprom_read_dword(EEPROM_BOOT_SESSION_ADDR);
    if (v == 0xFFFFFFFFul) v = 0u;
    v++;
    eeprom_write_dword(EEPROM_BOOT_SESSION_ADDR, v);
    return v;
}

/* static, so avr-size counts them (the RAM budget is measured, not guessed). `state`/`rx` stay HERE (not in
 * button_clock_defs.h): the GENERATED glue declares its OWN, under the same names, for its class/parser graph nodes
 * — the hand-written and generated builds never share a translation unit, so nothing is duplicated. */
static ButtonClockState_t state;
static polari_rx_t rx;

/* ---- clock.tick: the device's wall-clock ESTIMATE = the last sync's host time + elapsed uptime since it. Wrap-safe:
 * `now_ms - base_uptime_ms` is an unsigned subtraction, so it reads correctly across a hal_millis() wraparound (~49.7
 * days) the same way main()'s own `(int32_t)(now - next_ms) < 0` schedule check already relies on. Before the first
 * SET_TIME (state.clock_synced false) the estimate is 0,0 — never a guess. ---- */
POLARI_NODE(clock_tick, in(now_ms, "ms", "hal_millis() right now"), out(epoch_s, "s", "the device's current wall-clock estimate"),
            out(ms, "ms", "...within the second"),
            role("advance the wall-clock estimate = the last SET_TIME's host time + elapsed uptime since it"))
static void clock_tick(uint32_t now_ms, int64_t *epoch_s, int64_t *ms)
{
    uint32_t elapsed, total_ms;
    if (!state.clock_synced) { *epoch_s = 0; *ms = 0; return; }
    elapsed = now_ms - g_sync_base_uptime_ms;             /* wrap-safe: unsigned */
    total_ms = (uint32_t)g_sync_base_ms + elapsed;
    *epoch_s = g_sync_base_epoch_s + (int64_t)(total_ms / 1000u);
    *ms = (int64_t)(total_ms % 1000u);
}

/* ---- clock.set: a SET_TIME lands. Bumps sync_generation to whatever the HOST said (never incremented locally);
 * sync_uncertainty_ms is the frame period — the honest, cheap bound on how far the estimate may wander before the
 * next sync (no oscillator-drift model claimed); drift_ms is measured ONLY from the SECOND sync on (device's own
 * estimate just before adopting the new time, minus the host's new time) — the first sync has nothing prior to
 * compare against, so drift_ms stays whatever it was (0 at boot). Emits a `sync` event. ---- */
POLARI_NODE(clock_set, in(set_epoch_s, "s", "the host's SET_TIME"), in(set_ms, "ms", "...within the second"),
            in(set_sync_generation, "", "the host's generation counter"), in(now_ms, "ms", "hal_millis() right now"),
            role("record one SET_TIME sync: bump sync_generation, set sync_uncertainty_ms, measure drift_ms from the 2nd sync on"))
static void clock_set(int64_t set_epoch_s, int64_t set_ms, int64_t set_sync_generation, uint32_t now_ms)
{
    if (state.clock_synced) {
        int64_t prev_epoch_s, prev_ms, prev_total_ms, host_total_ms;
        clock_tick(now_ms, &prev_epoch_s, &prev_ms);
        prev_total_ms = prev_epoch_s * 1000 + prev_ms;
        host_total_ms = set_epoch_s * 1000 + set_ms;
        state.drift_ms = prev_total_ms - host_total_ms;    /* measured AT this sync only — never carried/extrapolated */
    }
    g_sync_base_epoch_s = set_epoch_s;
    g_sync_base_ms = (uint16_t)set_ms;
    g_sync_base_uptime_ms = now_ms;
    state.sync_generation = set_sync_generation;
    state.sync_uncertainty_ms = (int64_t)TELEMETRY_MS;     /* the frame period: an honest bound, not a drift model */
    state.clock_synced = 1u;
}

/* ---- events.queue: a bounded ring, drop-oldest on overflow (dropped_events counts what was lost since it was last
 * read). seq is assigned at SEND time (events_drain), not here — the ring holds only what a queued transition needs. */
POLARI_NODE(events_queue, in(kind, "enum", "press | led_on | led_off | sense_rise | sense_fall | sync"),
            in(at_ms, "ms", "device uptime at the moment of the event"),
            role("push one transition into the bounded ring; drop-oldest on overflow, counted in dropped_events"))
static void events_queue(uint8_t kind, uint32_t at_ms)
{
    int64_t es, ms;
    if (g_qcount == EVENT_QUEUE_LEN) {
        g_qtail = (uint8_t)((g_qtail + 1u) % EVENT_QUEUE_LEN);   /* drop-oldest: the oldest queued entry is gone */
        g_qcount--;
        state.dropped_events++;
    }
    clock_tick(at_ms, &es, &ms);
    g_queue[g_qhead].kind = kind;
    g_queue[g_qhead].uptime_ms = at_ms;
    g_queue[g_qhead].epoch_s = (int32_t)es;
    g_queue[g_qhead].ms = (uint16_t)ms;
    g_qhead = (uint8_t)((g_qhead + 1u) % EVENT_QUEUE_LEN);
    g_qcount++;
}

static int queue_pop(qevent_t *out)
{
    if (!g_qcount) return 0;
    *out = g_queue[g_qtail];
    g_qtail = (uint8_t)((g_qtail + 1u) % EVENT_QUEUE_LEN);
    g_qcount--;
    return 1;
}

/* ---- led.toggle: the main-loop half of "the button" (hal.c's HAL_INT0 ISR only counts + marks toggle-pending). One
 * debounced press = exactly one `press` event, one LED flip, one `led_on`/`led_off` event — the invariant the proof
 * checks (sense_rises + sense_falls == button_presses when D6 is wired to D3; led_on == sense_rises > sense_falls). */
POLARI_NODE(led_toggle, role("on the button atom's toggle-pending flag: flip state.led_on, stamp led_changed_at, emit events (the pins follow the struct: led_follow_state)"))
static void led_toggle(uint32_t now_ms)
{
#if HAL_INT0
    int64_t es, ms;
    if (!hal_take_toggle_pending()) return;
    state.button_presses = (int64_t)hal_presses();
    events_queue(BUTTONCLOCKEVENT_KIND_PRESS, now_ms);
    state.led_on = state.led_on ? 0u : 1u;
    clock_tick(now_ms, &es, &ms);
    state.led_changed_at = es;
    events_queue(state.led_on ? BUTTONCLOCKEVENT_KIND_LED_ON : BUTTONCLOCKEVENT_KIND_LED_OFF, now_ms);
#else
    (void)now_ms;
#endif
}

/* ---- sense.isr (the main-loop drain — the real ISR, hal.c's ISR(INT1_vect), only counts + stamps last_ms): any NEW
 * rise/fall since the last pass becomes one sense_rise/sense_fall event, stamped with the device's own clock. ---- */
POLARI_NODE(sense_isr, uses(SENSE_PIN), role("drain the sense atom's rise/fall counters; emit sense_rise/sense_fall for new edges"))
static void sense_isr(void)
{
#if HAL_INT1
    static uint16_t g_prev_rises, g_prev_falls;
    uint16_t rises, falls, dr, df;
    uint32_t last_ms;
    int64_t es, ms;
    hal_sense_read(&rises, &falls, &last_ms);
    dr = (uint16_t)(rises - g_prev_rises);
    df = (uint16_t)(falls - g_prev_falls);
    if (!dr && !df) return;
    state.sense_rises = rises;
    state.sense_falls = falls;
    clock_tick(last_ms, &es, &ms);
    state.last_edge_at = es;
    state.last_edge_ms = ms;
    while (dr--) events_queue(BUTTONCLOCKEVENT_KIND_SENSE_RISE, last_ms);
    while (df--) events_queue(BUTTONCLOCKEVENT_KIND_SENSE_FALL, last_ms);
    g_prev_rises = rises;
    g_prev_falls = falls;
#endif
}

/* STATE_TELEMETRY_MASK / EVENT_TELEMETRY_MASK (button_clock_defs.h): every telemetry field, never a command field
 * (set_* / snapshot are input-only). */
static void events_drain(void)
{
    qevent_t e;
    ButtonClockEvent_t ev;
    while (queue_pop(&e)) {
        memset(&ev, 0, sizeof ev);
#if SEND_NAME
        strcpy(ev.name, RIG_NAME);
#endif
        ev.boot_session = state.boot_session;
        ev.kind = e.kind;
        ev.uptime_ms = (int64_t)e.uptime_ms;
        ev.epoch_s = (int64_t)e.epoch_s;
        ev.ms = (int64_t)e.ms;
        ev.seq = (int64_t)g_seq_e;
        hal_usart_send(wire, ButtonClockEvent_frame(wire, DEVICE_ID, g_seq_e, payload, TX_ENCODE_E(&ev, payload, EVENT_TELEMETRY_MASK)));
        g_seq_e++;
    }
}

/* ---- telemetry.send: one ButtonClockState frame (an ATOMIC_BLOCK snapshot — acquisition and publication are
 * separate atoms, §5e "Adopted"), then drains events.queue as ButtonClockEvent frames. SNAPSHOT is the same call,
 * invoked immediately from apply_command (not waiting for the next scheduled tick) with status overridden for that
 * one frame only. ---- */
POLARI_NODE(telemetry_send, in(now_ms, "ms", "hal_millis() right now"),
            role("one ButtonClockState frame (atomic snapshot) then drain events.queue as ButtonClockEvent frames"))
static void telemetry_send(uint32_t now_ms)
{
    ButtonClockState_t snap;
    int64_t es, ms;
    clock_tick(now_ms, &es, &ms);
    state.uptime_ms = (int64_t)now_ms;
    state.epoch_s = es;
    state.ms = ms;
    state.seq = (int64_t)g_seq_s;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { snap = state; }
    hal_usart_send(wire, ButtonClockState_frame(wire, DEVICE_ID, g_seq_s, payload, TX_ENCODE_S(&snap, payload, STATE_TELEMETRY_MASK)));
    g_seq_s++;
    events_drain();
}

/* THE STRUCT CONTROLS THE LIGHT (slice scl): the mutators (led_toggle, apply_command) only alter state.led_on; this atom, called every
 * main-loop pass, is the only thing that drives D6 and the L LED (D13): when the struct's led_on differs from the value last written, it writes both. */
POLARI_NODE(led_follow_state, uses(LED_PIN), role("each pass: when state.led_on differs from the value last written to the pins, drive D6 + D13 to it"))
static void led_follow_state(void)
{
    static uint8_t pin = 0u;               /* the init functions leave both pins low */
    if (state.led_on == pin) return;
    pin = state.led_on ? 1u : 0u;
    hal_led(pin);
    l_led_set(pin);
}

POLARI_NODE(apply_command, in(r, "frame", "a parsed PolariPacket ButtonClockState command"),
            role("SET_TIME -> clock_set; SET_LED -> state.led_on (the pins follow: led_follow_state); SNAPSHOT -> a frame + queue replay now"))
static void apply_command(const polari_rx_t *r)
{
    ButtonClockState_t cmd;
    ButtonClockState_mask_t m;
    uint32_t now_ms = hal_millis();
    if (ButtonClockState_decode_rx(r, &cmd, &m) != 0) return;
    if (m & BUTTONCLOCKSTATE_F_SET_EPOCH_S) {
        int64_t set_ms = (m & BUTTONCLOCKSTATE_F_SET_MS) ? cmd.set_ms : 0;
        int64_t gen = (m & BUTTONCLOCKSTATE_F_SET_SYNC_GENERATION) ? cmd.set_sync_generation : state.sync_generation;
        clock_set(cmd.set_epoch_s, set_ms, gen, now_ms);
        events_queue(BUTTONCLOCKEVENT_KIND_SYNC, now_ms);
        g_status_base = BUTTONCLOCKSTATE_STATUS_SYNCED;
        state.status = g_status_base;
    }
    if (m & BUTTONCLOCKSTATE_F_SET_LED) {
        int64_t es, ms;
        state.led_on = cmd.set_led ? 1u : 0u;
        clock_tick(now_ms, &es, &ms);
        state.led_changed_at = es;
        events_queue(state.led_on ? BUTTONCLOCKEVENT_KIND_LED_ON : BUTTONCLOCKEVENT_KIND_LED_OFF, now_ms);
        if (!(m & BUTTONCLOCKSTATE_F_SET_EPOCH_S)) {
            g_status_base = BUTTONCLOCKSTATE_STATUS_COMMANDED;
            state.status = g_status_base;
        }
    }
    if (m & BUTTONCLOCKSTATE_F_SNAPSHOT) {
        state.status = BUTTONCLOCKSTATE_STATUS_SNAPSHOT;   /* this ONE frame only; telemetry_send sends it right away */
        telemetry_send(now_ms);
        state.status = g_status_base;
    }
}

int main(void)
{
    uint32_t next_ms = 0u, now;
    uint8_t b;

    hal_usart_init();
    hal_tick_init();
    hal_led_init();
    l_led_init();
#if HAL_INT0
    hal_button_init();
#endif
#if HAL_INT1
    hal_sense_init();
#endif
    memset(&state, 0, sizeof state);
    memset(&rx, 0, sizeof rx);
#if SEND_NAME
    strcpy(state.name, RIG_NAME);
#endif
    g_status_base = BUTTONCLOCKSTATE_STATUS_IDLE;
    state.status = g_status_base;
    state.boot_session = (int64_t)boot_session_mint();
    sei();

    for (;;) {
        while (hal_rx_pop(&b))
            if (polari_rx_feed(&rx, b) && rx.msg_type == BUTTONCLOCKSTATE_MSG_TYPE)
                apply_command(&rx);

        now = hal_millis();
        led_toggle(now);
        led_follow_state();
        sense_isr();
#if LOOP_DELAY_MS
        /* smp-1 (sample failure F2): a deliberately slow pass. The press is only acted on here, once per pass, so it is acted on up to LOOP_DELAY_MS late. */
        { uint32_t t0 = hal_millis(); while ((uint32_t)(hal_millis() - t0) < (uint32_t)LOOP_DELAY_MS) { } }
#endif

        if ((int32_t)(now - next_ms) < 0) continue;
        next_ms += TELEMETRY_MS;
        telemetry_send(now);
    }
}
