The toolchain image moved to its own submodule: `polari-rf-node/polari-eda-tools` (Dockerfile, the pinned sky130A
fetcher, the DRC/PEX/LVS flows and the licence ledger). Build it there as `polari-eda-tools:noble`; the lod scripts
read `POLARI_EDA_IMAGE` (default that name) and `POLARI_PDK_ROOT`. Nothing in this directory is executed.
