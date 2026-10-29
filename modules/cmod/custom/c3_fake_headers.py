"""
@module cmod.custom.c3_fake_headers

The FAKE system headers the C3 firmware is parsed against (cmod.custom.c3_atoms) - the same recipe as cmod.custom.preprocess's AVR set: pycparser parses preprocessed
C99 only and the real ESP-IDF / FreeRTOS headers do not parse (GCC extensions, inline asm), so the parse sees stand-ins that declare exactly the TYPES and the
CONSTANTS the firmware uses, with RV32 (ilp32) widths. Function calls (gpio_set_level, xTaskCreate ...) need no prototype - pycparser does no semantic check - so
they stay calls by NAME, which is what the atom scan reads. This is a parse for structure, never a build (the build is ESP-IDF's, through prf-esp-engines).
"""
import hashlib
import os
import tempfile

_LIBC = {
    'stdint.h': ('typedef signed char int8_t; typedef unsigned char uint8_t; typedef short int16_t; typedef unsigned short uint16_t;\n'
                 'typedef int int32_t; typedef unsigned int uint32_t; typedef long long int64_t; typedef unsigned long long uint64_t;\n'
                 'typedef int32_t intptr_t; typedef uint32_t uintptr_t;\n#define UINT32_MAX 0xffffffffu\n#define INT32_MAX 0x7fffffff\n'),
    'stddef.h': 'typedef unsigned int size_t; typedef int ptrdiff_t;\n#define NULL ((void *)0)\n',
    'stdbool.h': '#define bool _Bool\n#define true 1\n#define false 0\n',
    'string.h': '#include <stddef.h>\n',
    'stdlib.h': '#include <stddef.h>\n',
    'stdio.h': '#include <stddef.h>\n#include <stdarg.h>\n',
    'stdarg.h': 'typedef char *va_list;\n#define va_start(ap, last) ((void)0)\n#define va_end(ap) ((void)0)\n#define va_arg(ap, t) ((t)0)\n',
    'inttypes.h': '#include <stdint.h>\n',
}
_FREERTOS = ('#include <stdint.h>\n#include <stddef.h>\n'
             'typedef void *TaskHandle_t; typedef void *QueueHandle_t; typedef void *SemaphoreHandle_t; typedef uint32_t TickType_t;\n'
             'typedef int BaseType_t; typedef unsigned int UBaseType_t; typedef struct { int owner; int count; } portMUX_TYPE;\n'
             '#define pdFALSE 0\n#define pdTRUE 1\n#define pdPASS 1\n#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))\n#define portMAX_DELAY 0xffffffffu\n'
             '#define portTICK_PERIOD_MS 1\n#define portYIELD_FROM_ISR(...) __polari_yield_from_isr()\n#define portMUX_INITIALIZER_UNLOCKED {0, 0}\n'
             '#define portENTER_CRITICAL(m) __polari_enter_critical(m)\n#define portEXIT_CRITICAL(m) __polari_exit_critical(m)\n'
             '#define taskENTER_CRITICAL(m) __polari_enter_critical(m)\n#define taskEXIT_CRITICAL(m) __polari_exit_critical(m)\n'
             '#define tskIDLE_PRIORITY 0\n#define configMAX_PRIORITIES 25\n')
