/*
 * light_hal.h (smp S5; the light app's pin layer). PLAIN C on ESP-IDF. THREE functions are everything the light app asks of its pins:
 *
 *   hal_pins_init()       configure the LED pin (output), the sense pin (input, pull-down) and the button pin (input, pull-up, falling edge)
 *   hal_button_arm(task)  from now on every falling edge on the button pin notifies `task` (the chip: a GPIO interrupt; the shim: its script)
 *   hal_led_write(level)  drive the LED pin
 *   hal_sense_read()      read the sense pin (the jumper from the LED pin)
 *
 * PIN_SHIM 0 = the CHIP HAL (ESP-IDF's gpio driver; button = interrupt service routine -> task notification). PIN_SHIM 1 = THE TWIN SHIM: Espressif's QEMU
 * esp32c3 machine models the GPIO block as a register stub (writes are dropped, GPIO_IN never moves; measured 2026-10-19: GPIO_OUT stays 0 after
 * gpio_set_level), so a pin cannot be pressed or read from outside. The shim keeps the pin levels in RAM instead:
 *   the LED level is a variable, logged on the trace line `@LED <ms> <level>` when it is written;
 *   the sense pin reads that variable when the jumper is fitted (params a[5] = 1), else 0 (the pull-down);
 *   the button follows a SCRIPT from the params partition (a[0] first press ms, a[1] gap ms, a[2] hold ms, a[3] presses, a[4] the GPIO the script presses);
 *   a press on a pin other than BUTTON_GPIO never reaches the button task - a negative control.
 * Everything above the HAL (the tasks, the struct, the frames) is identical in both builds. The chip HAL has NOT run on a chip (no C3 on the bench).
 */
#ifndef LIGHT_HAL_H
#define LIGHT_HAL_H

#include <stdint.h>

#include "driver/gpio.h"
#include "esp_attr.h"

#include "polari_c3.h"

static volatile int s_led_level;

#if PIN_SHIM

static TaskHandle_t s_shim_target;

static void shim_script_task(void *arg)
{
    int level = 1;   /* the button idles high (pull-up), a press pulls it low */
    (void)arg;
    for (;;) {
        uint32_t t = polari_now_us() / 1000u;
        int want = 1;
        int32_t first = g_params.a[0], gap = g_params.a[1], hold = g_params.a[2], n = g_params.a[3];
        if (n > 0 && gap > 0 && (int32_t)t >= first && g_params.a[4] == BUTTON_GPIO) {
            uint32_t k = (t - (uint32_t)first) / (uint32_t)gap;
            if ((int32_t)k < n && (t - (uint32_t)first) % (uint32_t)gap < (uint32_t)hold) want = 0;
        }
        if (level && !want && s_shim_target) xTaskNotifyGive(s_shim_target);   /* the falling edge: what the interrupt service routine does on a chip */
        level = want;
        vTaskDelay(1);
    }
}

static void hal_pins_init(void) { s_led_level = 0; }

static void hal_button_arm(TaskHandle_t task)
{
    s_shim_target = task;
    xTaskCreate(shim_script_task, "pinshim", 2048, NULL, 7, NULL);
}

static void hal_led_write(int level)
{
    s_led_level = level;
    polari_line("@LED %lu %d", (unsigned long)(polari_now_us() / 1000u), level);
}

static int hal_sense_read(void) { return g_params.a[5] ? s_led_level : 0; }

#else /* the chip HAL */

static TaskHandle_t s_button_target;

static void IRAM_ATTR button_isr(void *arg)
{
    BaseType_t woken = pdFALSE;
    (void)arg;
    vTaskNotifyGiveFromISR(s_button_target, &woken);
    if (woken) portYIELD_FROM_ISR();
}

static void hal_pins_init(void)
{
    const gpio_config_t led = {.pin_bit_mask = 1ULL << LED_GPIO, .mode = GPIO_MODE_OUTPUT};
    const gpio_config_t sense = {.pin_bit_mask = 1ULL << SENSE_GPIO, .mode = GPIO_MODE_INPUT, .pull_down_en = GPIO_PULLDOWN_ENABLE};
    const gpio_config_t button = {.pin_bit_mask = 1ULL << BUTTON_GPIO, .mode = GPIO_MODE_INPUT, .pull_up_en = GPIO_PULLUP_ENABLE, .intr_type = GPIO_INTR_NEGEDGE};
    ESP_ERROR_CHECK(gpio_config(&led));
    ESP_ERROR_CHECK(gpio_config(&sense));
    ESP_ERROR_CHECK(gpio_config(&button));
    ESP_ERROR_CHECK(gpio_set_level(LED_GPIO, 0));
}

static void hal_button_arm(TaskHandle_t task)
{
    s_button_target = task;
    ESP_ERROR_CHECK(gpio_install_isr_service(0));
    ESP_ERROR_CHECK(gpio_isr_handler_add(BUTTON_GPIO, button_isr, NULL));
}

static void hal_led_write(int level)
{
    s_led_level = level;
    gpio_set_level(LED_GPIO, level);
}

static int hal_sense_read(void) { return gpio_get_level(SENSE_GPIO); }

#endif /* PIN_SHIM */

#endif /* LIGHT_HAL_H */
