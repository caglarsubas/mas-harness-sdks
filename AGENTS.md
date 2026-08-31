# Sol-High SDK Execution Rules

1. Implement exactly one approved task packet per branch and pull request.
2. Touch only the packet's `allowedPaths` and read every predecessor lock first.
3. `SDK-001` is the sole owner of `Makefile`, `ci/run_make_target.py`, and the
   inert `PORTING.yaml` bootstrap. Later Make-using packets add only their exact
   `ci/targets/<packet-id>.json` descriptor.
4. Never mount, open, copy, execute, or receive a path to a warm-start checkout.
   `PORTING.yaml` contains no current copy authorization.
5. Do not introduce cloud provisioning, hosted runners, paid APIs, API-key
   requirements, runtime downloads, remote caches, package publication, or
   external telemetry defaults.
6. Acceptance runs only through the hash-pinned packet's exact
   `offlineExecution.wrapperArgv`; prefetch and acceptance remain in the same
   deny-all-outbound OS-isolated process tree.
7. Preserve source, CI, merge, artifact, signature, deployment, runtime,
   security, assurance, and tenant acceptance as separate evidence states.
8. Create `codex/<packet-id>-<slug>`, open a PR, monitor the required ephemeral
   credential-free self-hosted check, and merge only when it is green.
9. Generated clients consume only the digest-verified snapshot named by
   `contracts.lock.json`. Drift, extra files, linked files, or an unknown lock
   version fail closed.
10. Generated request builders are transport-neutral and must never perform
    network I/O by default.
