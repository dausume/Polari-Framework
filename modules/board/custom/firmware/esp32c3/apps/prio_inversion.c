/*
 * variant app `prio_inversion` (sc-3, FIRMWARE_SCENARIO_PLAN.md §3a scenario 6) — three FreeRTOS tasks on the ESP32-C3
 * share ONE resource R. PLAIN C on ESP-IDF's FreeRTOS (RULE 2). `pol board gen c3 --variant c3-prio-inversion[-mutex]`
 * copies this file into the project as main/app.c.
 *
 *   L (priority 2) takes R at the round start and holds it for `l_cs_us` of ITS OWN CPU time (the critical section)
 *   H (priority 4) wakes `h_off` ticks later and asks for R            → blocks behind L
 *   M (priority 3) wakes `m_off` ticks later and runs `m_busy_us` of CPU, touching nothing shared
 *
 *   SC_PI_MUTEX 0 (BEFORE, c3-prio-inversion):        R is a BINARY SEMAPHORE — the kernel does not know who holds it, so
 *                 nothing raises L: M (3) preempts L (2) and H (4) waits for M's whole run → H's blocking ≫ L's section.
 *   SC_PI_MUTEX 1 (AFTER, c3-prio-inversion-mutex):   R is a FreeRTOS MUTEX — priority inheritance raises L to H's 4 while
 *                 H waits, M cannot preempt it, H waits at most the rest of L's section (the bound).
 *
 * The forcing (step `hold-lock-order`): the offsets are ticks after a common round start (vTaskDelay to an absolute
 * tick), so the interleaving is the recipe's, not chance. Slots of the params partition (polari_c3.h), defaults below:
 *   a[0] h_off ticks · a[1] m_off ticks (the host-steerable slot: a SimRigState command's pwm_duty) · a[2] l_cs_us ·
 *   a[3] m_busy_us · a[4] round period ticks · a[5] H's deadline µs
 * Telemetry: temp_c = H's worst blocking so far in ms (no sensor on this rig), pwm_duty = m_off, status ok.
 * The decision lines (UART1): one `@ROUND r h_req_us h_acq_us block_us` per round, then
 *   `@PI kind=<binary-semaphore|mutex> rounds=N worst_us=… bound_us=… deadline_us=… misses=…`, the trace dump, `@END`.
 * Nothing prints while the rounds run (printing takes a mutex — it would itself inherit).
 */
#include <string.h>

#include "polari_c3.h"

#ifndef SC_PI_MUTEX
#define SC_PI_MUTEX 0
#endif
#ifndef SC_ROUNDS
#define SC_ROUNDS 10
#endif
#define POLARI_APP_KIND (SC_PI_MUTEX ? "mutex" : "binary-semaphore")
#define PRIO_L 2
#define PRIO_M 3
#define PRIO_H 4
#define PRIO_TEL 5
#define PRIO_MON 6
#define LEAD_TICKS 50            /* the first round starts 50 ticks after the tasks exist (boot settles) */
#define MAX_ROUNDS 64

static const int32_t DEFAULTS[8] = {1, 2, 3000, 10000, 40, 5000, 0, 0};
static SemaphoreHandle_t R;
static TickType_t s_t0;
static volatile uint32_t s_done, s_worst, s_misses;
static uint32_t s_req[MAX_ROUNDS], s_acq[MAX_ROUNDS];

static void wait_until(TickType_t when)
{
    TickType_t now = xTaskGetTickCount();
    if ((int32_t)(when - now) > 0) vTaskDelay(when - now);
}

static TickType_t start_of(uint32_t r)
{
    return s_t0 + (TickType_t)(r * (uint32_t)g_params.a[4]);
}

static void task_l(void *arg)
{
    (void)arg;
    for (uint32_t r = 0; r < g_params.rounds; r++) {
        wait_until(start_of(r));
        polari_mark(POLARI_MARK_ROUND, (uint8_t)r);
        polari_mark(POLARI_MARK_REQ, 0);
        xSemaphoreTake(R, portMAX_DELAY);
        polari_mark(POLARI_MARK_ACQ, 0);
        polari_work_us((uint32_t)g_params.a[2]);
        polari_mark(POLARI_MARK_REL, 0);
        xSemaphoreGive(R);
    }
    vTaskSuspend(NULL);
}

