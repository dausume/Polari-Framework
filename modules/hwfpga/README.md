# Hwfpga (`hwfpga`)

FPGA register maps as data; Verilog/C/testbench artifacts from rows.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`FpgaRegisterMapAPI`, `FpgaRegisterState`, `LedMatrix4x4State`, `RegisterDefinition`, `RegisterMapDefinition`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/fpga/FpgaRegisterState.py`, `objects/fpga/RegisterDefinition.py`, `objects/fpga/RegisterMapDefinition.py`, `objects/fpga/_shared.py`, `objects/led/LedMatrix4x4State.py`, `objects/led/_shared.py`
- **basis** — `fpga_basis.py`, `led_basis.py`
- **api** — `fpga_api.py`
- **custom** — `custom/fpga_verilog.py`
- **selftests** — `fpga_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest hwfpga        # in the running backend
PYTHONPATH=.:modules python3 -m hwfpga.fpga_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform hwfpga`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
