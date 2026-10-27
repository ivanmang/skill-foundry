# == regression-harness ==
#
#   make check   run the self-check (compile + demo smoke)
#   make help    show this

.PHONY: check help validate

check:
	./scripts/selfcheck

validate:
	python3 scripts/validate.py

help:
	@./harness help