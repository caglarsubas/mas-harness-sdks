# Tenant-neutral telemetry examples

SDK-002 records a small OpenTelemetry-compatible span model without installing
or configuring an exporter. Python uses task-local context propagation;
TypeScript keeps context explicit so framework adapters can supply their own
async-context mechanism later.

Tenant and organization values are identity claims. The carrier extractors
ignore them unless the receiving service has authenticated the transport and
explicitly enables trusted identity extraction. Examples use synthetic opaque
identifiers only.

Only the closed `harness.*` semantic keys and `harness.label.*` extension keys
with opaque, whitespace-free values are retained. Raw prompts, completions, content, bodies, messages, payloads,
authorization data, cookies, credentials, passwords, secrets, tokens, unknown
keys, nested values, and overlong strings are dropped. Function arguments,
return values, error messages, and stack traces are never captured.

`golden-span-vectors.json` is shared by Python and TypeScript tests. The
provenance record contains hashes and Git object identifiers from the public
reuse authority only; the referenced warm-source files were not opened,
mounted, copied, adapted, translated, or executed.
