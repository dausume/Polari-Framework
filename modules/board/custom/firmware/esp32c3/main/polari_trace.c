/*
 * polari_trace.c — the trace ring the FreeRTOS hooks (polari_trace.h) write into, and its dump as `@EV` lines on UART1.
 * PLAIN C (RULE 2).
 *
 * The hooks run inside the kernel (the context switch, the semaphore take/give paths, already inside a critical section
 * on this single-core part), so the hook only stores 8 bytes into a static ring — no printing, no allocation, no lock.
 * Only REGISTERED tasks and locks are named; any other queue (the UART driver's, the timer task's) is ignored, any other
 * task is recorded as id 0 ("other") when it is switched in. The dump happens after the scenario window, with recording
 * stopped, so printing never perturbs what was recorded.
 */
#include <string.h>

#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "polari_c3.h"

typedef struct {
    uint32_t t_us;
    uint8_t kind, task, obj, arg;
} ev_t;

#define MAX_TASKS 12
#define MAX_LOCKS 6

static ev_t s_ring[POLARI_TRACE_EVENTS];
static volatile uint32_t s_n, s_dropped;
static volatile int s_on;
static uint8_t s_last_task = 0xFFu;
static struct { void *h; uint8_t id; char name[12]; } s_tasks[MAX_TASKS];
static struct { void *h; uint8_t id; char name[12]; char kind[24]; } s_locks[MAX_LOCKS];
static int s_ntasks, s_nlocks;
static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;

void polari_trace_task(TaskHandle_t h, uint8_t id, const char *name)
{
    if (s_ntasks >= MAX_TASKS || !h) return;
    s_tasks[s_ntasks].h = (void *)h;
    s_tasks[s_ntasks].id = id;
    strncpy(s_tasks[s_ntasks].name, name, sizeof s_tasks[0].name - 1);
    s_ntasks++;
}

void polari_trace_lock(void *h, uint8_t id, const char *name, const char *kind)
{
    if (s_nlocks >= MAX_LOCKS || !h) return;
    s_locks[s_nlocks].h = h;
    s_locks[s_nlocks].id = id;
    strncpy(s_locks[s_nlocks].name, name, sizeof s_locks[0].name - 1);
    strncpy(s_locks[s_nlocks].kind, kind, sizeof s_locks[0].kind - 1);
    s_nlocks++;
}

static uint8_t task_id(void *h)
{
    for (int i = 0; i < s_ntasks; i++)
        if (s_tasks[i].h == h) return s_tasks[i].id;
    return 0u;
}

static int lock_id(void *h)
{
    for (int i = 0; i < s_nlocks; i++)
        if (s_locks[i].h == h) return s_locks[i].id;
    return -1;
}

static void put(uint8_t kind, uint8_t task, uint8_t obj, uint8_t arg)
{
    uint32_t i = s_n;
    if (i >= POLARI_TRACE_EVENTS) { s_dropped++; return; }
    s_ring[i].t_us = (uint32_t)esp_timer_get_time();
    s_ring[i].kind = kind;
    s_ring[i].task = task;
    s_ring[i].obj = obj;
    s_ring[i].arg = arg;
    s_n = i + 1u;
}

void polari_trace_hook(unsigned kind, void *obj, unsigned arg)
{
    if (!s_on) return;
    if (kind == POLARI_EV_SWITCH_IN) {
        uint8_t t = task_id((void *)xTaskGetCurrentTaskHandle());
        if (t != s_last_task) { s_last_task = t; put((uint8_t)kind, t, 0u, 0u); }
        return;
    }
    if (kind == POLARI_EV_INHERIT || kind == POLARI_EV_DISINHERIT) {
        put((uint8_t)kind, task_id(obj), 0u, (uint8_t)arg);
        return;
    }
    int l = lock_id(obj);
    if (l < 0) return;
    put((uint8_t)kind, task_id((void *)xTaskGetCurrentTaskHandle()), (uint8_t)l, (uint8_t)arg);
}

void polari_mark(uint8_t code, uint8_t obj)
{
    if (!s_on) return;
    taskENTER_CRITICAL(&s_mux);
    put(POLARI_EV_MARK, task_id((void *)xTaskGetCurrentTaskHandle()), obj, code);
    taskEXIT_CRITICAL(&s_mux);
}

void polari_trace_start(void)
{
    s_n = 0u;
    s_dropped = 0u;
    s_last_task = 0xFFu;
    s_on = 1;
}

void polari_trace_stop(void)
{
    s_on = 0;
}

void polari_trace_dump(void)
{
    s_on = 0;
    polari_line("@TRACE events=%lu dropped=%lu cap=%d clock=esp_timer_us", (unsigned long)s_n, (unsigned long)s_dropped, POLARI_TRACE_EVENTS);
    for (int i = 0; i < s_ntasks; i++)
        polari_line("@TASK %u %s prio=%u", s_tasks[i].id, s_tasks[i].name, (unsigned)uxTaskPriorityGet((TaskHandle_t)s_tasks[i].h));
    for (int i = 0; i < s_nlocks; i++)
        polari_line("@LOCK %u %s %s", s_locks[i].id, s_locks[i].name, s_locks[i].kind);
    for (uint32_t i = 0; i < s_n; i++)
        polari_line("@EV %lu %u %u %u %u", (unsigned long)s_ring[i].t_us, s_ring[i].kind, s_ring[i].task, s_ring[i].obj, s_ring[i].arg);
}
