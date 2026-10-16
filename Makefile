PYTHON ?= python3
VFS ?= vfs/sample.xml
LOG ?= logs/session.csv

.PHONY: run test system-test check

run:
	$(PYTHON) main.py --vfs "$(VFS)" --log "$(LOG)"

test:
	$(PYTHON) tests/run_tests.py

system-test:
	bash system_scripts/run_all_parameters.sh
	bash system_scripts/run_minimal_vfs.sh
	bash system_scripts/run_deep_vfs.sh
	bash system_scripts/run_stage4_demo.sh
	bash system_scripts/run_stage5_demo.sh

check: test system-test
