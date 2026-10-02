"""
@module grpcbridge.custom.c_twin

grpc-j3 (first sliver, pulled forward for hwsim-1): generate the
firmware-side C header `<class>_packets.h` from the SAME contract
field_map the .proto and the Java codec came from — firmware, Java,
and Polari agree on the wire by construction.

Layout is the byte-exact twin of the generated Java PolariPacket +
<Class>Codec: 12-byte little-endian header (magic 0x504C u16 |
version=1 u8 | msg_type u8 | device_id u16 | sequence u32 |
payload_len u16), payload fields in TAG order (int64/double LE 8B,
bool 1B, strings u16-length-prefixed UTF-8), CRC32 (IEEE reflected)
over header+payload appended LE. Strings land in fixed char[64]
buffers on the MCU (truncated + NUL-terminated on decode) — the
nanopb-style bound that keeps this embeddable on the SAMD21 tier.

brd-0 TARGET KNOB (`target=`, `?target=avr` on the header endpoint):
`host` (default) is byte-identical to the header before brd-0. `avr`
exists because avr-gcc's `double` is 4 bytes (binary32) while the wire
carries 8-byte binary64: there, `double` fields are converted IN
SOFTWARE (32-bit integer ops only — float32→binary64 bit assembly on
encode, binary64→float32 round-to-nearest-even on decode). The WIRE
format does not change; AVR is little-endian, so the rest of the layout
holds. A compile-time check refuses the AVR header where `double` is not
4 bytes (e.g. `-mdouble=64`, or a host without the test shim).

@consumers
  - grpcbridge.contract_api (GET /api/grpc/exposures/{class}/c-header)
  - grpcbridge/custom/renode_twin firmware (hwsim-1)
  - grpcbridge.c_twin_selftest
  - board (brd-1: the UNO firmware renders its header with target=avr)
  - grpc-j4: `wire=<spec>` delegates to c_twin_v2 (wire v2: instance
    index + presence prelude, enum tables, the resync parser)
"""

C_STR_MAX = 64
TARGETS = ('host', 'avr')

#: proto type -> (C type, fixed wire size; strings are variable)
C_TYPES = {
    'int64': ('int64_t', 8),
    'double': ('double', 8),
    'bool': ('uint8_t', 1),
    'string': (f'char[{C_STR_MAX}]', None),
    'bytes': (f'uint8_t[{C_STR_MAX}]', None),
}

