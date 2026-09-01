# Migrating from `prometa` imports

`planeon-prometa-compat` 0.1.0 is a newly approved migration alias package. It does not claim compatibility with an observed historical or private `prometa` implementation.

Install `planeon-prometa-compat==0.1.0` only with `planeon-harness-sdk==0.1.0`. The compatibility wheel declares that exact canonical dependency and is intended for an offline, separately approved release assembly. It is not installed automatically and is not published by the repository build.

| Deprecated import | Replacement import |
| --- | --- |
| `prometa` | `planeon_harness` |
| `prometa.guardrail` | `planeon_harness.guardrail` |
| `prometa.integrations` | `planeon_harness.integrations` |
| `prometa.protocols` | `planeon_harness.protocols` |
| `prometa.runtime` | `planeon_harness.runtime` |

The first `prometa` package import raises one `DeprecationWarning`:

> The prometa import is deprecated; use planeon_harness. It is supported only through planeon-harness-sdk v1 and will be removed in v2.

Migrate each import to its replacement and remove `planeon-prometa-compat` after no `prometa` imports remain. No other compatibility module or attribute is supported. The aliases will be removed in compatibility version 2.0.0 and are supported only alongside canonical SDK v1.

For rollback before v2, remove the optional compatibility wheel from the release assembly and restore the application version that still used the same 0.1.0-to-0.1.0 pair. Do not change or withdraw `planeon-harness-sdk`; canonical consumers never depend on this compatibility package.

Any future pre-v2 release must update the canonical SDK version, compatibility version, exact dependency, alias tests, and compatibility matrix atomically.
