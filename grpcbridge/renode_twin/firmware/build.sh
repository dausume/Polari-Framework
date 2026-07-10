#!/bin/bash
# Build the hwsim-1 Renode twin firmware.
#
#   ./build.sh [POLARI_API_BASE]
#
# Fetches the GENERATED per-class C header from the running Polari
# (know-what-you-need: only SimRigState), then cross-compiles the
# bare-metal ELF. Needs arm-none-eabi-gcc on PATH (xPack tarball is
# fine — no sudo).
set -e
cd "$(dirname "$0")"

BASE="${1:-https://api.prf.192.168.0.210.nip.io}"

echo "== fetching SimRigState C twin from $BASE =="
curl -skf "$BASE/api/grpc/exposures/SimRigState/c-header?msg_type=1" \
    -o simrigstate_packets.h
grep -q 'SIMRIGSTATE_MSG_TYPE' simrigstate_packets.h \
    || { echo "header fetch failed (exposure enabled?)"; exit 1; }

echo "== compiling =="
arm-none-eabi-gcc \
    -mcpu=cortex-m4 -mthumb -O2 -g \
    -ffreestanding -Wall -Werror \
    --specs=nosys.specs -nostartfiles \
    -Wl,-T,link.ld \
    startup.c main.c \
    -o firmware.elf
arm-none-eabi-size firmware.elf
echo "== firmware.elf ready =="
