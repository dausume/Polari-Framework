/*
 * polari_c3.c — UART0 frames (the generated SimRigState header, target=host), UART1 trace lines, the params partition,
 * the telemetry and command tasks, CPU work. See polari_c3.h. PLAIN C (RULE 2).
 */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "driver/uart.h"
#include "esp_partition.h"
#include "esp_timer.h"

#include "polari_c3.h"
#include "simrigstate_packets.h"   /* GENERATED (c_twin target=host) — never edited by hand */

#define TRACE_UART UART_NUM_1
#define FRAME_UART UART_NUM_0
#ifndef FEATURE_VALUE
#define FEATURE_VALUE 1            /* 0: telemetry carries no temp_c (c3-sim-rig: no sensor) */
#endif
#define PREEMPT_GAP_US 20          /* a gap longer than this between two clock reads = the task was not running */

polari_params_t g_params;
int g_params_source;
int g_steer_slot = -1;
volatile polari_tel_t g_tel = {0, 0.0, SIMRIGSTATE_STATUS_BOOT, 0};
volatile int g_tel_stop;

static SemaphoreHandle_t s_line_lock;
static SemaphoreHandle_t s_gate;

uint32_t polari_now_us(void)
{
    return (uint32_t)esp_timer_get_time();
}

void polari_work_us(uint32_t us)
{
    int64_t last = esp_timer_get_time(), acc = 0;
    while (acc < (int64_t)us) {
        int64_t t = esp_timer_get_time();
        int64_t d = t - last;
        if (d < PREEMPT_GAP_US) acc += d;
        last = t;
    }
}

void polari_line(const char *fmt, ...)
{
    char buf[160];
    va_list ap;
    int n;
    va_start(ap, fmt);
    n = vsnprintf(buf, sizeof buf - 1, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n > (int)sizeof buf - 2) n = (int)sizeof buf - 2;
    buf[n++] = '\n';
    if (s_line_lock) xSemaphoreTake(s_line_lock, portMAX_DELAY);
    uart_write_bytes(TRACE_UART, buf, (size_t)n);
    if (s_line_lock) xSemaphoreGive(s_line_lock);
}

static void uart_up(uart_port_t port, int rx_buf, int tx_buf, int tx_gpio)
{
    const uart_config_t cfg = {
        .baud_rate = 115200, .data_bits = UART_DATA_8_BITS, .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1, .flow_ctrl = UART_HW_FLOWCTRL_DISABLE, .source_clk = UART_SCLK_DEFAULT,
    };
    ESP_ERROR_CHECK(uart_driver_install(port, rx_buf, tx_buf, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(port, &cfg));
    if (tx_gpio >= 0)
        ESP_ERROR_CHECK(uart_set_pin(port, tx_gpio, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
}

void polari_c3_init(const int32_t defaults[8], uint32_t window_ms, uint32_t rounds)
{
    const esp_partition_t *p;
    polari_params_t fl;
    uart_up(FRAME_UART, 1024, 0, -1);                       /* UART0 keeps its default pins (GPIO21 TX / GPIO20 RX) */
    uart_up(TRACE_UART, 256, 8192, POLARI_TRACE_TX_GPIO);
    s_line_lock = xSemaphoreCreateMutex();
    memset(&g_params, 0, sizeof g_params);
    g_params.magic = POLARI_PARAMS_MAGIC;
    g_params.version = 1u;
    g_params.window_ms = window_ms;
    g_params.rounds = rounds;
    memcpy(g_params.a, defaults, sizeof g_params.a);
    g_params_source = 0;
    p = esp_partition_find_first(ESP_PARTITION_TYPE_DATA, (esp_partition_subtype_t)POLARI_PARAMS_SUBTYPE, "polari");
    if (p && esp_partition_read(p, 0, &fl, sizeof fl) == ESP_OK && fl.magic == POLARI_PARAMS_MAGIC && fl.version == 1u) {
        g_params = fl;
        g_params_source = 1;
    }
    polari_line("@BOOT app=%s rig=%s params=%s seed=%lu window_ms=%lu rounds=%lu a=%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld",
                POLARI_APP, RIG_NAME, g_params_source ? "flash" : "defaults", (unsigned long)g_params.seed,
                (unsigned long)g_params.window_ms, (unsigned long)g_params.rounds, (long)g_params.a[0], (long)g_params.a[1],
                (long)g_params.a[2], (long)g_params.a[3], (long)g_params.a[4], (long)g_params.a[5], (long)g_params.a[6],
                (long)g_params.a[7]);
}

/* ------------------------------------------------------------------ UART0: the frames */
static SimRigState_t s_state;
static uint8_t s_payload[SIMRIGSTATE_PAYLOAD_MAX];
static uint8_t s_wire[POLARI_HEADER_LEN + SIMRIGSTATE_PAYLOAD_MAX + 4u];
static polari_rx_t s_rx;

#define TELEMETRY_MASK ((SimRigState_mask_t)(SIMRIGSTATE_F_UPTIME_MS | SIMRIGSTATE_F_STATUS | (FEATURE_VALUE ? SIMRIGSTATE_F_TEMP_C : 0u) \
    | SIMRIGSTATE_F_LED_ON | SIMRIGSTATE_F_PWM_DUTY | (SEND_NAME ? SIMRIGSTATE_F_NAME : 0u)))

static void telemetry_task(void *arg)
{
    uint32_t seq = 0u;
    TickType_t wake = xTaskGetTickCount();
    (void)arg;
    for (;;) {
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(1000u / TELEMETRY_HZ));
        if (g_tel_stop) vTaskSuspend(NULL);
        if (s_gate) xSemaphoreTake(s_gate, portMAX_DELAY);   /* two-lock: the snapshot needs lock A — a deadlock stops it */
        s_state.uptime_ms = esp_timer_get_time() / 1000;
        s_state.status = g_tel.status;
        s_state.temp_c = g_tel.value;
        s_state.pwm_duty = g_tel.steer;
        s_state.led_on = g_tel.led_on;
        if (s_gate) xSemaphoreGive(s_gate);
        uart_write_bytes(FRAME_UART, s_wire, SimRigState_frame(s_wire, DEVICE_ID, seq++, s_payload,
                                                               SimRigState_encode(&s_state, s_payload, TELEMETRY_MASK)));
    }
}

