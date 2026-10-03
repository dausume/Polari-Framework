/* util/atomic.h — the Mthread BRIDGE's stand-in (sc-2c) for avr-libc's ATOMIC_BLOCK: the block's body runs holding THE interrupt
 * lock (acquired on entry, released on exit) — avr-libc's `cli` + the cleanup that writes SREG back, seen by Mthread as a
 * mutex section. ATOMIC_RESTORESTATE and ATOMIC_FORCEON are the same here: the main loop runs with interrupts enabled, so
 * "restore" re-enables them (assumption A3 in ../../polari_mthread.h — a block entered with I already clear, i.e. nested
 * masking, is outside the model). Only under -DPOLARI_MTHREAD; it shadows the CBMC stub of the same name. */
#ifndef POLARI_MTHREAD_UTIL_ATOMIC_H
#define POLARI_MTHREAD_UTIL_ATOMIC_H
#ifndef POLARI_MTHREAD
#error "mthread_model/stubs is the Mthread bridge: preprocess with -DPOLARI_MTHREAD"
#endif
#include "polari_mthread.h"
#define ATOMIC_RESTORESTATE
#define ATOMIC_FORCEON
#define ATOMIC_BLOCK(type) for (int polari_once = (polari_irq_lock(), 1); polari_once; polari_once = 0, polari_irq_unlock())
#endif
