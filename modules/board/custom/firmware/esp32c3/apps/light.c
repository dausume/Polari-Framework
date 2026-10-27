/*
 * variant app `light` (smp S5; variant esp32c3-light) - THE LIGHT MISSION on the ESP32-C3 under FreeRTOS: one LED, switched from the board's button
 * and from Polari, reported up at 10 Hz, with the LED line sensed back on a second pin. PLAIN C on ESP-IDF's FreeRTOS (RULE 2).
 * The same struct and wire as the UNO's uno-light-sense-poll: ButtonClockState (+ ButtonClockEvent), v1 contract, wire v2, the same field meanings
 * (led_on, button_presses, sense_rises/falls, status idle|commanded, boot_session, set_led = the command field). The clock-sync fields are not used.
 *
 * THE STRUCT CONTROLS THE LIGHT (scl). The MUTATORS only alter the struct:
 *   led_toggle     (button task)   a debounced press: button_presses++, led_on flips, `press` and `led_on|led_off` events
 *   apply_command  (rx task)       SET_LED: led_on = set_led, status commanded, a `led_on|led_off` event
 * ONE task drives the LED pin, and only from the struct:
 *   led_follow_state  every tick: when state.led_on differs from what the pin was last set to, write the pin.
 *
 * FreeRTOS tasks (priorities: higher number runs first): button 6 - rx 5 - telemetry 5 - sense 4 - led_follow 3 (+ the pin shim 7 and a window timer 2 on the twin).
 *   rx         reads UART0, parses frames, calls apply_command
 *   button     waits for a notification from the button pin's falling edge, 30 ms lockout, calls led_toggle
 *   sense      polls the sense pin each tick, counts rises/falls (the LED line jumpered back), queues sense_rise/sense_fall events
 *   telemetry  every 100 ms (10 Hz): one ButtonClockState frame (a snapshot under the lock), then the queued ButtonClockEvent frames, then the trace line `@TEL <seq>`
 *   led_follow see above
 * boot_session: a counter in NVS (flash), +1 at every start - the chip's EEPROM counter of the UNO. Pins: light_hal.h (chip HAL, or the twin's RAM shim).
 * Params (the `polari` partition, steering the twin; defaults = a quiet board): a[0] first press ms, a[1] gap ms, a[2] hold ms, a[3] presses, a[4] GPIO pressed, a[5] sense jumper;
 * window_ms > 0 ends the run with `@END` on the trace.
 */
#include <string.h>

#include "driver/uart.h"
#include "esp_timer.h"
#include "freertos/queue.h"
#include "nvs.h"
#include "nvs_flash.h"

#include "polari_c3.h"
#include "buttonclockstate_packets.h"   /* GENERATED (c_twin target=host) - never edited by hand */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "buttonclockevent_packets.h"   /* GENERATED (c_twin target=host) - telemetry only */
#pragma GCC diagnostic pop
#include "light_hal.h"

#define FRAME_UART UART_NUM_0
#define TELEMETRY_MS (1000u / TELEMETRY_HZ)
#define STATE_MASK ((ButtonClockState_mask_t)(BUTTONCLOCKSTATE_F_BOOT_SESSION | BUTTONCLOCKSTATE_F_BUTTON_PRESSES | BUTTONCLOCKSTATE_F_DROPPED_EVENTS \
    | BUTTONCLOCKSTATE_F_LED_ON | (SEND_NAME ? BUTTONCLOCKSTATE_F_NAME : 0u) | BUTTONCLOCKSTATE_F_SENSE_FALLS | BUTTONCLOCKSTATE_F_SENSE_RISES \
    | BUTTONCLOCKSTATE_F_SEQ | BUTTONCLOCKSTATE_F_STATUS | BUTTONCLOCKSTATE_F_UPTIME_MS))
#define EVENT_MASK ((ButtonClockEvent_mask_t)(BUTTONCLOCKEVENT_F_BOOT_SESSION | BUTTONCLOCKEVENT_F_KIND | BUTTONCLOCKEVENT_F_SEQ | BUTTONCLOCKEVENT_F_UPTIME_MS))

typedef struct {
    uint8_t kind;
    uint32_t at_ms;
} qevent_t;

