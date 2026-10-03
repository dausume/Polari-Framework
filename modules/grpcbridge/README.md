# Grpcbridge (`grpcbridge`)

gRPC contracts from stabilized schemas, Java hardware bridges, hw sim rigs.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`GrpcContractsAPI`, `GrpcExposure`, `HardwareBridgeAPI`, `HardwareBridgeDefinition`, `ProtoContractVersion`, `SimRigState`; grpc-j4: `HardwareInterfaceBinding`, `EnumMapping`, `WireContract`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/contract/GrpcExposure.py`, `objects/contract/ProtoContractVersion.py`, `objects/hwsim/SimRigState.py`, `objects/hwsim/_shared.py`, `objects/java_bridge/HardwareBridgeDefinition.py`, `objects/mapping/{HardwareInterfaceBinding,EnumMapping,WireContract}.py`
- **basis** — `contract_basis.py`, `hwsim_basis.py`, `java_bridge_basis.py`, `mapping_basis.py` (the mapping rows + seeds)
- **api** — `contract_api.py`, `java_bridge_api.py`
- **custom** — `custom/c_twin.py`, `custom/descriptor_build.py`, `custom/grpc_server.py`, `custom/java_bridge.py`, `custom/java_bridge_codegen.py`, `custom/java_bridge_templates.py`, `custom/proto_gen.py`, `custom/transport_mux.py`; grpc-j4: `custom/wire_contract.py` (the wire spec, index width/representation, hash v2, derive), `custom/c_twin_v2.py` (the wire v2 C header), `custom/java_bridge_wire.py` (BindingRouter, enums, codec v2), `custom/wire_ref.py` (the independent Python reference)
- **selftests** — `c_twin_selftest.py` (+ `c_twin_wire_selftest.py`, run from it), `contracts_selftest.py`, `javabridge_selftest.py`, `serving_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## The computer↔firmware mapping (grpc-j4)

Design + decisions: `AI-Notes/plans/GRPC_BRIDGE_PLAN.md` §grpc-j4. Three layers: the Polari row (full identity, tied to
hardware by a `HardwareInterfaceBinding`) → the gRPC message (fields + `hardware_interface`, tag 2047, filled ONLY by
the bridge going up and the server going down) → the wire struct (fields only, after a prelude: the instance index —
none / packed ceil(log2 n) bits / an index byte / a u16 by the version byte 2/3/4 — and one presence bit per field).
A present false/0 is applied to the row (the proto3 drop is gone for bridged frames); `EnumMapping` fields are one
byte; `contract_hash` stays v1 (the schema watch), `WireContract.contract_hash_v2` is the wire watch.
`?wire=2&bridge=B` on `GET /api/grpc/exposures/<class>/c-header` renders the v2 header.

## Selftest

```
pol modules selftest grpcbridge        # in the running backend
PYTHONPATH=.:modules python3 -m grpcbridge.c_twin_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform grpcbridge`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
