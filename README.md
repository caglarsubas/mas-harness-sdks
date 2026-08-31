# Planeon Harness SDKs

Generated, dependency-minimal Python and TypeScript clients for the public
Planeon MAS harness contracts. The repository is offline-first: generation,
tests, and package builds run from a pinned contract snapshot without network
access, hosted runners, remote caches, package registries, paid APIs, or API
keys.

## SDK-001 scope

The bootstrap release provides:

- a digest-bound snapshot of the `mas-harness-contracts` v0.1.0 release;
- deterministic Python `TypedDict` models and request builders;
- deterministic TypeScript source, ESM runtime files, and declarations;
- lifecycle CloudEvent channel helpers;
- reproducible Python wheel/sdist and npm-compatible tarball builders;
- closed packet-owned Make dispatch and an inert `PORTING.yaml` ledger.

Generated request builders describe HTTP requests but never send them. Later
packets may add caller-supplied transports, telemetry, trust, protocol, and
integration helpers without changing this packet's Makefile.

## Commands

```console
make prefetch
make generated-check
make build-reproducible
```

All three targets are direct-argv rules. The signed CI launcher runs prefetch
and acceptance in one OS-isolated, deny-all-outbound process tree.

## Evidence boundary

Successful source generation, CI, merge, or package reproducibility does not
claim deployment, runtime, security, assurance, or tenant acceptance. Packages
are created locally for digest comparison and are not uploaded by CI.
