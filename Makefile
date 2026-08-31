.DEFAULT_GOAL := help

.PHONY: help prefetch generated-check build-reproducible

help:
	@python3 ci/run_make_target.py help

prefetch:
	@python3 ci/run_make_target.py prefetch

generated-check:
	@python3 ci/run_make_target.py generated-check

build-reproducible:
	@python3 ci/run_make_target.py build-reproducible

%:
	@python3 ci/run_make_target.py "$@"
