/*
 * variant app `two_lock` (sc-3, FIRMWARE_SCENARIO_PLAN.md §3a scenario 7) — two FreeRTOS tasks, two mutexes A and B, on
 * the ESP32-C3. PLAIN C on ESP-IDF's FreeRTOS (RULE 2). `pol board gen c3 --variant c3-two-lock[-ordered|-backoff]`
 * copies this file into the project as main/app.c.
 *
 *   T1 (priority 3): take A · vTaskDelay(t1_gap) — the forced yield point · take B · work · give B · give A
 *   T2 (priority 3), starting t2_start ticks after T1:
 *       SC_LOCK_ORDER 0 (BEFORE, c3-two-lock):          take B · vTaskDelay(t2_gap) · take A — the OPPOSITE order
 *       SC_LOCK_ORDER 1 (AFTER,  c3-two-lock-ordered):  take A · vTaskDelay(t2_gap) · take B — one global order
 *   SC_LOCK_TIMEOUT_MS N > 0 (c3-two-lock-backoff): the opposite order kept, but each task's SECOND take waits at most
 *       N ms; on a timeout it gives its first lock back, backs off (T1 1 tick, T2 3 ticks — unequal, so the two never
 *       retry in lock-step) and starts again.
 *
 * With the opposite order and t2_start < t1_gap, T1 holds A and asks for B while T2 holds B and asks for A: both wait for
 * ever (the wait-for graph T1 → B → T2 → A → T1). The telemetry task snapshots its counters UNDER A, so telemetry
 * stops too — the observable a host sees. The monitor (priority 6) declares a deadlock when neither task completed a
 * round for `stall_ms` and both are Blocked: `@DEADLOCK …` with the holder/waiter table, then the window runs out.
 *
 * Slots (polari_c3.h params): a[0] t1_gap ticks · a[1] t2_start ticks (the host-steerable slot) · a[2] t2_gap ticks ·
 *   a[3] hold_us (the work under both locks) · a[4] round period ticks · a[5] stall_ms
 * Telemetry: temp_c = rounds completed by T1 + T2, pwm_duty = t2_start, status ok (fault after a declared deadlock — but
 * the telemetry task is itself stuck on A by then, so the host sees the silence, not the word).
 */
#include <string.h>

#include "polari_c3.h"

#ifndef SC_LOCK_ORDER
#define SC_LOCK_ORDER 0
#endif
#ifndef SC_LOCK_TIMEOUT_MS
#define SC_LOCK_TIMEOUT_MS 0
#endif
#ifndef SC_ROUNDS
#define SC_ROUNDS 10
#endif
#define PRIO_T 3
#define PRIO_TEL 5
#define PRIO_MON 6
#define LEAD_TICKS 350          /* the first round starts after three telemetry frames, so a deadlock visibly STOPS telemetry */
#define TECHNIQUE (SC_LOCK_ORDER ? "lock-ordering" : SC_LOCK_TIMEOUT_MS ? "timeout-backoff" : "none")

static const int32_t DEFAULTS[8] = {2, 1, 1, 500, 50, 300, 0, 0};
static SemaphoreHandle_t A, B;
static TickType_t s_t0;
static TaskHandle_t s_t1, s_t2;
static volatile uint32_t s_prog[2], s_backoffs[2];
static volatile int s_holder[2] = {-1, -1};   /* lock (A = 0, B = 1) → task (0 = T1, 1 = T2), -1 = free */
static volatile int s_waiting[2] = {-1, -1};  /* task → the lock it is asking for, -1 = none */

static void wait_until(TickType_t when)
{
    TickType_t now = xTaskGetTickCount();
    if ((int32_t)(when - now) > 0) vTaskDelay(when - now);
}

static int take(int me, int lock, TickType_t timeout)
{
    SemaphoreHandle_t s = lock ? B : A;
    int ok;
    s_waiting[me] = lock;
    polari_mark(POLARI_MARK_REQ, (uint8_t)lock);
    ok = xSemaphoreTake(s, timeout) == pdTRUE;
    s_waiting[me] = -1;
    if (ok) {
        s_holder[lock] = me;
        polari_mark(POLARI_MARK_ACQ, (uint8_t)lock);
    }
    return ok;
}

static void give(int lock)
{
    s_holder[lock] = -1;
    polari_mark(POLARI_MARK_REL, (uint8_t)lock);
    xSemaphoreGive(lock ? B : A);
}

/* one round: first lock, the forced gap, second lock (with the technique's timeout), work, release */
static void round_of(int me, int first, int second, TickType_t gap, TickType_t backoff)
{
    for (;;) {
        take(me, first, portMAX_DELAY);
        if (gap) vTaskDelay(gap);
        if (take(me, second, SC_LOCK_TIMEOUT_MS ? pdMS_TO_TICKS(SC_LOCK_TIMEOUT_MS) : portMAX_DELAY)) break;
        polari_mark(POLARI_MARK_BACKOFF, (uint8_t)first);   /* the try-lock lost: give the first back, wait, retry */
        s_backoffs[me]++;
        give(first);
        vTaskDelay(backoff);
    }
    polari_work_us((uint32_t)g_params.a[3]);
    give(second);
    give(first);
    s_prog[me]++;
    polari_mark(POLARI_MARK_DONE, (uint8_t)me);
}

static void task_t1(void *arg)
{
    (void)arg;
    for (uint32_t r = 0; r < g_params.rounds; r++) {
        wait_until(s_t0 + (TickType_t)(r * (uint32_t)g_params.a[4]));
        polari_mark(POLARI_MARK_ROUND, (uint8_t)r);
        round_of(0, 0, 1, (TickType_t)g_params.a[0], 1);
        g_tel.value = (double)(s_prog[0] + s_prog[1]);
    }
    vTaskSuspend(NULL);
}