static void task_h(void *arg)
{
    (void)arg;
    for (uint32_t r = 0; r < g_params.rounds; r++) {
        uint32_t t_req, t_acq, b;
        wait_until(start_of(r) + (TickType_t)g_params.a[0]);
        polari_mark(POLARI_MARK_REQ, 0);
        t_req = polari_now_us();
        xSemaphoreTake(R, portMAX_DELAY);
        t_acq = polari_now_us();
        polari_mark(POLARI_MARK_ACQ, 0);
        b = t_acq - t_req;
        s_req[r] = t_req;
        s_acq[r] = t_acq;
        if (b > s_worst) s_worst = b;
        if (b > (uint32_t)g_params.a[5]) s_misses++;
        g_tel.value = (double)s_worst / 1000.0;
        polari_work_us(100u);
        polari_mark(POLARI_MARK_REL, 0);
        xSemaphoreGive(R);
        s_done = r + 1u;
    }
    vTaskSuspend(NULL);
}

static void task_m(void *arg)
{
    (void)arg;
    for (uint32_t r = 0; r < g_params.rounds; r++) {
        wait_until(start_of(r) + (TickType_t)g_params.a[1]);
        polari_mark(POLARI_MARK_BUSY0, 0);
        polari_work_us((uint32_t)g_params.a[3]);
        polari_mark(POLARI_MARK_BUSY1, 0);
    }
    vTaskSuspend(NULL);
}

static void task_mon(void *arg)
{
    TickType_t end;
    (void)arg;
    end = s_t0 + pdMS_TO_TICKS(g_params.window_ms);
    while (s_done < g_params.rounds && (int32_t)(end - xTaskGetTickCount()) > 0) vTaskDelay(pdMS_TO_TICKS(10));
    polari_window_end();
    for (uint32_t r = 0; r < s_done; r++)
        polari_line("@ROUND %lu %lu %lu %lu", (unsigned long)r, (unsigned long)s_req[r], (unsigned long)s_acq[r],
                    (unsigned long)(s_acq[r] - s_req[r]));
    polari_line("@PI kind=%s rounds=%lu of=%lu worst_us=%lu bound_us=%ld deadline_us=%ld misses=%lu h_off=%ld m_off=%ld "
                "m_busy_us=%ld params=%s", POLARI_APP_KIND, (unsigned long)s_done, (unsigned long)g_params.rounds,
                (unsigned long)s_worst, (long)g_params.a[2], (long)g_params.a[5], (unsigned long)s_misses, (long)g_params.a[0],
                (long)g_params.a[1], (long)g_params.a[3], g_params_source == 1 ? "flash" : g_params_source == 2 ? "host" : "defaults");
    polari_trace_dump();
    polari_line("@END t_us=%lu", (unsigned long)polari_now_us());
    for (;;) vTaskDelay(portMAX_DELAY);
}

void polari_app_main(void)
{
    TaskHandle_t h;
    polari_c3_init(DEFAULTS, 1000u, SC_ROUNDS);
    if (g_params.rounds > MAX_ROUNDS) g_params.rounds = MAX_ROUNDS;
    g_steer_slot = 1;
    g_tel.steer = g_params.a[1];
#if SC_PI_MUTEX
    R = xSemaphoreCreateMutex();
#else
    R = xSemaphoreCreateBinary();
    xSemaphoreGive(R);
#endif
    polari_trace_lock((void *)R, 0, "R", POLARI_APP_KIND);
    polari_telemetry_start(NULL, PRIO_TEL);
    polari_rx_start(PRIO_TEL);
    s_t0 = xTaskGetTickCount() + LEAD_TICKS;
    polari_trace_start();
    xTaskCreate(task_l, "L", 3072, NULL, PRIO_L, &h); polari_trace_task(h, 1, "L");
    xTaskCreate(task_m, "M", 3072, NULL, PRIO_M, &h); polari_trace_task(h, 2, "M");
    xTaskCreate(task_h, "H", 3072, NULL, PRIO_H, &h); polari_trace_task(h, 3, "H");
    xTaskCreate(task_mon, "MON", 4096, NULL, PRIO_MON, &h); polari_trace_task(h, 8, "MON");
    polari_trace_task(xTaskGetIdleTaskHandle(), 11, "IDLE");
    g_tel.status = 2;   /* SIMRIGSTATE_STATUS_OK */
}