#: Shared framing/CRC support, emitted once per translation unit
#: (guarded) so multi-class firmwares don't collide.
_COMMON = r'''#ifndef POLARI_PACKET_COMMON_H
#define POLARI_PACKET_COMMON_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>

#define POLARI_MAGIC      0x504CU  /* wire bytes: 0x4C 0x50 */
#define POLARI_VERSION    1U
#define POLARI_HEADER_LEN 12U

/* CRC32 (IEEE reflected, poly 0xEDB88320) — identical to
 * java.util.zip.CRC32 and Python zlib.crc32. Bitwise (no table):
 * cycles are cheap at telemetry rates, flash is not. */
static uint32_t polari_crc32(const uint8_t *d, size_t n)
{
    uint32_t c = 0xFFFFFFFFu;
    size_t i;
    int k;
    for (i = 0; i < n; i++) {
        c ^= d[i];
        for (k = 0; k < 8; k++)
            c = (c >> 1) ^ (0xEDB88320u
                            & (uint32_t)(-(int32_t)(c & 1u)));
    }
    return ~c;
}

static void polari_put_u16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
}

static void polari_put_u32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v;         p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}

static uint16_t polari_get_u16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static uint32_t polari_get_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8)
         | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* Frame a payload into `out` (must hold POLARI_HEADER_LEN+len+4).
 * Returns the wire length. */
static size_t polari_packet_encode(uint8_t *out, uint8_t msg_type,
                                   uint16_t device_id, uint32_t seq,
                                   const uint8_t *payload,
                                   uint16_t len)
{
    polari_put_u16(out, POLARI_MAGIC);
    out[2] = POLARI_VERSION;
    out[3] = msg_type;
    polari_put_u16(out + 4, device_id);
    polari_put_u32(out + 6, seq);
    polari_put_u16(out + 10, len);
    memcpy(out + POLARI_HEADER_LEN, payload, len);
    polari_put_u32(out + POLARI_HEADER_LEN + len,
                   polari_crc32(out, POLARI_HEADER_LEN + len));
    return POLARI_HEADER_LEN + (size_t)len + 4u;
}

/* Incremental receive parser: feed one byte at a time; returns 1
 * when rx holds a complete CRC-valid packet (msg_type/payload/len
 * fields populated), 0 otherwise. Resync-safe: bad magic, oversize
 * or bad CRC restart the hunt. */
typedef struct {
    uint8_t buf[POLARI_HEADER_LEN + POLARI_RX_PAYLOAD_MAX + 4u];
    size_t have;
    uint16_t need_payload;
    uint8_t msg_type;
    uint16_t device_id;
    uint32_t sequence;
    const uint8_t *payload;
    uint16_t payload_len;
} polari_rx_t;

static int polari_rx_feed(polari_rx_t *rx, uint8_t b)
{
    if (rx->have == 0u) {
        if (b != (uint8_t)(POLARI_MAGIC & 0xFFu)) return 0;
    } else if (rx->have == 1u) {
        if (b != (uint8_t)(POLARI_MAGIC >> 8)) { rx->have = 0u; return 0; }
    }
    rx->buf[rx->have++] = b;
    if (rx->have == POLARI_HEADER_LEN) {
        if (rx->buf[2] != POLARI_VERSION) { rx->have = 0u; return 0; }
        rx->need_payload = polari_get_u16(rx->buf + 10);
        if (rx->need_payload > POLARI_RX_PAYLOAD_MAX) {
            rx->have = 0u;
            return 0;
        }
    }
    if (rx->have >= POLARI_HEADER_LEN
        && rx->have == POLARI_HEADER_LEN + (size_t)rx->need_payload + 4u) {
        size_t body = POLARI_HEADER_LEN + (size_t)rx->need_payload;
        uint32_t crc = polari_get_u32(rx->buf + body);
        rx->have = 0u;
        if (crc != polari_crc32(rx->buf, body)) return 0;
        rx->msg_type = rx->buf[3];
        rx->device_id = polari_get_u16(rx->buf + 4);
        rx->sequence = polari_get_u32(rx->buf + 6);
        rx->payload = rx->buf + POLARI_HEADER_LEN;
        rx->payload_len = rx->need_payload;
        return 1;
    }
    return 0;
}

#endif /* POLARI_PACKET_COMMON_H */'''

