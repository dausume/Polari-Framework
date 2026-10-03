/*
 * polari_c3.h — the ESP32-C3 template's common layer (sc-3; BOARD_PROGRAMMING_PLAN.md + FIRMWARE_SCENARIO_PLAN.md §3a
 * S6/S7). PLAIN C on ESP-IDF + its FreeRTOS (RULE 2: the language is C; CMake is only ESP-IDF's build system).
 *
 *   UART0  the SimRigState frames — the SAME generated header (c_twin target=host: riscv32-esp-elf's double is 8 bytes)
 *          at 115200 Bd, so the SAME bridge attaches (the twin: QEMU's UART0 on TCP → a pty; silicon: GPIO21/20 through
 *          the board's USB-UART). Telemetry up at TELEMETRY_HZ; commands down (led_on, pwm_duty = the scenario steer).
 *   UART1  the trace channel — text lines `@…` (the FreeRTOS trace hook events, markers, the decision lines). QEMU
 *          serves it as the second -serial; on silicon it is GPIO POLARI_TRACE_TX_GPIO through a USB-UART adapter.
 *   params a 4 KB data partition `polari` (subtype 0x40) the scenario runner writes into the flash image per seed: the
 *          SAME binary is steered without a rebuild. Absent (erased flash) = the build-time defaults in board_config.h.
 */
#ifndef POLARI_C3_H
#define POLARI_C3_H

#include <stdint.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#include "board_config.h"

#ifndef POLARI_TRACE_TX_GPIO
#define POLARI_TRACE_TX_GPIO 4      /* silicon only: UART1 TX for the trace lines (any free GPIO; QEMU ignores pins) */
#endif
#ifndef POLARI_TRACE_EVENTS
#define POLARI_TRACE_EVENTS 4096    /* the trace ring (8 B each); recording stops when full and the dump says so */
#endif

#define POLARI_PARAMS_MAGIC 0x33435350u   /* "PSC3" little-endian */
#define POLARI_PARAMS_SUBTYPE 0x40

typedef struct {
    uint32_t magic;       /* POLARI_PARAMS_MAGIC, else the defaults apply */
    uint32_t version;     /* 1 */
    uint32_t seed;        /* recorded; the offsets below were drawn from it host-side */
    uint32_t window_ms;   /* the scenario window after boot; then the decision lines and @END */
    uint32_t rounds;
    int32_t a[8];         /* the scenario's own knobs (each app documents its slots) */
} polari_params_t;

extern polari_params_t g_params;
extern int g_params_source;     /* 0 = build defaults, 1 = the flash partition, 2 = a host command changed a slot */

/* what the telemetry task sends (the app writes it; the telemetry task snapshots it, under `gate` when one is set) */
typedef struct {
    int64_t steer;        /* → pwm_duty: the scenario's steerable slot */
    double value;         /* → temp_c: the scenario's decisive value (each app says which; there is no sensor) */
    uint8_t status;       /* SIMRIGSTATE_STATUS_* number (1 boot, 2 ok, 3 commanded, 5 fault) */
    uint8_t led_on;
} polari_tel_t;
extern volatile polari_tel_t g_tel;
extern volatile int g_tel_stop;   /* the window is over: the telemetry task sends no more frames (UART0 stays byte-reproducible) */
void polari_window_end(void);      /* stop telemetry + recording; the decision lines follow */

/* a command decoded from UART0 (only present fields are set) */
typedef struct {
    int has_led, led_on;
    int has_steer;
    int64_t steer;
} polari_cmd_t;

void polari_c3_init(const int32_t defaults[8], uint32_t window_ms, uint32_t rounds);
void polari_telemetry_start(SemaphoreHandle_t gate, UBaseType_t prio);
void polari_rx_start(UBaseType_t prio);
void polari_line(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
uint32_t polari_now_us(void);
void polari_work_us(uint32_t us);   /* CPU work of `us` microseconds of THIS task's own run time (preemption excluded) */

/* the application (apps/<app>.c, copied as main/app.c) */
void polari_app_main(void);
void polari_app_command(const polari_cmd_t *c);   /* weak default: led_on held, steer → g_params.a[g_steer_slot] */
extern int g_steer_slot;                           /* the params slot a host command's pwm_duty steers (-1 = none) */

/* trace (polari_trace.c) */
#define POLARI_MARK_REQ      1   /* about to take (obj = the lock) */
#define POLARI_MARK_ACQ      2   /* took it */
#define POLARI_MARK_REL      3   /* gave it */
#define POLARI_MARK_BUSY0    4   /* a busy run starts */
#define POLARI_MARK_BUSY1    5   /* a busy run ends */
#define POLARI_MARK_ROUND    6   /* a round starts (obj = the round number, mod 256) */
#define POLARI_MARK_BACKOFF  7   /* the back-off technique gave its first lock back */
#define POLARI_MARK_DONE     8   /* a round's work completed */
void polari_trace_task(TaskHandle_t h, uint8_t id, const char *name);
void polari_trace_lock(void *h, uint8_t id, const char *name, const char *kind);
void polari_trace_start(void);
void polari_trace_stop(void);
void polari_mark(uint8_t code, uint8_t obj);
void polari_trace_dump(void);

#endif /* POLARI_C3_H */
