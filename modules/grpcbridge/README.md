# Grpcbridge (`grpcbridge`)

gRPC contracts from stabilized schemas, Java hardware bridges, hw sim rigs.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`GrpcContractsAPI`, `GrpcExposure`, `HardwareBridgeAPI`, `HardwareBridgeDefinition`, `ProtoContractVersion`, `SimRigState`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `contract_basis.py`, `hwsim_basis.py`, `java_bridge_basis.py`
- **api** — `contract_api.py`, `java_bridge_api.py`
- **custom** — `custom/c_twin.py`, `custom/descriptor_build.py`, `custom/grpc_server.py`, `custom/java_bridge.py`, `custom/java_bridge_codegen.py`, `custom/java_bridge_templates.py`, `custom/proto_gen.py`, `custom/transport_mux.py`
- **selftests** — `c_twin_selftest.py`, `contracts_selftest.py`, `javabridge_selftest.py`, `serving_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest grpcbridge        # in the running backend
PYTHONPATH=.:modules python3 -m grpcbridge.c_twin_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform grpcbridge`