#: target=avr only (and only when the class has a double field): the
#: software binary32 <-> binary64 conversion. 32-bit integer ops only —
#: no float arithmetic, no 64-bit shifts; `(uint32_t)1` because AVR's
#: int is 16 bits.
_AVR_DOUBLE = r'''#ifndef POLARI_AVR_DOUBLE_H
#define POLARI_AVR_DOUBLE_H

/* target=avr: avr-gcc's double is 4 bytes (binary32); the wire's double
 * is 8 (binary64). Converted here in software; the WIRE is unchanged. */
#ifdef POLARI_AVR_DOUBLE_TEST
typedef float polari_avr_double_t;   /* host-test shim: a 4-byte double */
#else
typedef double polari_avr_double_t;  /* avr-gcc default: double == float */
#endif
/* refuses to compile where double is not 4 bytes (-mdouble=64, a host) */
typedef char polari_avr_double_is_4_bytes[
    (sizeof(polari_avr_double_t) == 4u) ? 1 : -1];

/* binary32 -> binary64 bits; exact (every binary32 is a binary64). */
static void polari_f32_to_f64(polari_avr_double_t v, uint32_t *lo,
                              uint32_t *hi)
{
    uint32_t b, sign, man;
    int32_t exp;
    memcpy(&b, &v, 4);
    sign = b & 0x80000000UL;
    exp = (int32_t)((b >> 23) & 0xFFUL);
    man = b & 0x007FFFFFUL;
    if (exp == 0xFF) {                 /* inf / nan: payload kept */
        exp = 0x7FF;
    } else if (exp == 0) {
        if (man == 0UL) { *hi = sign; *lo = 0UL; return; }  /* +-0 */
        exp = 1 - 127;                 /* subnormal: normalise */
        while ((man & 0x00800000UL) == 0UL) { man <<= 1; exp--; }
        man &= 0x007FFFFFUL;
        exp += 1023;
    } else {
        exp += 1023 - 127;
    }
    *hi = sign | ((uint32_t)exp << 20) | (man >> 3);
    *lo = man << 29;
}

/* binary64 bits -> binary32: round to nearest, ties to even; overflow
 * -> inf, underflow -> subnormal or signed zero; nan stays quiet nan. */
static polari_avr_double_t polari_f64_to_f32(uint32_t lo, uint32_t hi)
{
    uint32_t sign = hi & 0x80000000UL, man, rest, out;
    int32_t exp = (int32_t)((hi >> 20) & 0x7FFUL);
    polari_avr_double_t v;
    man = ((hi & 0x000FFFFFUL) << 3) | (lo >> 29);  /* top 23 bits */
    rest = lo & 0x1FFFFFFFUL;                        /* the 29 below */
    if (exp == 0x7FF) {
        out = sign | 0x7F800000UL
            | ((man | rest) ? (0x00400000UL | man) : 0UL);
    } else if (exp == 0) {
        out = sign;                    /* binary64 subnormals: far below */
    } else {
        exp = exp - 1023 + 127;
        if (exp >= 0xFF) {
            out = sign | 0x7F800000UL;
        } else if (exp <= 0) {         /* a binary32 subnormal */
            uint32_t sig = man | 0x00800000UL;
            uint32_t shift = (uint32_t)(1 - exp), q, r, half;
            if (shift > 24UL) {
                out = sign;
            } else {
                q = sig >> shift;
                r = sig & (((uint32_t)1 << shift) - 1UL);
                half = (uint32_t)1 << (shift - 1UL);
                if (r > half || (r == half && (rest != 0UL || (q & 1UL))))
                    q++;               /* a carry to the smallest normal is correct */
                out = sign | q;
            }
        } else {
            out = sign | ((uint32_t)exp << 23) | man;
            if (rest > 0x10000000UL
                || (rest == 0x10000000UL && (man & 1UL)))
                out++;                 /* a carry into exp is correct; 0xFF = inf */
        }
    }
    memcpy(&v, &out, 4);
    return v;
}

#endif /* POLARI_AVR_DOUBLE_H */'''


def _c_fields(field_map):
    """Fields in tag order as (name, proto_type, comment)."""
    fields = field_map.get('fields', {})
    return [(n, fields[n]['proto_type'], fields[n].get('comment', ''))
            for n in sorted(fields, key=lambda n: int(fields[n]['tag']))]


def payload_max(field_map):
    """Worst-case payload size for the RX buffer bound."""
    total = 0
    for _, ptype, _ in _c_fields(field_map):
        fixed = C_TYPES[ptype][1]
        total += fixed if fixed is not None else 2 + C_STR_MAX
    return total