void polari_window_end(void)
{
    g_tel_stop = 1;
    polari_trace_stop();
    vTaskDelay(pdMS_TO_TICKS(2));   /* a frame already being written finishes before the decision lines */
}

void polari_telemetry_start(SemaphoreHandle_t gate, UBaseType_t prio)
{
    TaskHandle_t h;
    memset(&s_state, 0, sizeof s_state);
    strncpy(s_state.name, RIG_NAME, sizeof s_state.name - 1);
    s_gate = gate;
    xTaskCreate(telemetry_task, "tel", 3072, NULL, prio, &h);
    polari_trace_task(h, 9, "TEL");
}

__attribute__((weak)) void polari_app_command(const polari_cmd_t *c)
{
    if (c->has_led) g_tel.led_on = c->led_on ? 1u : 0u;
    if (c->has_steer && g_steer_slot >= 0 && g_steer_slot < 8) {
        g_params.a[g_steer_slot] = (int32_t)c->steer;
        g_params_source = 2;
        g_tel.steer = c->steer;
        polari_line("@STEER slot=%d value=%ld (a host command; the next round uses it)", g_steer_slot, (long)c->steer);
    }
    g_tel.status = SIMRIGSTATE_STATUS_COMMANDED;
}

static void rx_task(void *arg)
{
    uint8_t buf[64];
    (void)arg;
    memset(&s_rx, 0, sizeof s_rx);
    for (;;) {
        int n = uart_read_bytes(FRAME_UART, buf, sizeof buf, pdMS_TO_TICKS(20));
        for (int i = 0; i < n; i++) {
            if (polari_rx_feed(&s_rx, buf[i]) && s_rx.msg_type == SIMRIGSTATE_MSG_TYPE) {
                SimRigState_t cmd;
                SimRigState_mask_t m;
                polari_cmd_t c = {0, 0, 0, 0};
                memset(&cmd, 0, sizeof cmd);
                if (SimRigState_decode_rx(&s_rx, &cmd, &m) != 0) continue;
                if (m & SIMRIGSTATE_F_LED_ON) { c.has_led = 1; c.led_on = cmd.led_on; }
                if (m & SIMRIGSTATE_F_PWM_DUTY) { c.has_steer = 1; c.steer = cmd.pwm_duty; }
                polari_app_command(&c);
            }
        }
    }
}

void polari_rx_start(UBaseType_t prio)
{
    TaskHandle_t h;
    xTaskCreate(rx_task, "rx", 3072, NULL, prio, &h);
    polari_trace_task(h, 10, "RX");
}

void app_main(void)
{
    polari_app_main();
}