static void task_t2(void *arg)
{
    (void)arg;
    for (uint32_t r = 0; r < g_params.rounds; r++) {
        wait_until(s_t0 + (TickType_t)(r * (uint32_t)g_params.a[4] + (uint32_t)g_params.a[1]));
        round_of(1, SC_LOCK_ORDER ? 0 : 1, SC_LOCK_ORDER ? 1 : 0, (TickType_t)g_params.a[2], 3);
        g_tel.value = (double)(s_prog[0] + s_prog[1]);
    }
    vTaskSuspend(NULL);
}

static const char *state_name(TaskHandle_t t)
{
    switch (eTaskGetState(t)) {
    case eRunning: return "Running";
    case eReady: return "Ready";
    case eBlocked: return "Blocked";
    case eSuspended: return "Suspended";
    default: return "Deleted";
    }
}

static void task_mon(void *arg)
{
    TickType_t end, last_change;
    uint32_t p0 = 0, p1 = 0, deadlock_us = 0;
    TickType_t deadlock_tick = 0;
    int deadlock = 0;
    (void)arg;
    end = s_t0 + pdMS_TO_TICKS(g_params.window_ms);
    last_change = xTaskGetTickCount();
    while ((int32_t)(end - xTaskGetTickCount()) > 0) {
        vTaskDelay(pdMS_TO_TICKS(10));
        if (s_prog[0] >= g_params.rounds && s_prog[1] >= g_params.rounds) break;
        if (s_prog[0] != p0 || s_prog[1] != p1) { p0 = s_prog[0]; p1 = s_prog[1]; last_change = xTaskGetTickCount(); continue; }
        if (!deadlock && (int32_t)(xTaskGetTickCount() - last_change) >= (int32_t)pdMS_TO_TICKS(g_params.a[5])
            && eTaskGetState(s_t1) == eBlocked && eTaskGetState(s_t2) == eBlocked
            && s_waiting[0] >= 0 && s_waiting[1] >= 0) {
            deadlock = 1;
            deadlock_us = polari_now_us();
            deadlock_tick = xTaskGetTickCount();
            g_tel.status = 5;   /* SIMRIGSTATE_STATUS_FAULT — the telemetry task is stuck on A, so it never says it */
        }
    }
    polari_window_end();
    if (deadlock)
        polari_line("@DEADLOCK detected_us=%lu detected_tick=%lu T1=%s T1_waits=%s A_held_by=%s T2=%s T2_waits=%s B_held_by=%s rounds=%lu,%lu",
                    (unsigned long)deadlock_us, (unsigned long)deadlock_tick, state_name(s_t1),
                    s_waiting[0] == 0 ? "A" : s_waiting[0] == 1 ? "B" : "-", s_holder[0] == 0 ? "T1" : s_holder[0] == 1 ? "T2" : "-",
                    state_name(s_t2), s_waiting[1] == 0 ? "A" : s_waiting[1] == 1 ? "B" : "-",
                    s_holder[1] == 0 ? "T1" : s_holder[1] == 1 ? "T2" : "-", (unsigned long)s_prog[0], (unsigned long)s_prog[1]);
    polari_line("@LOCKS technique=%s order=%s timeout_ms=%d rounds=%lu,%lu of=%lu backoffs=%lu,%lu deadlock=%d t1_gap=%ld "
                "t2_start=%ld t2_gap=%ld params=%s", TECHNIQUE, SC_LOCK_ORDER ? "A-then-B" : "T1:A-then-B,T2:B-then-A", SC_LOCK_TIMEOUT_MS,
                (unsigned long)s_prog[0], (unsigned long)s_prog[1], (unsigned long)g_params.rounds, (unsigned long)s_backoffs[0],
                (unsigned long)s_backoffs[1], deadlock, (long)g_params.a[0], (long)g_params.a[1], (long)g_params.a[2],
                g_params_source == 1 ? "flash" : g_params_source == 2 ? "host" : "defaults");
    polari_trace_dump();
    polari_line("@END t_us=%lu", (unsigned long)polari_now_us());
    for (;;) vTaskDelay(portMAX_DELAY);
}

void polari_app_main(void)
{
    TaskHandle_t h;
    polari_c3_init(DEFAULTS, 1500u, SC_ROUNDS);
    g_steer_slot = 1;
    g_tel.steer = g_params.a[1];
    A = xSemaphoreCreateMutex();
    B = xSemaphoreCreateMutex();
    polari_trace_lock((void *)A, 0, "A", "mutex");
    polari_trace_lock((void *)B, 1, "B", "mutex");
    polari_telemetry_start(A, PRIO_TEL);    /* the snapshot is taken under A */
    polari_rx_start(PRIO_TEL);
    s_t0 = xTaskGetTickCount() + LEAD_TICKS;
    polari_trace_start();
    xTaskCreate(task_t1, "T1", 3072, NULL, PRIO_T, &s_t1); polari_trace_task(s_t1, 4, "T1");
    xTaskCreate(task_t2, "T2", 3072, NULL, PRIO_T, &s_t2); polari_trace_task(s_t2, 5, "T2");
    xTaskCreate(task_mon, "MON", 4096, NULL, PRIO_MON, &h); polari_trace_task(h, 8, "MON");
    polari_trace_task(xTaskGetIdleTaskHandle(), 11, "IDLE");
    g_tel.status = 2;
}