def render_c_header(class_name, field_map, msg_type, version=0,
                    contract_hash='', target='host', wire=None):
    """The complete `<class>_packets.h`: struct (tag order) + encode
    + decode, on top of the shared framing block. `target` = 'host'
    (default, unchanged) | 'avr' (software double conversion).
    `wire` (grpc-j4): a wire_contract.spec → the WIRE V2 header
    (prelude: instance index + presence; enums; resync parser) from
    c_twin_v2; None = the v1 header, byte-identical as before."""
    if target not in TARGETS:
        raise ValueError('unknown c_twin target %r — one of %s'
                         % (target, TARGETS))
    if wire is not None:
        from grpcbridge.custom.c_twin_v2 import render as render_v2
        return render_v2(class_name, wire, msg_type, version=version,
                         contract_hash=contract_hash, target=target)
    avr = target == 'avr'
    upper = class_name.upper()
    struct_lines = []
    enc_lines = []
    dec_lines = []
    for name, ptype, comment in _c_fields(field_map):
        note = f'  /* {comment} */' if comment else ''
        ctype, fixed = C_TYPES[ptype]
        if avr and ptype == 'double':
            ctype = 'polari_avr_double_t'
        if '[' in ctype:
            base = ctype.split('[')[0]
            struct_lines.append(
                f'    {base} {name}[{C_STR_MAX}];{note}')
        else:
            struct_lines.append(f'    {ctype} {name};{note}')
        if ptype == 'int64':
            enc_lines.append(
                f'    polari_put_u32(p, (uint32_t)s->{name});\n'
                f'    polari_put_u32(p + 4, '
                f'(uint32_t)((uint64_t)s->{name} >> 32)); p += 8;')
            dec_lines.append(
                f'    if (end - p < 8) return -1;\n'
                f'    s->{name} = (int64_t)((uint64_t)'
                f'polari_get_u32(p)\n'
                f'        | ((uint64_t)polari_get_u32(p + 4) << 32));'
                f' p += 8;')
        elif ptype == 'double' and avr:
            enc_lines.append(
                f'    polari_f32_to_f64(s->{name}, &lo, &hi);\n'
                f'    polari_put_u32(p, lo); polari_put_u32(p + 4, hi);'
                ' p += 8;  /* binary32 -> binary64 (target avr) */')
            dec_lines.append(
                f'    if (end - p < 8) return -1;\n'
                f'    s->{name} = polari_f64_to_f32(polari_get_u32(p),'
                f' polari_get_u32(p + 4)); p += 8;')
        elif ptype == 'double':
            enc_lines.append(
                f'    memcpy(p, &s->{name}, 8); p += 8;'
                '  /* LE host assumed (Cortex-M / x86) */')
            dec_lines.append(
                f'    if (end - p < 8) return -1;\n'
                f'    memcpy(&s->{name}, p, 8); p += 8;')
        elif ptype == 'bool':
            enc_lines.append(f'    *p++ = s->{name} ? 1u : 0u;')
            dec_lines.append(
                f'    if (end - p < 1) return -1;\n'
                f'    s->{name} = (*p++ != 0u);')
        else:  # string / bytes: u16 length prefix
            # brd-1: on AVR ptrdiff_t is a 16-bit int and uint16_t an unsigned int, so `end - p < n` trips
            # -Wsign-compare under -Wextra -Werror; end - p is never negative here, so compare as uint16_t
            # (target avr only — the host header stays byte-identical)
            avail = '(uint16_t)(end - p)' if avr else 'end - p'
            enc_lines.append(
                f'    n = (uint16_t)strlen(s->{name});\n'
                f'    polari_put_u16(p, n); p += 2;\n'
                f'    memcpy(p, s->{name}, n); p += n;')
            dec_lines.append(
                f'    if (end - p < 2) return -1;\n'
                f'    n = polari_get_u16(p); p += 2;\n'
                f'    if ({avail} < n) return -1;\n'
                f'    cp = n < {C_STR_MAX - 1}u ? n : {C_STR_MAX - 1}u;'
                '  /* bounded: SAMD21-tier honest truncation */\n'
                f'    memcpy(s->{name}, p, cp); '
                f's->{name}[cp] = 0; p += n;')
    nl = '\n'
    has_double = any(t == 'double' for _, t, _ in _c_fields(field_map))
    common = _COMMON + ('\n\n' + _AVR_DOUBLE if avr and has_double else '')
    target_note = '   target avr' if avr else ''
    enc_decl = '\n    uint32_t lo, hi;' if avr and has_double else ''
    return f'''/* Generated by Polari grpcbridge.custom.c_twin (grpc-j3) — do not edit.
 * class: {class_name}   contract v{version}   hash {contract_hash}{target_note}
 * Byte-exact twin of the Java {class_name}Codec / PolariPacket:
 * regenerate when the contract regenerates. */
#ifndef {upper}_PACKETS_H
#define {upper}_PACKETS_H

#ifndef POLARI_RX_PAYLOAD_MAX
#define POLARI_RX_PAYLOAD_MAX {payload_max(field_map)}u
#endif

{common}

#define {upper}_MSG_TYPE {int(msg_type)}u
#define {upper}_PAYLOAD_MAX {payload_max(field_map)}u

typedef struct {{
{nl.join(struct_lines)}
}} {class_name}_t;

/* struct -> payload bytes (tag order). Returns payload length. */
static uint16_t {class_name}_encode(const {class_name}_t *s,
                                    uint8_t *p)
{{
    uint8_t *start = p;
    uint16_t n;{enc_decl}
    (void)n;
{nl.join(enc_lines)}
    return (uint16_t)(p - start);
}}

/* payload bytes -> struct. Returns 0, or -1 on truncated input. */
static int {class_name}_decode(const uint8_t *p, uint16_t len,
                               {class_name}_t *s)
{{
    const uint8_t *end = p + len;
    uint16_t n, cp;
    (void)n; (void)cp;
{nl.join(dec_lines)}
    return 0;
}}

#endif /* {upper}_PACKETS_H */
'''