_IDF = {
    'freertos/FreeRTOS.h': _FREERTOS,
    'freertos/task.h': '#include "freertos/FreeRTOS.h"\n',
    'freertos/queue.h': '#include "freertos/FreeRTOS.h"\n',
    'freertos/semphr.h': '#include "freertos/FreeRTOS.h"\n',
    'esp_err.h': ('typedef int esp_err_t;\n#define ESP_OK 0\n#define ESP_FAIL -1\n#define ESP_ERR_NVS_NO_FREE_PAGES 0x110d\n#define ESP_ERR_NVS_NEW_VERSION_FOUND 0x1110\n'
                  '#define ESP_ERROR_CHECK(x) __polari_error_check(x)\n'),
    'esp_attr.h': '#define IRAM_ATTR\n#define DRAM_ATTR\n#define RTC_DATA_ATTR\n#define RTC_NOINIT_ATTR\n',
    'esp_timer.h': '#include <stdint.h>\n#include "esp_err.h"\n',
    'esp_cpu.h': '#include <stdint.h>\n',
    'esp_partition.h': ('#include <stdint.h>\n#include <stddef.h>\n#include "esp_err.h"\n'
                        'typedef int esp_partition_type_t; typedef int esp_partition_subtype_t;\n'
                        'typedef struct { esp_partition_type_t type; esp_partition_subtype_t subtype; uint32_t address; uint32_t size; char label[17]; } esp_partition_t;\n'
                        '#define ESP_PARTITION_TYPE_DATA 1\n#define ESP_PARTITION_SUBTYPE_ANY 0xff\n'),
    'nvs.h': '#include <stdint.h>\n#include "esp_err.h"\ntypedef uint32_t nvs_handle_t;\n#define NVS_READWRITE 1\n#define NVS_READONLY 0\n',
    'nvs_flash.h': '#include "nvs.h"\n',
    'driver/gpio.h': ('#include <stdint.h>\n#include "esp_err.h"\ntypedef int gpio_num_t;\n'
                      'typedef enum { GPIO_MODE_DISABLE = 0, GPIO_MODE_INPUT = 1, GPIO_MODE_OUTPUT = 2, GPIO_MODE_INPUT_OUTPUT = 3 } gpio_mode_t;\n'
                      'typedef enum { GPIO_PULLUP_DISABLE = 0, GPIO_PULLUP_ENABLE = 1 } gpio_pullup_t;\n'
                      'typedef enum { GPIO_PULLDOWN_DISABLE = 0, GPIO_PULLDOWN_ENABLE = 1 } gpio_pulldown_t;\n'
                      'typedef enum { GPIO_INTR_DISABLE = 0, GPIO_INTR_POSEDGE = 1, GPIO_INTR_NEGEDGE = 2, GPIO_INTR_ANYEDGE = 3 } gpio_int_type_t;\n'
                      'typedef struct { uint64_t pin_bit_mask; gpio_mode_t mode; gpio_pullup_t pull_up_en; gpio_pulldown_t pull_down_en; gpio_int_type_t intr_type; } gpio_config_t;\n'),
    'driver/uart.h': ('#include <stdint.h>\n#include <stddef.h>\n#include "esp_err.h"\n#include "freertos/FreeRTOS.h"\ntypedef int uart_port_t;\n'
                      '#define UART_NUM_0 0\n#define UART_NUM_1 1\n#define UART_PIN_NO_CHANGE (-1)\n#define UART_DATA_8_BITS 3\n#define UART_PARITY_DISABLE 0\n'
                      '#define UART_STOP_BITS_1 1\n#define UART_HW_FLOWCTRL_DISABLE 0\n#define UART_SCLK_DEFAULT 1\n'
                      'typedef struct { int baud_rate; int data_bits; int parity; int stop_bits; int flow_ctrl; uint8_t rx_flow_ctrl_thresh; int source_clk; } uart_config_t;\n'),
}
FAKE_HEADERS = dict(_LIBC, **_IDF)
_DIR = None


def sha():
    h = hashlib.sha256()
    for k in sorted(FAKE_HEADERS):
        h.update(k.encode() + b'\0' + FAKE_HEADERS[k].encode() + b'\0')
    return h.hexdigest()


def fake_dir():
    global _DIR
    if _DIR and os.path.isdir(_DIR):
        return _DIR
    d = tempfile.mkdtemp(prefix='cmod-fake-c3-')
    for name, text in FAKE_HEADERS.items():
        p = os.path.join(d, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as fh:
            fh.write(text)
    _DIR = d
    return d
