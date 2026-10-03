/* stdint.h — the formal tier's stand-in (sc-2b): exact-width types for CBMC run with --16 (LP32: char 8, short 16,
 * int 16, long 32, long long 64 bits) — the integer widths avr-gcc uses, so integer promotion matches the AVR. The host's
 * <stdint.h> would typedef uint32_t as `unsigned int`, which --16 makes 16 bits wide: hence this file. */
#ifndef POLARI_FORMAL_STDINT_H
#define POLARI_FORMAL_STDINT_H
typedef signed char int8_t;
typedef unsigned char uint8_t;
typedef short int16_t;
typedef unsigned short uint16_t;
typedef long int32_t;
typedef unsigned long uint32_t;
typedef long long int64_t;
typedef unsigned long long uint64_t;
#define UINT8_MAX 0xFFu
#define UINT16_MAX 0xFFFFu
#define UINT32_MAX 0xFFFFFFFFul
#endif
