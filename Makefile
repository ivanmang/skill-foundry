# == regression-harness ==
#
#   make check    run the self-check (compile + skill-spec + demo smoke)
#   make validate check suites/arches/cann configs
#   make help     show this

.PHONY: check help validate

check:
	./scripts/selfcheck

validate:
	python3 scripts/validate.py

help:
	@./harness help
