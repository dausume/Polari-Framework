#!/bin/sh
# in prf-esp-engines: mmio_trace.sh IMAGE OUT SECONDS  -> OUT = the GPIO (0x60004xxx) / IO_MUX (0x60009xxx) MMIO writes + reads
cp "$1" /tmp/img.bin
timeout "$3" qemu-system-riscv32 -machine esp32c3 -display none -monitor none -nodefaults -serial file:/tmp/u0.txt -serial file:/tmp/u1.txt -icount shift=3,align=off,sleep=off \
  -drive file=/tmp/img.bin,if=mtd,format=raw -d trace:memory_region_ops_write,trace:memory_region_ops_read -D /tmp/q.log >/dev/null 2>&1
grep -E "name 'esp32.gpio'|addr 0x60009[0-9a-f]{3} .*esp32c3.iomem" /tmp/q.log > "$2"; grep -o "name '[^']*'" /tmp/q.log | sort | uniq -c | sort -rn > "$2.names"
grep -c . /tmp/q.log; cp /tmp/u0.txt "$2.u0"; cp /tmp/u1.txt "$2.u1"
