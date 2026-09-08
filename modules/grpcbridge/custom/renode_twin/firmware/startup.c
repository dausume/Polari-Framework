/* Minimal Cortex-M4 startup for the hwsim-1 Renode twin: vector
 * table (SP + Reset only — the firmware is pure polling, no
 * interrupts) + .data copy + .bss zero. */

#include <stdint.h>

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;

int main(void);

void Reset_Handler(void)
{
    uint32_t *src = &_sidata, *dst = &_sdata;
    while (dst < &_edata) *dst++ = *src++;
    for (dst = &_sbss; dst < &_ebss; ) *dst++ = 0u;
    main();
    for (;;) { }
}

__attribute__((section(".isr_vector"), used))
static void (* const vector_table[])(void) = {
    (void (*)(void))(&_estack),
    Reset_Handler,
};