/* a quiet board: no scripted presses (a[3] = 0); the script's other slots hold the values a host run overrides */
static const int32_t DEFAULTS[8] = {300, 150, 80, 0, BUTTON_GPIO, 1, 0, 0};
static ButtonClockState_t state;
static SemaphoreHandle_t state_lock;
static QueueHandle_t evq;
static uint8_t payload[BUTTONCLOCKSTATE_PAYLOAD_MAX];
static uint8_t wire[POLARI_HEADER_LEN + BUTTONCLOCKSTATE_PAYLOAD_MAX + 4u];

static uint32_t now_ms(void)
{
    return (uint32_t)(esp_timer_get_time() / 1000);
}

static uint32_t boot_session_mint(void)
{
    nvs_handle_t h;
    uint32_t v = 0u;
    esp_err_t e = nvs_flash_init();
    if (e == ESP_ERR_NVS_NO_FREE_PAGES || e == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        e = nvs_flash_init();
    }
    if (e != ESP_OK || nvs_open("polari", NVS_READWRITE, &h) != ESP_OK) return 0u;
    if (nvs_get_u32(h, "boot_session", &v) != ESP_OK) v = 0u;
    v++;
    nvs_set_u32(h, "boot_session", v);
    nvs_commit(h);
    nvs_close(h);
    return v;
}

/* caller holds state_lock. A full queue drops the oldest event and counts it in dropped_events. */
static void events_queue(uint8_t kind)
{
    qevent_t e = {kind, now_ms()}, old;
    if (xQueueSend(evq, &e, 0) != pdTRUE) {
        xQueueReceive(evq, &old, 0);
        state.dropped_events++;
        xQueueSend(evq, &e, 0);
    }
}

/* MUTATOR: a debounced press of the board's button - flip the struct's led_on, count it. The pin follows the struct (led_follow_state). */
static void led_toggle(void)
{
    xSemaphoreTake(state_lock, portMAX_DELAY);
    state.button_presses++;
    events_queue(BUTTONCLOCKEVENT_KIND_PRESS);
    state.led_on = state.led_on ? 0u : 1u;
    events_queue(state.led_on ? BUTTONCLOCKEVENT_KIND_LED_ON : BUTTONCLOCKEVENT_KIND_LED_OFF);
    xSemaphoreGive(state_lock);
}

/* MUTATOR: the host's SET_LED - the struct's led_on takes the commanded value. The pin follows the struct (led_follow_state). */
static void apply_command(const polari_rx_t *r)
{
    ButtonClockState_t cmd;
    ButtonClockState_mask_t m;
    memset(&cmd, 0, sizeof cmd);
    if (ButtonClockState_decode_rx(r, &cmd, &m) != 0) return;
    if (m & BUTTONCLOCKSTATE_F_SET_LED) {
        xSemaphoreTake(state_lock, portMAX_DELAY);
        state.led_on = cmd.set_led ? 1u : 0u;
        events_queue(state.led_on ? BUTTONCLOCKEVENT_KIND_LED_ON : BUTTONCLOCKEVENT_KIND_LED_OFF);
        state.status = BUTTONCLOCKSTATE_STATUS_COMMANDED;
        xSemaphoreGive(state_lock);
    }
}

/* THE ONLY TASK THAT DRIVES THE LED PIN: whenever the struct's led_on differs from what the pin was last set to, set the pin. */
static void led_follow_task(void *arg)
{
    uint8_t pin = 0u;   /* hal_pins_init leaves the pin low */
    (void)arg;
    for (;;) {
        uint8_t want = *(volatile uint8_t *)&state.led_on;
        if (want != pin) {
            pin = want;
            hal_led_write(pin);
        }
        vTaskDelay(1);
    }
}

static void button_task(void *arg)
{
    uint32_t last = 0u;
    int have = 0;
    (void)arg;
    for (;;) {
        uint32_t t;
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        t = now_ms();
        if (have && (uint32_t)(t - last) < DEBOUNCE_MS) continue;   /* lockout: edges inside the debounce window are the same press */
        have = 1;
        last = t;
        led_toggle();
    }
}

