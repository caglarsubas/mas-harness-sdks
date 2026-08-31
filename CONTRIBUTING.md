# Contributing

Work from one approved `task-packets/` packet and its exact branch name. Keep
edits within `allowedPaths`, preserve deterministic generation, and run only the
packet's signed offline acceptance sequence. Do not hand-edit generated files;
change the generator or pinned input and regenerate them.

Pull requests must identify their packet, predecessor commit or digest, exact
acceptance evidence, and unclaimed evidence axes. No PR may require a hosted
runner, remote cache, package registry, cloud credential, or paid service.
