/* polari_mthread.h — the BRIDGE from the UNO's critical-section idiom to Frama-C/Mthread's thread + mutex convention (sc-2c,
 * FIRMWARE_SCENARIO_PLAN.md §5 tier 2; D-sc-6 ruled 2026-10-02; AI-Notes/evaluations/FRAMA_C_EVALUATION.md §2c, §6). Included by
 * mt_stubs/avr/interrupt.h + mt_stubs/util/atomic.h (which hal.c includes) and by the harnesses. The firmware is NOT edited:
 * the harness #includes the variant's own hal.c, preprocessed with -DPOLARI_MTHREAD, so HAL_MILLIS_ATOMIC (from the variant's
 * board_config.h) decides which hal_millis Mthread sees — no hand copy.
 *
 * The builtins are Frama-C 33.0's own (share/frama-c/share/mt/mthread.h, LGPL-2.1, CEA), #included below: a thread made by
 * Frama_C_thread_create starts SUSPENDED until Frama_C_thread_start (the shipped test late_start.c) — the harnesses do both.
 *
 * ASSUMPTIONS BEGIN
 * A1 The interrupt lock: ONE global Mthread mutex, polari_irq_mutex, models SREG.I. cli() acquires it, sei() releases it,
 *    ATOMIC_BLOCK holds it for its body. "Holding the lock" = "interrupts are masked".
 * A2 An ISR = a thread created with Frama_C_thread_create whose body runs the REAL ISR function (hal.c's, unedited)
 *    repeatedly, each run holding the interrupt lock — the AVR core clears I on entry and reti sets it again, so no other
 *    interrupt and no masked section of the main loop can interleave with an ISR body.
 * A3 The main loop = the analysis' <main> thread, running with interrupts ENABLED (the lock free) between masked sections;
 *    ATOMIC_RESTORESTATE is therefore modelled as release-on-exit. Nested ISRs (an ISR that re-enables I) and nested masking
 *    (an ATOMIC_BLOCK entered with I already clear, a cli() inside an ISR) are EXCLUDED — the firmware has neither.
 * A4 Mthread's definition of a data race: two accesses to the same memory location from two different threads, at least
 *    one a write, that do not both hold a common mutex. Mthread lists every such variable with each access (thread, source
 *    line, mutexes held). Its threads run truly concurrently, which over-approximates the AVR's single core (an ISR
 *    pre-empts the main loop, never the reverse): sound, possibly coarse.
 * A5 The byte rule (the framework's classify, not Mthread's): an access the lock does NOT protect is still safe when the
 *    object (an array: its element) is ONE byte — one lds/sts, which no interrupt can split — and only ONE thread ever
 *    writes it. Sizes come from the harness (sizeof, printed by Eva), never typed by hand.
 * A6 Machdep avr_16 — Frama-C's own AVR model (int 16 bits, long 32, pointers 16, little endian: avr-gcc's defaults).
 *    Registers are bytes of POLARI_IO (the CBMC stubs' avr/io.h); a register the ISR alone touches is not shared and is
 *    never reported. Mthread decides at the C level: the byte-wise lds sequence is the simulation tier's (and CBMC's model).
 * ASSUMPTIONS END
 */
#ifndef POLARI_MTHREAD_H
#define POLARI_MTHREAD_H
#ifndef POLARI_MTHREAD
#error "polari_mthread.h is the Mthread bridge: preprocess with -DPOLARI_MTHREAD"
#endif

/* Frama-C's own builtins (Frama_C_thread_create/_start, Frama_C_mutex_init/_lock/_unlock), from FRAMAC_SHARE/mt — the worker
 * adds that directory to the include path (polari-mthread-check) */
#include <mthread.h>

/* A1: the interrupt lock. polari_irq is its Mthread id; polari_irq_mutex names it in Mthread's report. */
extern __fc_mthread_id polari_irq;
extern int polari_irq_mutex;
#define polari_irq_lock() ((void)Frama_C_mutex_lock(polari_irq))
#define polari_irq_unlock() ((void)Frama_C_mutex_unlock(polari_irq))
#define POLARI_IRQ_INIT() (polari_irq = Frama_C_mutex_init(&polari_irq_mutex))
/* A2: one ISR thread's body — the real ISR, run under the lock, as often as an interrupt may fire */
#define POLARI_SPAWN(name, thread_fn) ((void)Frama_C_thread_start(Frama_C_thread_create(&(name), thread_fn, 0)))
#define POLARI_ISR_THREAD(thread_fn, isr) \
    void *thread_fn(void *polari_arg) { (void)polari_arg; while (polari_irq_pending) { polari_irq_lock(); isr(); polari_irq_unlock(); } return 0; }
extern volatile int polari_irq_pending;     /* volatile: Eva reads it as any value — "an interrupt may (not) fire now" */
extern volatile int polari_main_runs;       /* the main loop's condition, same reading */
#endif
