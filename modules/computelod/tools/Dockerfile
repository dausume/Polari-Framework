# polari-computelod-tools — THE OPEN TOOLCHAIN of the teaching path (lod-1, plan §C Phase 4), pinned by the
# Ubuntu 24.04 (noble) apt archive: gcc-riscv64-unknown-elf (GPL-3, the RISC-V cross compiler), yosys (ISC,
# synthesis), verilator (LGPL-3/Artistic-2, simulation), iverilog (GPL-2). Nothing here is vendor-locked.
# Used by computelod/custom/lod1_chain.py when the binaries are not on the PATH:
#   docker build -t polari-computelod-tools:noble modules/computelod/tools
#   docker run --rm -v <work>:/w -w /w polari-computelod-tools:noble <tool> …
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-riscv64-unknown-elf binutils-riscv64-unknown-elf picolibc-riscv64-unknown-elf \
        yosys verilator iverilog python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /w
