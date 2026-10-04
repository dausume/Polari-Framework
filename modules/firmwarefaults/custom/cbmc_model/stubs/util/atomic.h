/* util/atomic.h — the formal tier's stand-in (sc-2b) for avr-libc's ATOMIC_BLOCK(ATOMIC_RESTORESTATE): save SREG.I and
 * clear it on entry, restore the saved value on exit — the same semantics (avr-libc util/atomic.h: cli + a cleanup that
 * writes SREG back), so the harness's interrupt model sees interrupts masked exactly across the block's body. */
#ifndef POLARI_FORMAL_UTIL_ATOMIC_H
#define POLARI_FORMAL_UTIL_ATOMIC_H
#include <stdint.h>
extern uint8_t polari_sreg_i;
static inline uint8_t polari_atomic_enter(void)
{
    uint8_t s = polari_sreg_i;
    polari_sreg_i = 0u;
    return s;
}
#define ATOMIC_RESTORESTATE
#define ATOMIC_FORCEON
#define ATOMIC_BLOCK(type) for (uint8_t polari_saved = polari_atomic_enter(), polari_once = 1u; polari_once; polari_once = 0u, polari_sreg_i = polari_saved)
#endif