static void sense_task(void *arg)
{
    int prev = hal_sense_read();
    (void)arg;
    for (;;) {
        int v = hal_sense_read();
        if (v != prev) {
            xSemaphoreTake(state_lock, portMAX_DELAY);
            if (v) state.sense_rises++; else state.sense_falls++;
            events_queue(v ? BUTTONCLOCKEVENT_KIND_SENSE_RISE : BUTTONCLOCKEVENT_KIND_SENSE_FALL);
            xSemaphoreGive(state_lock);
            prev = v;
        }
        vTaskDelay(1);
    }
}

static void send_events(uint32_t *seq_e)
{
    qevent_t e;
    ButtonClockEvent_t ev;
    while (xQueueReceive(evq, &e, 0) == pdTRUE) {
        memset(&ev, 0, sizeof ev);
        ev.boot_session = state.boot_session;
        ev.kind = e.kind;
        ev.uptime_ms = (int64_t)e.at_ms;
        ev.seq = (int64_t)*seq_e;
        uart_write_bytes(FRAME_UART, wire, ButtonClockEvent_frame(wire, DEVICE_ID, *seq_e, payload, ButtonClockEvent_encode(&ev, payload, EVENT_MASK)));
        (*seq_e)++;
    }
}

static void telemetry_task(void *arg)
{
    uint32_t seq_s = 0u, seq_e = 0u;
    TickType_t wake = xTaskGetTickCount();
    ButtonClockState_t snap;
    (void)arg;
    for (;;) {   /* the first report goes out at once (like the UNO's next_ms = 0), then one every TELEMETRY_MS */
        xSemaphoreTake(state_lock, portMAX_DELAY);
        state.uptime_ms = (int64_t)now_ms();
        state.seq = (int64_t)seq_s;
        snap = state;
        xSemaphoreGive(state_lock);
        uart_write_bytes(FRAME_UART, wire, ButtonClockState_frame(wire, DEVICE_ID, seq_s, payload, ButtonClockState_encode(&snap, payload, STATE_MASK)));
        polari_line("@TEL %lu", (unsigned long)seq_s);
        seq_s++;
        send_events(&seq_e);
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(TELEMETRY_MS));
    }
}

static void rx_task(void *arg)
{
    uint8_t buf[64];
    polari_rx_t rx;
    (void)arg;
    memset(&rx, 0, sizeof rx);
    for (;;) {
        int n = uart_read_bytes(FRAME_UART, buf, sizeof buf, pdMS_TO_TICKS(20));
        for (int i = 0; i < n; i++)
            if (polari_rx_feed(&rx, buf[i]) && rx.msg_type == BUTTONCLOCKSTATE_MSG_TYPE) apply_command(&rx);
    }
}

static void window_task(void *arg)
{
    (void)arg;
    vTaskDelay(pdMS_TO_TICKS(g_params.window_ms));
    polari_cycle_line("end");   /* ipb-4: the cycle counter beside the clock at the window's end */
    polari_line("@END presses=%lld led_on=%d", (long long)state.button_presses, state.led_on);
    vTaskSuspend(NULL);
}

void polari_app_main(void)
{
    TaskHandle_t btn;
    polari_c3_init(DEFAULTS, 0u, 0u);
    memset(&state, 0, sizeof state);
#if SEND_NAME
    strncpy(state.name, RIG_NAME, sizeof state.name - 1);
#endif
    state.status = BUTTONCLOCKSTATE_STATUS_IDLE;
    state.boot_session = (int64_t)boot_session_mint();
    state_lock = xSemaphoreCreateMutex();
    evq = xQueueCreate(EVENT_QUEUE_LEN, sizeof(qevent_t));
    hal_pins_init();
    xTaskCreate(button_task, "button", 2048, NULL, 6, &btn);
    xTaskCreate(sense_task, "sense", 2048, NULL, 4, NULL);
    xTaskCreate(led_follow_task, "led_follow", 2048, NULL, 3, NULL);
    xTaskCreate(telemetry_task, "telemetry", 4096, NULL, 5, NULL);
    xTaskCreate(rx_task, "rx", 4096, NULL, 5, NULL);
    if (g_params.window_ms) xTaskCreate(window_task, "window", 2048, NULL, 2, NULL);
    hal_button_arm(btn);
    polari_line("@UP %lu boot_session=%lld", (unsigned long)now_ms(), (long long)state.boot_session);
}
