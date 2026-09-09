# Grpcbridge (`grpcbridge`)

gRPC contracts from stabilized schemas, Java hardware bridges, hw sim rigs.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`GrpcContractsAPI`, `GrpcExposure`, `HardwareBridgeAPI`, `HardwareBridgeDefinition`, `ProtoContractVersion`, `SimRigState`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/contract/GrpcExposure.py`, `objects/contract/ProtoContractVersion.py`, `objects/hwsim/SimRigState.py`, `objects/hwsim/_shared.py`, `objects/java_bridge/HardwareBridgeDefinition.py`
- **basis** — `contract_basis.py`, `hwsim_basis.py`, `java_bridge_basis.py`
- **api** — `contract_api.py`, `java_bridge_api.py`
- **custom** — `custom/c_twin.py`, `custom/descriptor_build.py`, `custom/grpc_server.py`, `custom/java_bridge.py`, `custom/java_bridge_codegen.py`, `custom/java_bridge_templates.py`, `custom/proto_gen.py`, `custom/transport_mux.py`
- **selftests** — `c_twin_selftest.py`, `contracts_selftest.py`, `javabridge_selftest.py`, `serving_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest grpcbridge        # in the running backend
PYTHONPATH=.:modules python3 -m grpcbridge.c_twin_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform grpcbridge`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
