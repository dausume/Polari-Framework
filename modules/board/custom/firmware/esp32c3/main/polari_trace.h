/*
 * polari_trace.h — the FreeRTOS trace hooks of the C3 template (sc-3, FIRMWARE_SCENARIO_PLAN.md §2d: "FreeRTOS trace hook
 * macros → our wait-for-graph events"). PLAIN C (RULE 2).
 *
 * The project's top CMakeLists.txt force-includes this header into EVERY C translation unit of the build (ESP-IDF's
 * FreeRTOS kernel included), so the kernel's own `#ifndef traceX / #define traceX()` defaults never apply: each hook
 * below calls polari_trace_hook() at the exact point the kernel switches a task in, blocks a task on a semaphore, hands
 * a semaphore over, or raises/drops a priority by inheritance. The macro NAMES and ARGUMENTS are FreeRTOS-Kernel's
 * (include/FreeRTOS.h, MIT); nothing in the kernel is edited.
 *
 * It must stay includable before anything else: no FreeRTOS header, no ESP-IDF header, nothing for the assembler.
 */
#ifndef POLARI_TRACE_H
#define POLARI_TRACE_H

#ifndef __ASSEMBLER__

/* event kinds — the host side (firmwarefaults.custom.c3_trace) reads the same numbers */
#define POLARI_EV_SWITCH_IN   1   /* a task was switched in (task = the new one) */
#define POLARI_EV_TAKE        2   /* a task took a registered lock (semaphore receive succeeded) */
#define POLARI_EV_BLOCK       3   /* a task is about to block on a registered lock */
#define POLARI_EV_GIVE        4   /* a task gave a registered lock */
#define POLARI_EV_INHERIT     5   /* the holder's priority raised by inheritance (arg = the new priority) */
#define POLARI_EV_DISINHERIT  6   /* the holder's priority dropped back (arg = the priority it returns to) */
#define POLARI_EV_MARK        7   /* an application marker (arg = POLARI_MARK_*) */
#define POLARI_EV_TIMEOUT     8   /* a timed take expired (the try-lock of the back-off technique) */

void polari_trace_hook(unsigned kind, void *obj, unsigned arg);

#define traceTASK_SWITCHED_IN()                    polari_trace_hook(POLARI_EV_SWITCH_IN, (void *)0, 0u)
#define traceBLOCKING_ON_QUEUE_RECEIVE(pxQueue)    polari_trace_hook(POLARI_EV_BLOCK, (void *)(pxQueue), 0u)
#define traceQUEUE_RECEIVE(pxQueue)                polari_trace_hook(POLARI_EV_TAKE, (void *)(pxQueue), 0u)
/* a semaphore/mutex take succeeds through xQueueSemaphoreTake, which reports it with this macro — not traceQUEUE_RECEIVE
 * (ESP-IDF v5.5.5 components/freertos/FreeRTOS-Kernel/queue.c line 1738; found because the first runs had no TAKE events) */
#define traceQUEUE_SEMAPHORE_RECEIVE(pxQueue)      polari_trace_hook(POLARI_EV_TAKE, (void *)(pxQueue), 0u)
#define traceQUEUE_RECEIVE_FAILED(pxQueue)         polari_trace_hook(POLARI_EV_TIMEOUT, (void *)(pxQueue), 0u)
#define traceQUEUE_SEND(pxQueue)                   polari_trace_hook(POLARI_EV_GIVE, (void *)(pxQueue), 0u)
#define traceTASK_PRIORITY_INHERIT(pxTCB, uxPrio)  polari_trace_hook(POLARI_EV_INHERIT, (void *)(pxTCB), (unsigned)(uxPrio))
#define traceTASK_PRIORITY_DISINHERIT(pxTCB, uxPrio) polari_trace_hook(POLARI_EV_DISINHERIT, (void *)(pxTCB), (unsigned)(uxPrio))

#endif /* __ASSEMBLER__ */
#endif /* POLARI_TRACE_H */
