/*
 * variant app `sim_rig` (sc-3; variant c3-sim-rig) — the ESP32-C3 as one Polari rig: SimRigState telemetry up and
 * commands down over UART0, as FreeRTOS tasks. PLAIN C on ESP-IDF (RULE 2). The same frames as the UNO's sim_rig
 * (the SAME generated header, rendered target=host), so the SAME bridge attaches to the twin's pty or a real board.
 *
 *   Up:   SimRigState at TELEMETRY_HZ — uptime_ms from esp_timer, status 'boot' → 'ok' after 1 s → 'commanded', led_on and
 *         pwm_duty as last commanded. temp_c is NOT sent: this rig has no sensor wired, and the C3's internal
 *         temperature sensor is not emulated by Espressif's QEMU (a later variant reads it on silicon).
 *   Down: led_on / pwm_duty from a command are HELD and echoed in the next frame; no pin is driven yet (the QEMU twin
 *         emulates no LEDC/GPIO output the run could observe — said so rather than claimed).
 * The trace channel (UART1) carries @BOOT and nothing else for this app.
 */
#include "polari_c3.h"

static const int32_t DEFAULTS[8] = {0, 0, 0, 0, 0, 0, 0, 0};

void polari_app_command(const polari_cmd_t *c)
{
    if (c->has_led) g_tel.led_on = c->led_on ? 1u : 0u;
    if (c->has_steer) g_tel.steer = c->steer < 0 ? 0 : c->steer > 100 ? 100 : c->steer;   /* a duty, 0..100 % */
    g_tel.status = 3;   /* SIMRIGSTATE_STATUS_COMMANDED */
}

static void task_status(void *arg)
{
    (void)arg;
    vTaskDelay(pdMS_TO_TICKS(1000));
    if (g_tel.status == 1) g_tel.status = 2;   /* boot → ok */
    vTaskSuspend(NULL);
}

void polari_app_main(void)
{
    polari_c3_init(DEFAULTS, 0u, 0u);
    polari_telemetry_start(NULL, 5);
    polari_rx_start(5);
    xTaskCreate(task_status, "status", 2048, NULL, 4, NULL);
}
