PYTHON ?= python3

.PHONY: run test check

run:
	$(PYTHON) main.py

test:
	$(PYTHON) tests/run_tests.py

check: test
