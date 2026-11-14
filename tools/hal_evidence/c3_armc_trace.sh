#!/bin/sh
# econ gate 2 on arm C: in prf-esp-engines:pt2-polari, job dir $1 (holds layout.json + img.bin) -> trace of every GPIO / IO_MUX access
# (polari-block runs, esp32.gpio passthrough, esp32c3.iomem IO_MUX) + pb-dump.txt + pins.log, SECONDS $2 of wall, no input
cd "$1" || exit 2
timeout "$2" qemu-system-riscv32 -machine esp32c3 -display none -monitor none -nodefaults -serial file:u0.txt -serial file:u1.txt \
  -icount shift=3,align=off,sleep=off -drive file=img.bin,if=mtd,format=raw \
  -d trace:memory_region_ops_write,trace:memory_region_ops_read,guest_errors,unimp -D q.log >/dev/null 2>&1
grep -E "name 'polari-block\.|name 'esp32.gpio'|addr 0x60009[0-9a-f]{3} .*esp32c3.iomem" q.log > mmio.txt
grep -v "memory_region_ops" q.log > notes.txt
wc -l < q.log; rm -f q.log
