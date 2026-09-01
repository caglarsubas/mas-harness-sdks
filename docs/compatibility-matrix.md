# Compatibility matrix

This matrix describes only the newly approved migration aliases implemented by `planeon-prometa-compat`. It is not evidence of parity with any historical private API.

| Evidence dimension | SDK-007 status | Boundary |
| --- | --- | --- |
| Compatibility package | `planeon-prometa-compat==0.1.0` | Separate optional wheel |
| Canonical package | `planeon-harness-sdk==0.1.0` | Exact dependency; canonical never imports compatibility |
| Python | `>=3.10` | Pure Python `py3-none-any` wheel |
| Approved aliases | SUPPORTED | Only `prometa`, `prometa.guardrail`, `prometa.integrations`, `prometa.protocols`, and `prometa.runtime` |
| Offline build | VERIFIED_BY_PACKET | Dependency-free, fixed-epoch, two-build byte comparison; no default retained artifact |
| Network and paid services | DISABLED | No network call, runtime download, API key, hosted telemetry, or publication |
| Historical/private `prometa` APIs | NOT_CLAIMED | No warm-source observation or inferred legacy surface |
| Deployment | NOT_CLAIMED | No cluster, VM, SaaS, or air-gapped deployment was performed |
| Runtime | NOT_CLAIMED | Package import tests are not deployed runtime evidence |
| Security assurance | NOT_CLAIMED | Packet checks do not constitute independent assurance certification |
| Tenant acceptance | NOT_CLAIMED | No tenant can be accepted by a package build or campaign |

The compatibility aliases are scheduled for removal in compatibility version 2.0.0. Every pre-v2 version change must atomically update the canonical SDK, compatibility version, exact dependency, alias tests, and this matrix.
